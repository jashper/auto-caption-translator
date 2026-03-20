"""
檔案儲存管理
處理影片和字幕檔案的儲存、讀取和清理
"""
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from fastapi import UploadFile

from src.config import (
    STORAGE_BASE_DIR,
    UPLOAD_DIR,
    SUBTITLE_DIR,
    JOB_DIR,
    CLEANUP_HOURS
)
from src.utils.logger import get_logger

logger = get_logger("file_storage")


class FileStorage:
    """檔案儲存管理器"""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        初始化檔案儲存管理器
        
        Args:
            base_dir: 基礎目錄（用於測試時覆蓋）
        """
        self.base_dir = base_dir or STORAGE_BASE_DIR
        self.upload_dir = self.base_dir / "uploads"
        self.subtitle_dir = self.base_dir / "subtitles"
        self.job_dir = self.base_dir / "jobs"
        
        # 確保目錄存在
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """確保所有必要目錄存在"""
        for directory in [self.base_dir, self.upload_dir, self.subtitle_dir, self.job_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    async def save_uploaded_file(self, file: UploadFile, job_id: str) -> str:
        """
        儲存上傳的檔案
        
        Args:
            file: 上傳的檔案
            job_id: 任務識別碼
            
        Returns:
            儲存的檔案路徑
        """
        # 取得檔案副檔名
        ext = Path(file.filename).suffix
        file_path = self.upload_dir / f"{job_id}{ext}"
        
        try:
            # 寫入檔案
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            logger.info(f"已儲存上傳檔案: {file_path}")
            return str(file_path)
        except Exception as e:
            logger.error(f"儲存上傳檔案失敗: {e}")
            raise
    
    def get_video_path(self, job_id: str) -> str:
        """
        取得影片檔案路徑
        
        Args:
            job_id: 任務識別碼
            
        Returns:
            影片檔案路徑
        """
        # 尋找符合的檔案（可能有不同副檔名）
        for ext in [".mp4", ".avi", ".mov", ".mkv"]:
            path = self.upload_dir / f"{job_id}{ext}"
            if path.exists():
                return str(path)
        
        raise FileNotFoundError(f"找不到任務 {job_id} 的影片檔案")
    
    def get_subtitle_path(self, job_id: str, language: str) -> str:
        """
        取得字幕檔案路徑
        
        Args:
            job_id: 任務識別碼
            language: 語言代碼
            
        Returns:
            字幕檔案路徑
        """
        subtitle_job_dir = self.subtitle_dir / job_id
        return str(subtitle_job_dir / f"{language}.vtt")
    
    def get_subtitle_dir(self, job_id: str) -> Path:
        """
        取得字幕目錄路徑
        
        Args:
            job_id: 任務識別碼
            
        Returns:
            字幕目錄路徑
        """
        return self.subtitle_dir / job_id
    
    def ensure_subtitle_dir(self, job_id: str) -> Path:
        """
        確保字幕目錄存在
        
        Args:
            job_id: 任務識別碼
            
        Returns:
            字幕目錄路徑
        """
        subtitle_job_dir = self.subtitle_dir / job_id
        subtitle_job_dir.mkdir(parents=True, exist_ok=True)
        return subtitle_job_dir
    
    def get_job_state_path(self, job_id: str) -> str:
        """
        取得任務狀態檔案路徑
        
        Args:
            job_id: 任務識別碼
            
        Returns:
            任務狀態檔案路徑
        """
        return str(self.job_dir / f"{job_id}.json")
    
    def cleanup_job_files(self, job_id: str) -> None:
        """
        清理任務相關檔案
        
        Args:
            job_id: 任務識別碼
        """
        try:
            # 刪除影片檔案
            try:
                video_path = self.get_video_path(job_id)
                if os.path.exists(video_path):
                    os.remove(video_path)
                    logger.info(f"已刪除影片檔案: {video_path}")
            except FileNotFoundError:
                pass
            
            # 刪除字幕目錄
            subtitle_job_dir = self.get_subtitle_dir(job_id)
            if subtitle_job_dir.exists():
                shutil.rmtree(subtitle_job_dir)
                logger.info(f"已刪除字幕目錄: {subtitle_job_dir}")
            
            # 保留任務狀態檔案（用於查詢歷史記錄）
            logger.info(f"已清理任務 {job_id} 的檔案")
        except Exception as e:
            logger.error(f"清理任務 {job_id} 檔案時發生錯誤: {e}")
    
    def cleanup_old_files(self, hours: int = CLEANUP_HOURS) -> int:
        """
        清理舊檔案（超過指定小時數）
        
        Args:
            hours: 保留時間（小時）
            
        Returns:
            刪除的檔案數量
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        deleted_count = 0
        
        try:
            # 清理舊的影片檔案
            for file_path in self.upload_dir.iterdir():
                if file_path.is_file():
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_time:
                        file_path.unlink()
                        deleted_count += 1
                        logger.debug(f"已刪除舊影片檔案: {file_path}")
            
            # 清理舊的字幕目錄
            for dir_path in self.subtitle_dir.iterdir():
                if dir_path.is_dir():
                    dir_time = datetime.fromtimestamp(dir_path.stat().st_mtime)
                    if dir_time < cutoff_time:
                        shutil.rmtree(dir_path)
                        deleted_count += 1
                        logger.debug(f"已刪除舊字幕目錄: {dir_path}")
            
            # 清理舊的任務狀態檔案
            for file_path in self.job_dir.iterdir():
                if file_path.is_file():
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_time:
                        file_path.unlink()
                        deleted_count += 1
                        logger.debug(f"已刪除舊任務狀態檔案: {file_path}")
            
            if deleted_count > 0:
                logger.info(f"清理完成，共刪除 {deleted_count} 個舊檔案/目錄")
            
            return deleted_count
        except Exception as e:
            logger.error(f"清理舊檔案時發生錯誤: {e}")
            return deleted_count
    
    def get_disk_space(self) -> int:
        """
        取得可用磁碟空間
        
        Returns:
            可用空間（bytes）
        """
        try:
            stat = shutil.disk_usage(str(self.base_dir))
            return stat.free
        except Exception as e:
            logger.error(f"取得磁碟空間時發生錯誤: {e}")
            return 0
