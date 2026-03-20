"""
狀態管理器
處理任務狀態的持久化和查詢
"""
import json
from pathlib import Path
from typing import Optional

from src.models.job import JobState
from src.storage.file_storage import FileStorage
from src.utils.logger import get_logger

logger = get_logger("state_manager")


class StateManager:
    """任務狀態管理器"""
    
    def __init__(self, file_storage: Optional[FileStorage] = None):
        """
        初始化狀態管理器
        
        Args:
            file_storage: 檔案儲存管理器
        """
        self.file_storage = file_storage or FileStorage()
    
    def save_job_state(self, job_id: str, state: JobState) -> None:
        """
        儲存任務狀態
        
        Args:
            job_id: 任務識別碼
            state: 任務狀態
        """
        try:
            state_path = self.file_storage.get_job_state_path(job_id)
            state_dict = state.to_dict()
            
            with open(state_path, 'w', encoding='utf-8') as f:
                json.dump(state_dict, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"已儲存任務 {job_id} 的狀態")
        except Exception as e:
            logger.error(f"儲存任務 {job_id} 狀態時發生錯誤: {e}")
            raise
    
    def load_job_state(self, job_id: str) -> JobState:
        """
        載入任務狀態
        
        Args:
            job_id: 任務識別碼
            
        Returns:
            任務狀態
            
        Raises:
            FileNotFoundError: 任務狀態檔案不存在
        """
        try:
            state_path = self.file_storage.get_job_state_path(job_id)
            
            if not Path(state_path).exists():
                raise FileNotFoundError(f"找不到任務 {job_id} 的狀態檔案")
            
            with open(state_path, 'r', encoding='utf-8') as f:
                state_dict = json.load(f)
            
            state = JobState.from_dict(state_dict)
            logger.debug(f"已載入任務 {job_id} 的狀態")
            return state
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"載入任務 {job_id} 狀態時發生錯誤: {e}")
            raise
    
    def update_progress(self, job_id: str, progress: int, stage: str) -> None:
        """
        更新任務進度
        
        Args:
            job_id: 任務識別碼
            progress: 進度百分比
            stage: 階段描述
        """
        try:
            state = self.load_job_state(job_id)
            state.update_progress(progress, stage)
            self.save_job_state(job_id, state)
            logger.info(f"任務 {job_id} 進度更新: {progress}% - {stage}")
        except Exception as e:
            logger.error(f"更新任務 {job_id} 進度時發生錯誤: {e}")
            raise
    
    def job_exists(self, job_id: str) -> bool:
        """
        檢查任務是否存在
        
        Args:
            job_id: 任務識別碼
            
        Returns:
            任務是否存在
        """
        state_path = self.file_storage.get_job_state_path(job_id)
        return Path(state_path).exists()
