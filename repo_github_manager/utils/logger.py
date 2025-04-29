"""
로깅 시스템 설정 모듈
애플리케이션 전반에서 사용되는 로깅 시스템을 설정합니다.
"""
import os
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from utils.config_manager import load_app_config

# 로그 파일이 저장될 디렉토리
LOG_DIR = Path.home() / ".github_repo_manager" / "logs"


def setup_logger(name: Optional[str] = None) -> logging.Logger:
    """
    로거를 설정하고 반환합니다.
    
    Args:
        name (Optional[str]): 로거 이름 (없으면 루트 로거 사용)
        
    Returns:
        logging.Logger: 설정된 로거
    """
    # 로그 디렉토리 생성
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # 설정에서 로그 레벨 가져오기
    config = load_app_config()
    log_level_str = config.get("log_level", "INFO")
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    # 로거 가져오기
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # 이미 핸들러가 설정되어 있으면 추가 설정 안함
    if logger.handlers:
        return logger
    
    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # 파일 핸들러 설정 (날짜별 로그 파일)
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"app_{today}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(log_level)
    
    # 포맷터 설정
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # 핸들러 추가
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


# 애플리케이션 시작 시 루트 로거 설정
def init_logging():
    """
    애플리케이션 전역 로깅을 초기화합니다.
    """
    root_logger = setup_logger()
    root_logger.info("로깅 시스템이 초기화되었습니다.")
    return root_logger 