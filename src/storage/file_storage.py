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
        self.job_dir = self.base_dir / "jobs"
        
        # 確保目錄存在
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """確保所有必要目錄存在"""
        for directory in [self.base_dir, self.job_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _get_job_folder(self, job_id: str) -> Path:
        """取得任務資料夾路徑"""
        return self.job_dir / job_id
    
    def _ensure_job_folder(self, job_id: str) -> Path:
        """確保任務資料夾存在"""
        folder = self._get_job_folder(job_id)
        folder.mkdir(parents=True, exist_ok=True)
        return folder
    
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
        job_folder = self._ensure_job_folder(job_id)
        file_path = job_folder / f"source{ext}"
        
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
        job_folder = self._get_job_folder(job_id)
        for ext in [".mp4", ".avi", ".mov", ".mkv"]:
            path = job_folder / f"source{ext}"
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
        job_folder = self._get_job_folder(job_id)
        return str(job_folder / f"{language}.vtt")
    
    def get_subtitle_dir(self, job_id: str) -> Path:
        """
        取得字幕目錄路徑（即任務資料夾）
        
        Args:
            job_id: 任務識別碼
            
        Returns:
            字幕目錄路徑
        """
        return self._get_job_folder(job_id)
    
    def ensure_subtitle_dir(self, job_id: str) -> Path:
        """
        確保字幕目錄存在（即任務資料夾）
        
        Args:
            job_id: 任務識別碼
            
        Returns:
            字幕目錄路徑
        """
        return self._ensure_job_folder(job_id)
    
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
            # 刪除任務資料夾（包含影片、音訊、字幕）
            job_folder = self._get_job_folder(job_id)
            if job_folder.exists():
                shutil.rmtree(job_folder)
                logger.info(f"已刪除任務資料夾: {job_folder}")
            
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
            # 清理舊的任務資料夾和狀態檔案
            for entry in self.job_dir.iterdir():
                entry_time = datetime.fromtimestamp(entry.stat().st_mtime)
                if entry_time < cutoff_time:
                    if entry.is_dir():
                        shutil.rmtree(entry)
                        deleted_count += 1
                        logger.debug(f"已刪除舊任務資料夾: {entry}")
                    elif entry.is_file():
                        entry.unlink()
                        deleted_count += 1
                        logger.debug(f"已刪除舊任務狀態檔案: {entry}")
            
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
