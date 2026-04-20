"""
任務狀態資料模型
定義任務狀態和相關方法
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class JobStatus(str, Enum):
    """任務狀態枚舉"""
    QUEUED = "queued"
    PROCESSING = "processing"
    TRANSCRIBING = "transcribing"
    TRANSLATING = "translating"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class JobState:
    """
    任務狀態資料結構
    
    Attributes:
        job_id: 任務唯一識別碼
        status: 當前狀態
        progress: 進度百分比 (0-100)
        stage: 當前階段描述
        video_filename: 原始影片檔名
        video_path: 影片檔案路徑
        target_languages: 目標翻譯語言列表
        created_at: 建立時間
        updated_at: 更新時間
        completed_at: 完成時間
        error_message: 錯誤訊息
        detected_language: 檢測到的原語言代碼 (例如: 'en', 'zh', 'ms')
        subtitle_files: 字幕檔案路徑字典 {language: file_path}
    """
    job_id: str
    status: JobStatus
    progress: int
    stage: str
    video_filename: str
    video_path: str
    target_languages: List[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    detected_language: Optional[str] = None
    source_language: Optional[str] = None
    primary_language: Optional[str] = None
    language_distribution: Optional[dict] = None
    language_mismatch: bool = False
    subtitle_files: dict[str, str] = field(default_factory=dict)
    estimated_seconds: Optional[float] = None
    
    def __post_init__(self):
        """驗證資料有效性"""
        if not 0 <= self.progress <= 100:
            raise ValueError("progress 必須在 0-100 之間")
    
    def to_dict(self) -> dict:
        """
        轉換為字典格式（用於 JSON 序列化）
        
        Returns:
            字典表示
        """
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "progress": self.progress,
            "stage": self.stage,
            "video_filename": self.video_filename,
            "video_path": self.video_path,
            "target_languages": self.target_languages,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "detected_language": self.detected_language,
            "source_language": self.source_language,
            "primary_language": self.primary_language,
            "language_distribution": self.language_distribution,
            "language_mismatch": self.language_mismatch,
            "subtitle_files": self.subtitle_files,
            "estimated_seconds": self.estimated_seconds
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "JobState":
        """
        從字典建立實例
        
        Args:
            data: 字典資料
            
        Returns:
            JobState 實例
        """
        # 轉換狀態枚舉
        data["status"] = JobStatus(data["status"])
        
        # 轉換時間戳
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        if data.get("completed_at"):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
        
        # 向後相容：舊任務可能沒有新欄位
        data.setdefault("primary_language", data.get("source_language"))
        data.setdefault("language_distribution", None)
        data.setdefault("language_mismatch", False)
        
        # 過濾未知欄位（向後相容）
        import dataclasses
        valid_fields = {f.name for f in dataclasses.fields(cls)}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        
        return cls(**filtered)
    
    def update_progress(self, progress: int, stage: str) -> None:
        """
        更新進度
        
        Args:
            progress: 進度百分比
            stage: 階段描述
        """
        if not 0 <= progress <= 100:
            raise ValueError("progress 必須在 0-100 之間")
        
        self.progress = progress
        self.stage = stage
        self.updated_at = datetime.now()
    
    def mark_completed(self, subtitle_files: dict[str, str]) -> None:
        """
        標記為完成
        
        Args:
            subtitle_files: 字幕檔案路徑字典
        """
        self.status = JobStatus.COMPLETED
        self.progress = 100
        self.stage = "已完成"
        self.subtitle_files = subtitle_files
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()
    
    def mark_failed(self, error_message: str) -> None:
        """
        標記為失敗
        
        Args:
            error_message: 錯誤訊息
        """
        self.status = JobStatus.FAILED
        self.error_message = error_message
        self.updated_at = datetime.now()
