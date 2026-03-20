"""
錯誤處理器
定義錯誤代碼和使用者友善訊息
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from src.models.api import ErrorResponse
from src.utils.logger import get_logger

logger = get_logger("error_handler")


# 錯誤代碼和使用者友善訊息對照表
ERROR_MESSAGES = {
    "INVALID_FORMAT": {
        "message": "檔案格式不支援",
        "suggestion": "請上傳 mp4、avi、mov 或 mkv 格式的影片"
    },
    "FILE_TOO_LARGE": {
        "message": "檔案太大",
        "suggestion": "請上傳小於 5GB 的影片檔案"
    },
    "VIDEO_TOO_LONG": {
        "message": "影片時長超過限制",
        "suggestion": "請上傳時長不超過 2 小時的影片"
    },
    "INSUFFICIENT_DISK_SPACE": {
        "message": "伺服器儲存空間不足",
        "suggestion": "請稍後再試，或聯絡管理員"
    },
    "VIDEO_PARSE_FAILED": {
        "message": "影片檔案無法解析",
        "suggestion": "請確認檔案完整且未損壞"
    },
    "TRANSCRIPTION_FAILED": {
        "message": "轉錄失敗",
        "suggestion": "請確認影片包含可辨識的語音內容"
    },
    "TRANSLATION_API_FAILED": {
        "message": "翻譯服務暫時不可用",
        "suggestion": "系統已保留英文字幕，您仍可下載"
    },
    "MODEL_LOAD_FAILED": {
        "message": "系統初始化失敗",
        "suggestion": "請聯絡管理員檢查模型檔案"
    },
    "JOB_NOT_FOUND": {
        "message": "找不到指定的任務",
        "suggestion": "請確認任務 ID 是否正確"
    },
    "FILE_NOT_FOUND": {
        "message": "找不到指定的檔案",
        "suggestion": "檔案可能已被清理，請重新上傳"
    }
}


def get_error_response(error_code: str, details: str = None) -> ErrorResponse:
    """
    取得錯誤回應
    
    Args:
        error_code: 錯誤代碼
        details: 詳細資訊
        
    Returns:
        錯誤回應
    """
    error_info = ERROR_MESSAGES.get(error_code, {
        "message": "發生未知錯誤",
        "suggestion": "請稍後再試"
    })
    
    message = error_info["message"]
    if error_info.get("suggestion"):
        message += f"。{error_info['suggestion']}"
    
    return ErrorResponse(
        error=message,
        error_code=error_code,
        details=details
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    處理請求驗證錯誤
    
    Args:
        request: 請求物件
        exc: 驗證錯誤
        
    Returns:
        JSON 錯誤回應
    """
    logger.warning(f"請求驗證失敗: {exc.errors()}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "請求參數驗證失敗",
            "error_code": "VALIDATION_ERROR",
            "details": str(exc.errors())
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """
    處理一般異常
    
    Args:
        request: 請求物件
        exc: 異常
        
    Returns:
        JSON 錯誤回應
    """
    logger.error(f"發生未處理的異常: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "伺服器內部錯誤",
            "error_code": "INTERNAL_ERROR",
            "details": str(exc)
        }
    )
