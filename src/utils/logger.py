"""
日誌系統配置
提供統一的日誌記錄介面
"""
import logging
import sys
from pathlib import Path
from pythonjsonlogger import jsonlogger

from src.config import LOG_LEVEL, LOG_FILE, LOG_DIR, TRANSLATION_METRICS_LOG

# 確保日誌目錄存在
LOG_DIR.mkdir(parents=True, exist_ok=True)

def setup_logger(name: str = "video-subtitle-translator") -> logging.Logger:
    """
    設定並返回日誌記錄器
    
    Args:
        name: 日誌記錄器名稱
        
    Returns:
        配置好的日誌記錄器
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # 避免重複添加 handler
    if logger.handlers:
        return logger
    
    # 控制台 handler（人類可讀格式）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # 檔案 handler（JSON 格式，便於解析）
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    json_formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(json_formatter)
    
    # 添加 handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# 建立預設日誌記錄器
logger = setup_logger()

def get_logger(name: str) -> logging.Logger:
    """
    獲取指定名稱的日誌記錄器
    
    Args:
        name: 日誌記錄器名稱
        
    Returns:
        日誌記錄器
    """
    return logging.getLogger(f"video-subtitle-translator.{name}")


def get_metrics_logger() -> logging.Logger:
    """
    獲取翻譯 metrics 專用日誌記錄器
    寫入獨立檔案 logs/translation_metrics.log
    """
    metrics_logger = logging.getLogger("translation_metrics")
    metrics_logger.setLevel(logging.INFO)
    
    # 避免重複添加 handler
    if metrics_logger.handlers:
        return metrics_logger
    
    handler = logging.FileHandler(TRANSLATION_METRICS_LOG, encoding='utf-8')
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    metrics_logger.addHandler(handler)
    
    # 不要把訊息往上層 logger 傳（避免重複出現在 app.log）
    metrics_logger.propagate = False
    
    return metrics_logger
