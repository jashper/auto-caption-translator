"""
任務佇列管理器
控制並發處理數量和任務排程
"""
import asyncio
from typing import Optional

from src.config import MAX_CONCURRENT_JOBS
from src.utils.logger import get_logger

logger = get_logger("task_queue")


class TaskQueue:
    """任務佇列管理器"""
    
    def __init__(self, max_concurrent_jobs: int = MAX_CONCURRENT_JOBS):
        """
        初始化任務佇列
        
        Args:
            max_concurrent_jobs: 最大並發任務數量
        """
        self.max_concurrent_jobs = max_concurrent_jobs
        self.semaphore = asyncio.Semaphore(max_concurrent_jobs)
        self.queue = asyncio.Queue()
        self.active_jobs = set()
        self._worker_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """啟動佇列處理器"""
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._process_queue())
            logger.info("任務佇列處理器已啟動")
    
    async def stop(self) -> None:
        """停止佇列處理器"""
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            logger.info("任務佇列處理器已停止")
    
    async def enqueue(self, job_id: str, process_func, *args, **kwargs) -> None:
        """
        將任務加入佇列
        
        Args:
            job_id: 任務識別碼
            process_func: 處理函數
            *args: 位置參數
            **kwargs: 關鍵字參數
        """
        await self.queue.put((job_id, process_func, args, kwargs))
        logger.info(f"任務 {job_id} 已加入佇列，當前佇列大小: {self.queue.qsize()}")
    
    async def _run_job(self, job_id: str, process_func, args, kwargs) -> None:
        """在 semaphore 控制下執行單一任務"""
        async with self.semaphore:
            self.active_jobs.add(job_id)
            logger.info(f"開始處理任務 {job_id}，活躍任務數: {len(self.active_jobs)}")
            try:
                await process_func(*args, **kwargs)
            except Exception as e:
                logger.error(f"處理任務 {job_id} 時發生錯誤: {e}")
            finally:
                self.active_jobs.discard(job_id)
                self.queue.task_done()
                logger.info(f"任務 {job_id} 處理完成，活躍任務數: {len(self.active_jobs)}")

    async def _process_queue(self) -> None:
        """處理佇列中的任務（每個任務獨立啟動，支援真正的並發）"""
        while True:
            try:
                # 從佇列取出任務
                job_id, process_func, args, kwargs = await self.queue.get()
                
                # 以獨立 Task 執行，不阻塞佇列取出下一個任務
                asyncio.create_task(self._run_job(job_id, process_func, args, kwargs))
            except asyncio.CancelledError:
                logger.info("佇列處理器收到取消信號")
                break
            except Exception as e:
                logger.error(f"佇列處理器發生錯誤: {e}")
    
    def get_queue_size(self) -> int:
        """
        取得佇列大小
        
        Returns:
            佇列中等待的任務數量
        """
        return self.queue.qsize()
    
    def get_active_jobs_count(self) -> int:
        """
        取得活躍任務數量
        
        Returns:
            正在處理的任務數量
        """
        return len(self.active_jobs)
    
    def is_slot_available(self) -> bool:
        """
        檢查是否有可用槽位
        
        Returns:
            是否有可用槽位
        """
        return len(self.active_jobs) < self.max_concurrent_jobs
