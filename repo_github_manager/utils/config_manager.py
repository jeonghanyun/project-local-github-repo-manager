"""
설정 관리 모듈
GitHub PAT와 같은 민감한 정보 및 애플리케이션 설정을 관리합니다.
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# 로거 설정
logger = logging.getLogger(__name__)

# 애플리케이션 기본 설정
DEFAULT_CONFIG = {
    "clone_base_path": str(Path.home() / "github_repos"),
    "default_branch": "main",
    "log_level": "INFO",
}

# 애플리케이션 설정 파일 경로
CONFIG_PATH = Path.home() / ".github_repo_manager" / "config.json"


def load_github_pat() -> Optional[str]:
    """
    .env 파일에서 GitHub 개인 액세스 토큰을 로드합니다.
    
    Returns:
        Optional[str]: GitHub PAT 또는 None (로드 실패 시)
    """
    try:
        load_dotenv()
        github_pat = os.getenv("GITHUB_PAT")
        if not github_pat:
            logger.warning("GITHUB_PAT가 .env 파일에 설정되지 않았습니다.")
            return None
        return github_pat
    except Exception as e:
        logger.error(f".env 파일 로드 중 오류 발생: {e}")
        return None


def load_app_config() -> Dict[str, Any]:
    """
    애플리케이션 설정을 로드합니다. 설정 파일이 없으면 기본 설정을 반환합니다.
    
    Returns:
        Dict[str, Any]: 애플리케이션 설정
    """
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
            # 기본 설정과 병합하여 누락된 설정이 있으면 기본값 사용
            merged_config = DEFAULT_CONFIG.copy()
            merged_config.update(config)
            return merged_config
        else:
            logger.info("설정 파일이 없습니다. 기본 설정을 사용합니다.")
            return DEFAULT_CONFIG.copy()
    except Exception as e:
        logger.error(f"설정 로드 중 오류 발생: {e}")
        return DEFAULT_CONFIG.copy()


def save_app_config(config: Dict[str, Any]) -> bool:
    """
    애플리케이션 설정을 저장합니다.
    
    Args:
        config (Dict[str, Any]): 저장할 설정
        
    Returns:
        bool: 저장 성공 여부
    """
    try:
        # 설정 디렉토리가 없으면 생성
        os.makedirs(CONFIG_PATH.parent, exist_ok=True)
        
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        logger.info("설정이 저장되었습니다.")
        return True
    except Exception as e:
        logger.error(f"설정 저장 중 오류 발생: {e}")
        return False


def get_clone_base_path() -> str:
    """
    리포지토리 클론 기본 경로를 반환합니다.
    
    Returns:
        str: 클론 기본 경로
    """
    config = load_app_config()
    return config.get("clone_base_path", DEFAULT_CONFIG["clone_base_path"])


def set_clone_base_path(path: str) -> bool:
    """
    리포지토리 클론 기본 경로를 설정합니다.
    
    Args:
        path (str): 설정할 경로
        
    Returns:
        bool: 설정 성공 여부
    """
    config = load_app_config()
    config["clone_base_path"] = path
    return save_app_config(config) 