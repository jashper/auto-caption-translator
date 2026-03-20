"""
任務管理器
管理任務的生命週期和處理流程
"""
import uuid
from datetime import datetime
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
    
    def create_job(self, video_filename: str, video_path: str, target_languages: List[str] = None) -> str:
        """
        建立新任務
        
        Args:
            video_filename: 影片檔名
            video_path: 影片檔案路徑
            target_languages: 目標翻譯語言列表
            
        Returns:
            任務識別碼
        """
        # 生成任務 ID
        job_id = str(uuid.uuid4())
        
        # 預設語言
        if target_languages is None:
            target_languages = ["zh-TW", "zh-CN", "ms"]
        
        # 建立任務狀態
        now = datetime.now()
        state = JobState(
            job_id=job_id,
            status=JobStatus.QUEUED,
            progress=0,
            stage="已加入佇列",
            video_filename=video_filename,
            video_path=video_path,
            target_languages=target_languages,
            created_at=now,
            updated_at=now
        )
        
        # 儲存狀態
        self.state_manager.save_job_state(job_id, state)
        
        logger.info(f"已建立任務: {job_id} ({video_filename}, 語言: {', '.join(target_languages)})")
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
            self.update_job_progress(job_id, 5, "正在轉錄影片...")
            state.status = JobStatus.TRANSCRIBING
            self.state_manager.save_job_state(job_id, state)
            
            english_segments = await self.transcription_service.transcribe(state.video_path)
            self.update_job_progress(job_id, 40, "轉錄完成")
            
            # 階段 2: 翻譯 (40-80%)
            state.status = JobStatus.TRANSLATING
            self.state_manager.save_job_state(job_id, state)
            
            translations = {}
            target_languages = state.target_languages
            
            for idx, lang in enumerate(target_languages):
                progress = 40 + int((idx + 1) / len(target_languages) * 40)
                self.update_job_progress(job_id, progress, f"正在翻譯成 {lang}...")
                
                translated_segments = await self.translation_service.translate_segments(
                    english_segments,
                    lang
                )
                translations[lang] = translated_segments
            
            # 階段 3: 生成字幕檔案 (80-100%)
            state.status = JobStatus.GENERATING
            self.state_manager.save_job_state(job_id, state)
            self.update_job_progress(job_id, 85, "正在生成字幕檔案...")
            
            # 確保字幕目錄存在
            subtitle_dir = self.file_storage.ensure_subtitle_dir(job_id)
            
            # 生成所有語言的字幕檔案
            subtitle_files = {}
            
            # 英文字幕
            en_path = self.file_storage.get_subtitle_path(job_id, "en")
            self.subtitle_generator.generate_vtt(english_segments, en_path, "en")
            subtitle_files["en"] = en_path
            
            # 翻譯後的字幕
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
