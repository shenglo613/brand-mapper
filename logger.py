"""
日誌工具模組

此模組提供統一的日誌記錄功能，使用 loguru 作為日誌庫。
"""

from loguru import logger
import sys
from pathlib import Path

# 移除預設的處理器
logger.remove()

# 設定日誌格式
file_format = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {function} | {message}"
console_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{function}</cyan> | <white>{message}</white>"

# 設定控制台輸出
logger.add(
    sys.stdout,
    format=console_format,
    level="INFO",
    colorize=True,
    backtrace=True,
    diagnose=True,
)

# 設定檔案輸出
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# 主日誌檔案
logger.add(
    log_dir / "app.log",
    rotation="1 day",
    retention="7 days",
    format=file_format,
    level="INFO",
    encoding="utf-8",
    backtrace=True,
    diagnose=True,
)

# 錯誤日誌檔案
logger.add(
    log_dir / "error.log",
    rotation="1 day",
    retention="7 days",
    format=file_format,
    level="ERROR",
    encoding="utf-8",
    backtrace=True,
    diagnose=True,
)


# 提供一個方便使用的函數
def get_logger():
    """
    獲取配置好的 logger 實例

    返回：
        logger: 配置好的 loguru logger 實例
    """
    return logger
