"""
配置管理模組
從環境變數載入系統配置
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 專案根目錄
BASE_DIR = Path(__file__).parent.parent

# 伺服器配置
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Whisper 模型配置
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")

# 並發控制
MAX_CONCURRENT_JOBS = int(os.getenv("MAX_CONCURRENT_JOBS", "2"))

# 儲存配置
STORAGE_BASE_DIR = BASE_DIR / os.getenv("STORAGE_BASE_DIR", "storage")
UPLOAD_DIR = STORAGE_BASE_DIR / "uploads"
SUBTITLE_DIR = STORAGE_BASE_DIR / "subtitles"
JOB_DIR = STORAGE_BASE_DIR / "jobs"
CLEANUP_HOURS = int(os.getenv("CLEANUP_HOURS", "24"))

# 日誌配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "app.log"

# 檔案限制
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_GB", "5")) * 1024 * 1024 * 1024  # 轉換為 bytes
MAX_VIDEO_DURATION = int(os.getenv("MAX_VIDEO_DURATION_HOURS", "2")) * 3600  # 轉換為秒
MIN_DISK_SPACE = int(os.getenv("MIN_DISK_SPACE_GB", "1")) * 1024 * 1024 * 1024  # 轉換為 bytes

# 支援的影片格式
SUPPORTED_VIDEO_FORMATS = [".mp4", ".avi", ".mov", ".mkv"]

# 支援的翻譯語言
SUPPORTED_LANGUAGES = {
    "en": "English",
    "zh-TW": "繁體中文",
    "zh-CN": "簡體中文",
    "ms": "Bahasa Melayu"
}

# 確保必要目錄存在
def ensure_directories():
    """確保所有必要的目錄存在"""
    for directory in [STORAGE_BASE_DIR, UPLOAD_DIR, SUBTITLE_DIR, JOB_DIR, LOG_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

# 初始化時建立目錄
ensure_directories()
