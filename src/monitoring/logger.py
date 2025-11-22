import logging
import sys
from datetime import datetime
from pathlib import Path
from src.config import LOGS_DIR

# ANSI color codes
class LogColors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Foreground colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels"""
    
    FORMATS = {
        logging.DEBUG: LogColors.CYAN + '%(asctime)s - %(name)s - [DEBUG] %(message)s' + LogColors.RESET,
        logging.INFO: LogColors.GREEN + '%(asctime)s - %(name)s - [INFO] %(message)s' + LogColors.RESET,
        logging.WARNING: LogColors.YELLOW + '%(asctime)s - %(name)s - [WARNING] %(message)s' + LogColors.RESET,
        logging.ERROR: LogColors.RED + '%(asctime)s - %(name)s - [ERROR] %(message)s' + LogColors.RESET,
        logging.CRITICAL: LogColors.BRIGHT_RED + LogColors.BOLD + '%(asctime)s - %(name)s - [CRITICAL] %(message)s' + LogColors.RESET,
    }
    
    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)


def setup_logger(name: str, level=logging.INFO) -> logging.Logger:
    """
    Setup a colored logger that logs to both console and file.
    
    Usage:
        from src.monitoring.logger import setup_logger
        logger = setup_logger(__name__)
        logger.info("This is an info message")
        logger.error("This is an error message")
    """
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Ensure logs directory exists
    LOGS_DIR.mkdir(exist_ok=True)
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(ColoredFormatter())
    
    # File handler without colors
    log_file = LOGS_DIR / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger