"""
檔案驗證器
驗證上傳的影片檔案是否符合要求
"""
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import ffmpeg

from src.config import (
    SUPPORTED_VIDEO_FORMATS,
    MAX_FILE_SIZE,
    MAX_VIDEO_DURATION,
    MIN_DISK_SPACE
)
from src.utils.logger import get_logger

logger = get_logger("validator")


@dataclass
class ValidationResult:
    """
    驗證結果資料結構
    
    Attributes:
        is_valid: 是否通過驗證
        error_message: 錯誤訊息
        error_code: 錯誤代碼
    """
    is_valid: bool
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    
    @classmethod
    def success(cls) -> "ValidationResult":
        """建立成功結果"""
        return cls(is_valid=True)
    
    @classmethod
    def failure(cls, error_message: str, error_code: str) -> "ValidationResult":
        """建立失敗結果"""
        return cls(is_valid=False, error_message=error_message, error_code=error_code)


# UUID 格式：8-4-4-4-12 的十六進位字元
UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)


class Validator:
    """檔案驗證器"""
    
    def __init__(self):
        """初始化驗證器"""
        self.supported_formats = SUPPORTED_VIDEO_FORMATS
        self.max_file_size = MAX_FILE_SIZE
        self.max_duration = MAX_VIDEO_DURATION
        self.min_disk_space = MIN_DISK_SPACE
    
    def validate_job_id(self, job_id: str) -> ValidationResult:
        """
        驗證 job_id 是否為合法 UUID 格式，防止路徑注入攻擊
        
        Args:
            job_id: 任務識別碼
            
        Returns:
            驗證結果
        """
        if not job_id or not UUID_PATTERN.match(job_id):
            logger.warning(f"可疑請求：無效的 job_id 格式: {job_id}")
            return ValidationResult.failure("無效的任務 ID", "INVALID_JOB_ID")
        return ValidationResult.success()
    
    def validate_file_format(self, filename: str) -> bool:
        """
        驗證檔案格式
        
        Args:
            filename: 檔案名稱
            
        Returns:
            是否為支援的格式
        """
        ext = Path(filename).suffix.lower()
        return ext in self.supported_formats
    
    def validate_file_size(self, size: int) -> ValidationResult:
        """
        驗證檔案大小
        
        Args:
            size: 檔案大小（bytes）
            
        Returns:
            驗證結果
        """
        if size > self.max_file_size:
            size_gb = size / (1024 * 1024 * 1024)
            max_gb = self.max_file_size / (1024 * 1024 * 1024)
            return ValidationResult.failure(
                f"檔案大小 {size_gb:.2f}GB 超過限制 {max_gb:.0f}GB",
                "FILE_TOO_LARGE"
            )
        return ValidationResult.success()
    
    def validate_video_duration(self, video_path: str) -> ValidationResult:
        """
        驗證影片時長
        
        Args:
            video_path: 影片檔案路徑
            
        Returns:
            驗證結果
        """
        try:
            probe = ffmpeg.probe(video_path)
            duration = float(probe['format']['duration'])
            
            if duration > self.max_duration:
                duration_hours = duration / 3600
                max_hours = self.max_duration / 3600
                return ValidationResult.failure(
                    f"影片時長 {duration_hours:.1f} 小時超過限制 {max_hours:.0f} 小時",
                    "VIDEO_TOO_LONG"
                )
            
            return ValidationResult.success()
        except ffmpeg.Error as e:
            logger.error(f"無法解析影片檔案: {e}")
            return ValidationResult.failure(
                "影片檔案無法解析，請確認檔案完整且未損壞",
                "VIDEO_PARSE_FAILED"
            )
        except Exception as e:
            logger.error(f"驗證影片時長時發生錯誤: {e}")
            return ValidationResult.failure(
                "驗證影片時長時發生錯誤",
                "VALIDATION_ERROR"
            )
    
    def validate_disk_space(self) -> ValidationResult:
        """
        驗證磁碟空間
        
        Returns:
            驗證結果
        """
        try:
            stat = shutil.disk_usage("/")
            free_space = stat.free
            
            if free_space < self.min_disk_space:
                free_gb = free_space / (1024 * 1024 * 1024)
                min_gb = self.min_disk_space / (1024 * 1024 * 1024)
                return ValidationResult.failure(
                    f"磁碟剩餘空間 {free_gb:.2f}GB 不足，需要至少 {min_gb:.0f}GB",
                    "INSUFFICIENT_DISK_SPACE"
                )
            
            return ValidationResult.success()
        except Exception as e:
            logger.error(f"檢查磁碟空間時發生錯誤: {e}")
            return ValidationResult.failure(
                "檢查磁碟空間時發生錯誤",
                "DISK_CHECK_ERROR"
            )
    
    def validate_video_file(self, filename: str, file_size: int, file_path: Optional[str] = None) -> ValidationResult:
        """
        驗證影片檔案（完整驗證）
        
        Args:
            filename: 檔案名稱
            file_size: 檔案大小
            file_path: 檔案路徑（用於驗證時長）
            
        Returns:
            驗證結果
        """
        # 驗證檔案格式
        if not self.validate_file_format(filename):
            return ValidationResult.failure(
                f"不支援的檔案格式，僅支援 {', '.join(self.supported_formats)}",
                "INVALID_FORMAT"
            )
        
        # 驗證檔案大小
        size_result = self.validate_file_size(file_size)
        if not size_result.is_valid:
            return size_result
        
        # 驗證磁碟空間
        disk_result = self.validate_disk_space()
        if not disk_result.is_valid:
            return disk_result
        
        # 如果提供了檔案路徑，驗證影片時長
        if file_path and os.path.exists(file_path):
            duration_result = self.validate_video_duration(file_path)
            if not duration_result.is_valid:
                return duration_result
        
        return ValidationResult.success()
