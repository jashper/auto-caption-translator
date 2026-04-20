"""
任務管理器
管理任務的生命週期和處理流程
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from src.models.job import JobState, JobStatus
from src.models.subtitle import SubtitleSegment
from src.managers.state_manager import StateManager
from src.storage.file_storage import FileStorage
from src.services.transcription_service import TranscriptionService
from src.services.translation_service import TranslationService
from src.services.subtitle_generator import SubtitleGenerator
from src.utils.logger import get_logger

logger = get_logger("job_manager")


class JobManager:
    """任務管理器"""
    
    def __init__(
        self,
        state_manager: Optional[StateManager] = None,
        file_storage: Optional[FileStorage] = None,
        transcription_service: Optional[TranscriptionService] = None,
        translation_service: Optional[TranslationService] = None,
        subtitle_generator: Optional[SubtitleGenerator] = None
    ):
        """
        初始化任務管理器
        
        Args:
            state_manager: 狀態管理器
            file_storage: 檔案儲存管理器
            transcription_service: 轉錄服務
            translation_service: 翻譯服務
            subtitle_generator: 字幕生成器
        """
        self.state_manager = state_manager or StateManager()
        self.file_storage = file_storage or FileStorage()
        self.transcription_service = transcription_service or TranscriptionService()
        self.translation_service = translation_service or TranslationService()
        self.subtitle_generator = subtitle_generator or SubtitleGenerator()
    
    def create_job(self, video_filename: str, video_path: str, target_languages: List[str] = None, source_language: str = None) -> str:
        """
        建立新任務
        
        Args:
            video_filename: 影片檔名
            video_path: 影片檔案路徑
            target_languages: 目標翻譯語言列表
            source_language: 使用者指定的主要字幕語言 (en/zh/ms)
            
        Returns:
            任務識別碼
        """
        # 生成任務 ID
        job_id = str(uuid.uuid4())
        
        # 預設語言
        if target_languages is None:
            target_languages = ["zh-TW", "zh-CN", "ms"]
        
        # primary_language = source_language（不再接受 "auto"）
        primary_language = source_language if source_language and source_language != "auto" else None
        
        # 建立任務狀態
        now = datetime.now()
        state = JobState(
            job_id=job_id,
            status=JobStatus.QUEUED,
            progress=0,
            stage="排隊等待中，稍後自動開始處理…",
            video_filename=video_filename,
            video_path=video_path,
            target_languages=target_languages,
            created_at=now,
            updated_at=now,
            source_language=primary_language,
            primary_language=primary_language
        )
        
        # 儲存狀態
        self.state_manager.save_job_state(job_id, state)
        
        logger.info(f"已建立任務: {job_id} ({video_filename}, 主要語言: {primary_language}, 目標: {', '.join(target_languages)})")
        return job_id
    
    def get_job_status(self, job_id: str) -> JobState:
        """
        取得任務狀態
        
        Args:
            job_id: 任務識別碼
            
        Returns:
            任務狀態
        """
        return self.state_manager.load_job_state(job_id)
    
    def update_job_progress(self, job_id: str, progress: int, stage: str) -> None:
        """
        更新任務進度
        
        Args:
            job_id: 任務識別碼
            progress: 進度百分比
            stage: 階段描述
        """
        self.state_manager.update_progress(job_id, progress, stage)
    
    def mark_job_completed(self, job_id: str, subtitle_files: dict[str, str]) -> None:
        """
        標記任務為完成
        
        Args:
            job_id: 任務識別碼
            subtitle_files: 字幕檔案路徑字典
        """
        state = self.get_job_status(job_id)
        state.mark_completed(subtitle_files)
        self.state_manager.save_job_state(job_id, state)
        logger.info(f"任務 {job_id} 已完成")
    
    def mark_job_failed(self, job_id: str, error: str) -> None:
        """
        標記任務為失敗
        
        Args:
            job_id: 任務識別碼
            error: 錯誤訊息
        """
        state = self.get_job_status(job_id)
        state.mark_failed(error)
        self.state_manager.save_job_state(job_id, state)
        logger.error(f"任務 {job_id} 失敗: {error}")
    
    async def process_job(self, job_id: str) -> None:
        """
        處理任務（完整流程）
        
        Args:
            job_id: 任務識別碼
        """
        try:
            # 更新狀態為處理中
            state = self.get_job_status(job_id)
            state.status = JobStatus.PROCESSING
            self.state_manager.save_job_state(job_id, state)
            
            # 階段 1: 轉錄 (0-40%)
            if self.transcription_service.model is None:
                self.update_job_progress(job_id, 2, "正在載入語音識別模型（首次可能需要下載）…")
                state.status = JobStatus.TRANSCRIBING
                self.state_manager.save_job_state(job_id, state)
            
            self.update_job_progress(job_id, 5, "正在辨識影片中的語音…")
            state.status = JobStatus.TRANSCRIBING
            self.state_manager.save_job_state(job_id, state)
            
            source_segments, used_language, auto_detected_language = await self.transcription_service.transcribe(
                state.video_path, language=state.primary_language
            )
            
            # 語言不符檢測
            language_distribution = {auto_detected_language: 100}
            language_mismatch = False
            if state.primary_language and auto_detected_language != state.primary_language:
                # 處理 zh 變體（zh, zh-TW, zh-CN 視為同系列）
                zh_variants = {'zh', 'zh-TW', 'zh-CN'}
                if not (state.primary_language in zh_variants and auto_detected_language in zh_variants):
                    language_mismatch = True
                    logger.warning(
                        f"任務 {job_id} 語言不符：主要語言 {state.primary_language}，偵測到 {auto_detected_language}"
                    )
            
            # 保存 raw transcript（內部使用，不給使用者看）
            subtitle_dir = self.file_storage.ensure_subtitle_dir(job_id)
            raw_path = Path(subtitle_dir) / "raw.json"
            raw_data = [
                {
                    "index": seg.index,
                    "start_time": seg.start_time,
                    "end_time": seg.end_time,
                    "text": seg.text,
                    "language": seg.language
                }
                for seg in source_segments
            ]
            with open(raw_path, 'w', encoding='utf-8') as f:
                json.dump({"language": used_language, "auto_detected": auto_detected_language, "segments": raw_data}, f, ensure_ascii=False, indent=2)
            
            # 保存語言資訊到狀態
            state.detected_language = auto_detected_language
            state.primary_language = state.primary_language or used_language
            state.language_distribution = language_distribution
            state.language_mismatch = language_mismatch
            self.state_manager.save_job_state(job_id, state)
            
            logger.info(f"任務 {job_id} 使用語言: {used_language}，偵測語言: {auto_detected_language}，不符: {language_mismatch}")
            lang_names = {'en': 'English', 'zh': '中文', 'zh-TW': '繁體中文', 'zh-CN': '簡體中文', 'ms': 'Bahasa Melayu'}
            detected_name = lang_names.get(used_language, used_language)
            self.update_job_progress(job_id, 40, f"語音辨識完成（偵測到 {detected_name}）")
            
            # 階段 2: 翻譯 (40-80%)
            state.status = JobStatus.TRANSLATING
            self.state_manager.save_job_state(job_id, state)
            
            # 使用用戶選擇的目標語言
            if state.target_languages:
                target_languages = list(state.target_languages)
                logger.info(f"任務 {job_id} 使用用戶選擇的語言: {', '.join(target_languages)}")
            else:
                logger.warning(f"任務 {job_id} 未指定目標語言，跳過翻譯")
                target_languages = []
            
            translations = {}
            
            for idx, lang in enumerate(target_languages):
                progress = 40 + int((idx + 1) / len(target_languages) * 40) if target_languages else 80
                lang_names = {'en': 'English', 'zh': '中文', 'zh-TW': '繁體中文', 'zh-CN': '簡體中文', 'ms': 'Bahasa Melayu'}
                lang_display = lang_names.get(lang, lang)
                self.update_job_progress(job_id, progress, f"正在翻譯成 {lang_display}…")
                
                translated_segments = await self.translation_service.translate_segments(
                    source_segments,
                    used_language,
                    lang
                )
                translations[lang] = translated_segments
            
            # 階段 3: 生成字幕檔案 (80-100%)
            state.status = JobStatus.GENERATING
            self.state_manager.save_job_state(job_id, state)
            self.update_job_progress(job_id, 85, "正在產生字幕檔案，即將完成…")
            
            # 確保字幕目錄存在
            subtitle_dir = self.file_storage.ensure_subtitle_dir(job_id)
            
            # 生成主要語言字幕檔案（直接來自轉錄結果）
            subtitle_files = {}
            primary_lang = state.primary_language or used_language
            primary_path = self.file_storage.get_subtitle_path(job_id, primary_lang)
            self.subtitle_generator.generate_vtt(source_segments, primary_path, primary_lang)
            subtitle_files[primary_lang] = primary_path
            logger.info(f"已生成主要語言字幕: {primary_lang}")
            
            # 生成翻譯語言的字幕檔案
            for lang, segments in translations.items():
                lang_path = self.file_storage.get_subtitle_path(job_id, lang)
                self.subtitle_generator.generate_vtt(segments, lang_path, lang)
                subtitle_files[lang] = lang_path
            
            # 標記為完成
            self.mark_job_completed(job_id, subtitle_files)
            
        except Exception as e:
            logger.error(f"處理任務 {job_id} 時發生錯誤: {e}")
            self.mark_job_failed(job_id, str(e))
            
            # 清理失敗任務的檔案
            try:
                self.file_storage.cleanup_job_files(job_id)
            except Exception as cleanup_error:
                logger.error(f"清理失敗任務檔案時發生錯誤: {cleanup_error}")
            
            raise
