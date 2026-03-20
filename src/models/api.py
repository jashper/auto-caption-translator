"""
API 回應模型
使用 Pydantic 定義所有 API 回應格式
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """上傳回應"""
    job_id: str = Field(..., description="任務識別碼")
    status: str = Field(..., description="任務狀態")
    message: str = Field(..., description="回應訊息")


class JobStatusResponse(BaseModel):
    """任務狀態回應"""
    job_id: str = Field(..., description="任務識別碼")
    status: str = Field(..., description="任務狀態")
    progress: int = Field(..., ge=0, le=100, description="進度百分比")
    stage: str = Field(..., description="當前階段")
    error_message: Optional[str] = Field(None, description="錯誤訊息")
    subtitle_files: Optional[dict[str, str]] = Field(None, description="字幕檔案路徑")


class SubtitlePreview(BaseModel):
    """字幕預覽項目"""
    index: int = Field(..., description="片段索引")
    start_time: str = Field(..., description="開始時間")
    end_time: str = Field(..., description="結束時間")
    text: str = Field(..., description="字幕文字")


class PreviewResponse(BaseModel):
    """預覽回應"""
    job_id: str = Field(..., description="任務識別碼")
    language: str = Field(..., description="語言代碼")
    subtitles: List[SubtitlePreview] = Field(..., description="字幕列表")


class HealthResponse(BaseModel):
    """健康檢查回應"""
    status: str = Field(..., description="系統狀態")
    active_jobs: int = Field(..., description="活躍任務數量")
    queue_size: int = Field(..., description="佇列大小")
    disk_space_gb: float = Field(..., description="可用磁碟空間 (GB)")
    whisper_model_loaded: bool = Field(..., description="Whisper 模型是否已載入")


class ErrorResponse(BaseModel):
    """錯誤回應"""
    error: str = Field(..., description="錯誤訊息")
    error_code: str = Field(..., description="錯誤代碼")
    details: Optional[str] = Field(None, description="詳細資訊")
