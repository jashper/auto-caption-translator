"""
FastAPI 主應用程式
影片字幕自動翻譯系統
"""
# 修復 PyTorch 2.6+ weights_only 問題 - 必須在導入 torch 前設置
import os
os.environ['TORCH_FORCE_WEIGHTS_ONLY_LOAD'] = '0'

import torch
# Monkey patch torch.load 以使用 weights_only=False
_original_torch_load = torch.load
def _patched_torch_load(*args, **kwargs):
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)
torch.load = _patched_torch_load

# 添加 omegaconf 到安全全局列表（WhisperX 模型需要）
try:
    from omegaconf.listconfig import ListConfig
    from omegaconf.dictconfig import DictConfig
    from omegaconf.base import ContainerMetadata
    torch.serialization.add_safe_globals([ListConfig, DictConfig, ContainerMetadata])
except ImportError:
    pass  # omegaconf 可能未安裝

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, UploadFile, HTTPException, status, Form, Body
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
import zipfile
import io

from src.models.api import (
    UploadResponse,
    JobStatusResponse,
    PreviewResponse,
    SubtitlePreview,
    HealthResponse,
    ErrorResponse
)
from src.managers.job_manager import JobManager
from src.managers.task_queue import TaskQueue
from src.storage.file_storage import FileStorage
from src.validators.file_validator import Validator
from src.services.subtitle_generator import SubtitleGenerator
from src.utils.error_handlers import (
    validation_exception_handler,
    general_exception_handler,
    get_error_response
)
from src.utils.cleanup import scheduled_cleanup
from src.utils.logger import get_logger
from src.config import HOST, PORT
import ffmpeg as ffmpeg_lib

logger = get_logger("main")

# 全域實例
job_manager = JobManager()
task_queue = TaskQueue()
file_storage = FileStorage()
validator = Validator()
subtitle_generator = SubtitleGenerator()


def _validate_job_id(job_id: str):
    """驗證 job_id 格式，無效則拋出 400 錯誤"""
    result = validator.validate_job_id(job_id)
    if not result.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": result.error_message, "error_code": result.error_code}
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    # 啟動時
    logger.info("正在啟動應用程式...")
    
    # 啟動任務佇列
    await task_queue.start()
    
    # 啟動定時清理任務
    cleanup_task = asyncio.create_task(scheduled_cleanup(file_storage))
    
    # 在背景執行緒中預載 WhisperX 模型（不阻塞 uvicorn 啟動）
    async def _preload_model():
        svc = job_manager.transcription_service
        try:
            loop = asyncio.get_event_loop()
            
            # 啟動模型載入（在背景執行緒）
            load_future = loop.run_in_executor(None, svc._load_model)
            
            # 同時監控下載進度（每 5 秒輸出一次）
            while not load_future.done():
                await asyncio.sleep(5)
                if load_future.done():
                    break
                progress = svc._get_download_progress()
                if progress >= 0:
                    pct = int(progress * 100)
                    size_gb = svc.MODEL_SIZES.get(svc.model_size, 0)
                    downloaded_mb = int(progress * size_gb * 1024)
                    total_mb = int(size_gb * 1024)
                    logger.info(f"模型下載進度: {pct}% ({downloaded_mb}/{total_mb} MB)")
                elif svc.model_status == "loading":
                    logger.info("模型載入中，請稍候...")
            
            # 等待完成並取得結果（如有例外會在此拋出）
            await load_future
            logger.info("WhisperX 模型預載完成")
        except Exception as e:
            logger.error(f"WhisperX 模型預載失敗: {e}")
            logger.error("轉錄功能可能無法使用，請檢查模型設定")
    
    model_task = asyncio.create_task(_preload_model())
    
    logger.info("應用程式啟動完成")
    
    yield
    
    # 關閉時
    logger.info("正在關閉應用程式...")
    
    # 停止任務佇列
    await task_queue.stop()
    
    # 取消清理任務
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    
    logger.info("應用程式已關閉")


# 建立 FastAPI 應用程式
app = FastAPI(
    title="影片字幕自動翻譯系統",
    description="使用 Whisper 和 Google Translate 自動生成多語言字幕",
    version="1.0.0",
    lifespan=lifespan
)

# 設定 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊異常處理器
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# 掛載靜態檔案
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    logger.info(f"靜態檔案目錄: {static_dir}")
else:
    logger.warning(f"靜態檔案目錄不存在: {static_dir}")


@app.get("/", include_in_schema=False)
async def root():
    """根路徑重定向到靜態頁面"""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    else:
        return {"message": "Video Subtitle Translator API", "docs": "/docs", "health": "/health"}


@app.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_video(
    file: UploadFile = File(...),
    target_languages: str = Form(""),
    source_language: str = Form("en")
):
    """
    上傳影片檔案
    
    Args:
        file: 上傳的影片檔案
        target_languages: 目標翻譯語言（逗號分隔，例如：zh-TW,zh-CN,ms）
        
    Returns:
        上傳回應（包含任務 ID）
    """
    try:
        # 解析目標語言
        languages = []
        if target_languages:
            languages = [lang.strip() for lang in target_languages.split(',') if lang.strip()]
        
        # 如果沒有指定語言，使用預設值
        if not languages:
            languages = ["zh-TW", "zh-CN", "ms"]
        
        # 驗證語言代碼
        valid_languages = ["en", "zh-TW", "zh-CN", "ms"]
        languages = [lang for lang in languages if lang in valid_languages]
        
        if not languages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "請至少選擇一種有效的翻譯語言", "error_code": "INVALID_LANGUAGES"}
            )
        
        # 驗證檔案
        file_size = 0
        if file.file:
            file.file.seek(0, 2)  # 移到檔案末尾
            file_size = file.file.tell()
            file.file.seek(0)  # 回到檔案開頭
        
        validation_result = validator.validate_video_file(file.filename, file_size)
        if not validation_result.is_valid:
            error_response = get_error_response(validation_result.error_code, validation_result.error_message)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_response.dict()
            )
        
        # 儲存檔案
        job_id = job_manager.create_job(file.filename, "", languages, source_language)
        video_path = await file_storage.save_uploaded_file(file, job_id)
        
        # 更新任務狀態中的影片路徑
        state = job_manager.get_job_status(job_id)
        state.video_path = video_path
        job_manager.state_manager.save_job_state(job_id, state)
        
        # 驗證影片時長
        duration_result = validator.validate_video_duration(video_path)
        if not duration_result.is_valid:
            # 清理檔案
            file_storage.cleanup_job_files(job_id)
            error_response = get_error_response(duration_result.error_code, duration_result.error_message)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_response.dict()
            )
        
        # 計算預估處理時間
        try:
            probe = ffmpeg_lib.probe(video_path)
            video_duration = float(probe['format']['duration'])
            state.estimated_seconds = video_duration * 0.05
            job_manager.state_manager.save_job_state(job_id, state)
        except Exception:
            pass  # 取不到時長也沒關係，就不顯示預估

        # 加入處理佇列
        await task_queue.enqueue(job_id, job_manager.process_job, job_id)
        
        logger.info(f"已接受上傳: {file.filename} (任務 ID: {job_id}, 語言: {', '.join(languages)})")
        
        return UploadResponse(
            job_id=job_id,
            status="queued",
            message="影片已上傳，正在處理中"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上傳失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "上傳失敗", "error_code": "UPLOAD_FAILED", "details": str(e)}
        )


@app.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    查詢任務狀態
    
    Args:
        job_id: 任務識別碼
        
    Returns:
        任務狀態回應
    """
    try:
        _validate_job_id(job_id)
        state = job_manager.get_job_status(job_id)
        
        return JobStatusResponse(
            job_id=state.job_id,
            status=state.status.value,
            progress=state.progress,
            stage=state.stage,
            detected_language=state.detected_language,
            source_language=state.source_language,
            primary_language=state.primary_language,
            language_distribution=state.language_distribution,
            language_mismatch=state.language_mismatch,
            error_message=state.error_message,
            estimated_seconds=state.estimated_seconds,
            subtitle_files=state.subtitle_files if state.status.value == "completed" else None
        )
    except FileNotFoundError:
        error_response = get_error_response("JOB_NOT_FOUND")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response.dict()
        )
    except Exception as e:
        logger.error(f"查詢任務狀態失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "查詢失敗", "error_code": "QUERY_FAILED", "details": str(e)}
        )


@app.get("/download/{job_id}/{language}")
async def download_subtitle(job_id: str, language: str):
    """
    下載字幕檔案
    
    Args:
        job_id: 任務識別碼
        language: 語言代碼
        
    Returns:
        VTT 字幕檔案
    """
    try:
        _validate_job_id(job_id)
        # 檢查任務狀態
        state = job_manager.get_job_status(job_id)
        
        if state.status.value != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "任務尚未完成", "error_code": "JOB_NOT_COMPLETED"}
            )
        
        # 取得字幕檔案路徑
        subtitle_path = file_storage.get_subtitle_path(job_id, language)
        
        if not Path(subtitle_path).exists():
            error_response = get_error_response("FILE_NOT_FOUND")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response.dict()
            )
        
        # 回傳檔案
        return FileResponse(
            subtitle_path,
            media_type="text/vtt",
            filename=f"{state.video_filename.rsplit('.', 1)[0]}_{language}.vtt"
        )
    except HTTPException:
        raise
    except FileNotFoundError:
        error_response = get_error_response("JOB_NOT_FOUND")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response.dict()
        )
    except Exception as e:
        logger.error(f"下載字幕失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "下載失敗", "error_code": "DOWNLOAD_FAILED", "details": str(e)}
        )


@app.get("/preview/{job_id}/{language}", response_model=PreviewResponse)
async def preview_subtitle(job_id: str, language: str):
    """
    預覽字幕內容
    
    Args:
        job_id: 任務識別碼
        language: 語言代碼
        
    Returns:
        字幕預覽回應
    """
    try:
        _validate_job_id(job_id)
        # 檢查任務狀態
        state = job_manager.get_job_status(job_id)
        
        if state.status.value != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "任務尚未完成", "error_code": "JOB_NOT_COMPLETED"}
            )
        
        # 取得字幕檔案路徑
        subtitle_path = file_storage.get_subtitle_path(job_id, language)
        
        if not Path(subtitle_path).exists():
            error_response = get_error_response("FILE_NOT_FOUND")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response.dict()
            )
        
        # 解析字幕檔案
        segments = subtitle_generator.parse_vtt(subtitle_path)
        
        # 轉換為預覽格式
        subtitles = [
            SubtitlePreview(
                index=seg.index,
                start_time=seg.format_vtt_timestamp(seg.start_time),
                end_time=seg.format_vtt_timestamp(seg.end_time),
                text=seg.text
            )
            for seg in segments
        ]
        
        return PreviewResponse(
            job_id=job_id,
            language=language,
            subtitles=subtitles
        )
    except HTTPException:
        raise
    except FileNotFoundError:
        error_response = get_error_response("JOB_NOT_FOUND")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response.dict()
        )
    except Exception as e:
        logger.error(f"預覽字幕失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "預覽失敗", "error_code": "PREVIEW_FAILED", "details": str(e)}
        )


@app.get("/video/{job_id}")
async def get_video(job_id: str):
    """
    取得影片檔案（用於播放器）
    
    Args:
        job_id: 任務識別碼
        
    Returns:
        影片檔案
    """
    try:
        _validate_job_id(job_id)
        # 檢查任務狀態
        state = job_manager.get_job_status(job_id)
        
        if not state.video_path or not Path(state.video_path).exists():
            error_response = get_error_response("FILE_NOT_FOUND")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response.dict()
            )
        
        # 回傳影片檔案
        return FileResponse(
            state.video_path,
            media_type="video/mp4",
            filename=state.video_filename
        )
    except HTTPException:
        raise
    except FileNotFoundError:
        error_response = get_error_response("JOB_NOT_FOUND")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response.dict()
        )
    except Exception as e:
        logger.error(f"取得影片失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "取得影片失敗", "error_code": "VIDEO_FETCH_FAILED", "details": str(e)}
        )


@app.put("/subtitle/{job_id}/{language}")
async def update_subtitle(job_id: str, language: str, subtitles: List[dict]):
    """
    更新字幕內容
    
    Args:
        job_id: 任務識別碼
        language: 語言代碼
        subtitles: 更新後的字幕列表
        
    Returns:
        更新結果
    """
    try:
        _validate_job_id(job_id)
        # 檢查任務狀態
        state = job_manager.get_job_status(job_id)
        
        if state.status.value != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "任務尚未完成", "error_code": "JOB_NOT_COMPLETED"}
            )
        
        # 轉換為 SubtitleSegment 對象
        from src.models.subtitle import SubtitleSegment
        segments = []
        for sub in subtitles:
            segment = SubtitleSegment(
                index=sub["index"],
                start_time=sub["start_time"],
                end_time=sub["end_time"],
                text=sub["text"],
                language=language,
                dirty=True
            )
            segments.append(segment)
        
        # 重新生成字幕檔案
        subtitle_path = file_storage.get_subtitle_path(job_id, language)
        subtitle_generator.generate_vtt(segments, subtitle_path, language)
        
        logger.info(f"已更新字幕: {job_id} ({language})")
        
        return {"success": True, "message": "字幕已更新"}
    except HTTPException:
        raise
    except FileNotFoundError:
        error_response = get_error_response("JOB_NOT_FOUND")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response.dict()
        )
    except Exception as e:
        logger.error(f"更新字幕失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "更新字幕失敗", "error_code": "UPDATE_FAILED", "details": str(e)}
        )


async def download_all_subtitles(job_id: str, include_video: bool = False):
    """
    批量下載所有字幕（ZIP 格式）

    Args:
        job_id: 任務識別碼
        include_video: 是否包含影片檔案

    Returns:
        ZIP 檔案
    """
    try:
        import zipfile
        import io

        _validate_job_id(job_id)
        # 檢查任務狀態
        state = job_manager.get_job_status(job_id)

        if state.status.value != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "任務尚未完成", "error_code": "JOB_NOT_COMPLETED"}
            )

        # 創建 ZIP 文件
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # 添加所有字幕文件
            for lang, subtitle_path in state.subtitle_files.items():
                if Path(subtitle_path).exists():
                    base_name = state.video_filename.rsplit('.', 1)[0]

                    # 添加 VTT 格式
                    vtt_filename = f"{base_name}_{lang}.vtt"
                    zip_file.write(subtitle_path, vtt_filename)

                    # 添加 SRT 格式
                    segments = subtitle_generator.parse_vtt(subtitle_path)
                    srt_content = subtitle_generator.generate_srt_content(segments)
                    srt_filename = f"{base_name}_{lang}.srt"
                    zip_file.writestr(srt_filename, srt_content)

            # 如果需要，添加影片文件
            if include_video and state.video_path and Path(state.video_path).exists():
                zip_file.write(state.video_path, state.video_filename)

        zip_buffer.seek(0)

        # 回傳 ZIP 檔案
        base_name = state.video_filename.rsplit('.', 1)[0]
        zip_filename = f"{base_name}_subtitles.zip"

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={zip_filename}"
            }
        )
    except HTTPException:
        raise
    except FileNotFoundError:
        error_response = get_error_response("JOB_NOT_FOUND")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response.dict()
        )
    except Exception as e:
        logger.error(f"批量下載失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "批量下載失敗", "error_code": "BATCH_DOWNLOAD_FAILED", "details": str(e)}
        )



@app.get("/download/{job_id}/{language}/srt")
async def download_subtitle_srt(job_id: str, language: str):
    """
    下載 SRT 格式字幕
    
    Args:
        job_id: 任務識別碼
        language: 語言代碼
        
    Returns:
        SRT 字幕檔案
    """
    try:
        _validate_job_id(job_id)
        # 檢查任務狀態
        state = job_manager.get_job_status(job_id)
        
        if state.status.value != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "任務尚未完成", "error_code": "JOB_NOT_COMPLETED"}
            )
        
        # 取得 VTT 字幕檔案
        vtt_path = file_storage.get_subtitle_path(job_id, language)
        
        if not Path(vtt_path).exists():
            error_response = get_error_response("FILE_NOT_FOUND")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response.dict()
            )
        
        # 解析 VTT 並轉換為 SRT
        segments = subtitle_generator.parse_vtt(vtt_path)
        
        # 生成 SRT 內容
        srt_content = subtitle_generator.generate_srt_content(segments)
        
        # 創建臨時 SRT 檔案
        import tempfile
        temp_srt = tempfile.NamedTemporaryFile(delete=False, suffix='.srt', mode='w', encoding='utf-8')
        temp_srt.write(srt_content)
        temp_srt.close()
        
        # 回傳檔案
        return FileResponse(
            temp_srt.name,
            media_type="text/plain",
            filename=f"{state.video_filename.rsplit('.', 1)[0]}_{language}.srt"
        )
    except HTTPException:
        raise
    except FileNotFoundError:
        error_response = get_error_response("JOB_NOT_FOUND")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response.dict()
        )
    except Exception as e:
        logger.error(f"下載 SRT 字幕失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "下載失敗", "error_code": "DOWNLOAD_FAILED", "details": str(e)}
        )


@app.get("/download/{job_id}/{language}/ass")
async def download_subtitle_ass(job_id: str, language: str):
    """
    下載 ASS 格式字幕
    
    Args:
        job_id: 任務識別碼
        language: 語言代碼
        
    Returns:
        ASS 字幕檔案
    """
    try:
        _validate_job_id(job_id)
        state = job_manager.get_job_status(job_id)
        
        if state.status.value != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "任務尚未完成", "error_code": "JOB_NOT_COMPLETED"}
            )
        
        vtt_path = file_storage.get_subtitle_path(job_id, language)
        
        if not Path(vtt_path).exists():
            error_response = get_error_response("FILE_NOT_FOUND")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response.dict()
            )
        
        segments = subtitle_generator.parse_vtt(vtt_path)
        ass_content = subtitle_generator.generate_ass_content(segments)
        
        import tempfile
        temp_ass = tempfile.NamedTemporaryFile(delete=False, suffix='.ass', mode='w', encoding='utf-8')
        temp_ass.write(ass_content)
        temp_ass.close()
        
        return FileResponse(
            temp_ass.name,
            media_type="text/plain",
            filename=f"{state.video_filename.rsplit('.', 1)[0]}_{language}.ass"
        )
    except HTTPException:
        raise
    except FileNotFoundError:
        error_response = get_error_response("JOB_NOT_FOUND")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response.dict()
        )
    except Exception as e:
        logger.error(f"下載 ASS 字幕失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "下載失敗", "error_code": "DOWNLOAD_FAILED", "details": str(e)}
        )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    健康檢查
    
    Returns:
        系統狀態資訊
    """
    try:
        # 取得磁碟空間
        disk_space = file_storage.get_disk_space()
        disk_space_gb = disk_space / (1024 * 1024 * 1024)
        
        # 檢查 Whisper 模型狀態
        whisper_loaded = job_manager.transcription_service.model is not None
        model_info = job_manager.transcription_service.get_model_info()
        
        return HealthResponse(
            status="healthy",
            active_jobs=task_queue.get_active_jobs_count(),
            queue_size=task_queue.get_queue_size(),
            disk_space_gb=round(disk_space_gb, 2),
            whisper_model_loaded=whisper_loaded,
            model_status=model_info["status"],
            model_status_message=model_info["status_message"],
            model_size=model_info["model_size"],
            model_size_gb=model_info["model_size_gb"],
            model_changed_from=model_info["changed_from"]
        )
    except Exception as e:
        logger.error(f"健康檢查失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "健康檢查失敗", "error_code": "HEALTH_CHECK_FAILED", "details": str(e)}
        )


@app.get("/video/{job_id}")
async def get_video(job_id: str):
    """
    獲取影片文件
    
    Args:
        job_id: 任務識別碼
        
    Returns:
        影片文件
    """
    try:
        _validate_job_id(job_id)
        state = job_manager.get_job_status(job_id)
        video_path = state.video_path
        
        if not Path(video_path).exists():
            error_response = get_error_response("FILE_NOT_FOUND")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response.dict()
            )
        
        return FileResponse(
            video_path,
            media_type="video/mp4",
            filename=state.video_filename
        )
    except FileNotFoundError:
        error_response = get_error_response("JOB_NOT_FOUND")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response.dict()
        )
    except Exception as e:
        logger.error(f"獲取影片失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "獲取影片失敗", "error_code": "VIDEO_FETCH_FAILED", "details": str(e)}
        )


@app.post("/update-subtitle/{job_id}/{language}")
async def update_subtitle_post(job_id: str, language: str, subtitles: list = Body(...)):
    """
    更新字幕內容
    
    Args:
        job_id: 任務識別碼
        language: 語言代碼
        subtitles: 字幕列表
        
    Returns:
        更新結果
    """
    try:
        _validate_job_id(job_id)
        state = job_manager.get_job_status(job_id)
        
        if state.status.value != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "任務尚未完成", "error_code": "JOB_NOT_COMPLETED"}
            )
        
        # 轉換為 SubtitleSegment 對象
        from src.models.subtitle import SubtitleSegment
        segments = []
        for sub in subtitles:
            segment = SubtitleSegment(
                index=sub["index"],
                start_time=sub["start_time"],
                end_time=sub["end_time"],
                text=sub["text"],
                language=language,
                dirty=True
            )
            segments.append(segment)
        
        # 重新生成字幕文件
        subtitle_path = file_storage.get_subtitle_path(job_id, language)
        subtitle_generator.generate_vtt(segments, subtitle_path, language)
        
        logger.info(f"已更新字幕: {job_id} ({language})")
        
        return {"success": True, "message": "字幕已更新"}
    except HTTPException:
        raise
    except FileNotFoundError:
        error_response = get_error_response("JOB_NOT_FOUND")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response.dict()
        )
    except Exception as e:
        logger.error(f"更新字幕失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "更新字幕失敗", "error_code": "UPDATE_FAILED", "details": str(e)}
        )


@app.get("/download/{job_id}/{language}/srt")
async def download_subtitle_srt(job_id: str, language: str):
    """
    下載 SRT 格式字幕
    
    Args:
        job_id: 任務識別碼
        language: 語言代碼
        
    Returns:
        SRT 字幕檔案
    """
    try:
        _validate_job_id(job_id)
        state = job_manager.get_job_status(job_id)
        
        if state.status.value != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "任務尚未完成", "error_code": "JOB_NOT_COMPLETED"}
            )
        
        # 讀取 VTT 字幕
        subtitle_path = file_storage.get_subtitle_path(job_id, language)
        if not Path(subtitle_path).exists():
            error_response = get_error_response("FILE_NOT_FOUND")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response.dict()
            )
        
        segments = subtitle_generator.parse_vtt(subtitle_path)
        
        # 轉換為 SRT 格式
        srt_content = subtitle_generator.generate_srt(segments)
        
        # 返回 SRT 文件
        return StreamingResponse(
            io.BytesIO(srt_content.encode('utf-8')),
            media_type="text/plain",
            headers={
                "Content-Disposition": f"attachment; filename={state.video_filename.rsplit('.', 1)[0]}_{language}.srt"
            }
        )
    except HTTPException:
        raise
    except FileNotFoundError:
        error_response = get_error_response("JOB_NOT_FOUND")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response.dict()
        )
    except Exception as e:
        logger.error(f"下載 SRT 字幕失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "下載失敗", "error_code": "DOWNLOAD_FAILED", "details": str(e)}
        )


@app.post("/merge-subtitles/{job_id}")
async def merge_subtitles(job_id: str, languages: List[str] = Body(..., embed=True), format: str = Body("srt", embed=True)):
    """
    合併多個語言的字幕為單一檔案
    
    Args:
        job_id: 任務識別碼
        languages: 要合併的語言列表（2-3 種）
        format: 輸出格式（"srt" 或 "vtt"）
        
    Returns:
        合併後的字幕檔案
    """
    try:
        _validate_job_id(job_id)
        # 檢查任務狀態
        state = job_manager.get_job_status(job_id)
        
        if state.status.value != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "任務尚未完成", "error_code": "JOB_NOT_COMPLETED"}
            )
        
        # 驗證語言數量
        if len(languages) < 2 or len(languages) > 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "請選擇 2-3 種語言", "error_code": "INVALID_LANGUAGE_COUNT"}
            )
        
        # 驗證格式
        if format.lower() not in ["srt", "vtt"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "格式必須是 srt 或 vtt", "error_code": "INVALID_FORMAT"}
            )
        
        # 取得字幕檔案路徑
        subtitle_paths = []
        for lang in languages:
            if lang not in state.subtitle_files:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"error": f"找不到語言 {lang} 的字幕", "error_code": "SUBTITLE_NOT_FOUND"}
                )
            subtitle_path = file_storage.get_subtitle_path(job_id, lang)
            if not Path(subtitle_path).exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"error": f"字幕檔案不存在: {lang}", "error_code": "FILE_NOT_FOUND"}
                )
            subtitle_paths.append(subtitle_path)
        
        # 合併字幕
        merged_content = subtitle_generator.merge_subtitles(subtitle_paths, languages, format.lower())
        
        # 返回合併後的字幕
        file_ext = format.lower()
        filename = f"{state.video_filename.rsplit('.', 1)[0]}_merged_{'_'.join(languages)}.{file_ext}"
        media_type = "text/vtt" if file_ext == "vtt" else "text/plain"
        
        return StreamingResponse(
            io.BytesIO(merged_content.encode('utf-8')),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except HTTPException:
        raise
    except FileNotFoundError:
        error_response = get_error_response("JOB_NOT_FOUND")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response.dict()
        )
    except Exception as e:
        logger.error(f"合併字幕失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "合併字幕失敗", "error_code": "MERGE_FAILED", "details": str(e)}
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
