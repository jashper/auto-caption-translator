"""
資源清理工具
定時清理舊檔案和失敗任務
"""
import asyncio
from datetime import datetime, timedelta

from src.storage.file_storage import FileStorage
from src.config import CLEANUP_HOURS
from src.utils.logger import get_logger

logger = get_logger("cleanup")


async def cleanup_failed_job(job_id: str, file_storage: FileStorage = None) -> None:
    """
    清理失敗任務的資源
    
    Args:
        job_id: 任務識別碼
        file_storage: 檔案儲存管理器
    """
    if file_storage is None:
        file_storage = FileStorage()
    
    try:
        file_storage.cleanup_job_files(job_id)
        logger.info(f"已清理失敗任務 {job_id} 的資源")
    except Exception as e:
        logger.error(f"清理失敗任務 {job_id} 時發生錯誤: {e}")


async def scheduled_cleanup(file_storage: FileStorage = None, hours: int = CLEANUP_HOURS) -> None:
    """
    定時清理舊檔案（每小時執行一次）
    
    Args:
        file_storage: 檔案儲存管理器
        hours: 保留時間（小時）
    """
    if file_storage is None:
        file_storage = FileStorage()
    
    logger.info(f"啟動定時清理任務，保留時間: {hours} 小時")
    
    while True:
        try:
            deleted_count = file_storage.cleanup_old_files(hours)
            if deleted_count > 0:
                logger.info(f"定時清理完成，刪除 {deleted_count} 個舊檔案/目錄")
        except Exception as e:
            logger.error(f"定時清理失敗: {e}")
        
        # 每小時執行一次
        await asyncio.sleep(3600)
