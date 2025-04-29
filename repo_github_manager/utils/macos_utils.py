"""
macOS 시스템 유틸리티 모듈
macOS 권한 확인 및 시스템 정보 관련 기능을 제공합니다.
"""
import os
import subprocess
import platform
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional

from utils.logger import setup_logger

# 로거 설정
logger = setup_logger(__name__)


def check_macos_version() -> Tuple[bool, str]:
    """
    현재 실행 중인 macOS 버전을 확인합니다.
    
    Returns:
        Tuple[bool, str]: (macOS 여부, 버전 정보)
    """
    if platform.system() != "Darwin":
        return False, "이 애플리케이션은 macOS에서만 실행할 수 있습니다."
    
    version = platform.mac_ver()[0]
    logger.info(f"현재 macOS 버전: {version}")
    return True, version


def check_file_permission(path: str) -> bool:
    """
    지정된 경로에 파일 시스템 권한이 있는지 확인합니다.
    
    Args:
        path (str): 확인할 경로
        
    Returns:
        bool: 권한 여부
    """
    try:
        test_file = os.path.join(path, ".permission_test")
        with open(test_file, "w") as f:
            f.write("test")
        
        os.remove(test_file)
        return True
    except (PermissionError, IOError, OSError) as e:
        logger.warning(f"경로에 쓰기 권한이 없습니다: {path} - {str(e)}")
        return False
    except Exception as e:
        logger.error(f"권한 확인 중 오류 발생: {str(e)}")
        return False


def is_git_installed() -> bool:
    """
    Git이 설치되어 있는지 확인합니다.
    
    Returns:
        bool: Git 설치 여부
    """
    try:
        result = subprocess.run(
            ["git", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            version = result.stdout.strip()
            logger.info(f"Git 설치 확인: {version}")
            return True
        else:
            logger.warning("Git이 설치되어 있지 않습니다.")
            return False
    except Exception as e:
        logger.error(f"Git 설치 확인 중 오류 발생: {str(e)}")
        return False


def check_system_requirements() -> Dict[str, Any]:
    """
    애플리케이션 실행을 위한 시스템 요구사항을 확인합니다.
    
    Returns:
        Dict[str, Any]: 시스템 요구사항 충족 여부
    """
    # macOS 버전 확인
    is_macos, macos_version = check_macos_version()
    
    # Git 설치 확인
    git_available = is_git_installed()
    
    # 설정 디렉토리 권한 확인
    config_dir = Path.home() / ".github_repo_manager"
    os.makedirs(config_dir, exist_ok=True)
    config_permission = check_file_permission(str(config_dir))
    
    # 홈 디렉토리 권한 확인
    home_permission = check_file_permission(str(Path.home()))
    
    return {
        "is_macos": is_macos,
        "macos_version": macos_version,
        "git_available": git_available,
        "config_permission": config_permission,
        "home_permission": home_permission,
        "all_requirements_met": is_macos and git_available and config_permission
    } 