"""
Git 명령어 실행 유틸리티 모듈
로컬 Git 명령어를 안전하게 실행하고 결과를 처리합니다.
"""
import os
import subprocess
import shutil
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional, Union

from utils.logger import setup_logger
from utils.config_manager import get_clone_base_path

# 로거 설정
logger = setup_logger(__name__)


def run_git_command(command: List[str], cwd: Optional[str] = None, 
                    timeout: int = 60) -> Tuple[bool, Union[str, Dict[str, Any]]]:
    """
    Git 명령어를 안전하게 실행합니다.
    
    Args:
        command (List[str]): 실행할 Git 명령어와 인자 리스트 (['git', 'status'] 형식)
        cwd (Optional[str], optional): 작업 디렉토리 경로
        timeout (int, optional): 명령어 실행 타임아웃 (초)
    
    Returns:
        Tuple[bool, Union[str, Dict[str, Any]]]: 
            (성공 여부, 결과 또는 오류 메시지)
    """
    try:
        # 보안을 위해 shell=True 사용하지 않음
        result = subprocess.run(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,  # 오류 코드 반환해도 예외 발생하지 않도록 설정
        )
        
        if result.returncode == 0:
            logger.info(f"Git 명령어 실행 성공: {' '.join(command)}")
            return True, result.stdout.strip()
        else:
            error_msg = f"Git 명령어 실행 실패: {result.stderr.strip()}"
            logger.error(error_msg)
            return False, error_msg
    except subprocess.TimeoutExpired:
        error_msg = f"Git 명령어 실행 타임아웃 ({timeout}초): {' '.join(command)}"
        logger.error(error_msg)
        return False, error_msg
    except FileNotFoundError:
        error_msg = "Git 명령어를 찾을 수 없습니다. Git이 설치되어 있는지 확인하세요."
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Git 명령어 실행 중 오류 발생: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def clone_repository(url: str, path: Optional[str] = None, 
                     branch: Optional[str] = None) -> Tuple[bool, str]:
    """
    리포지토리를 클론합니다.
    
    Args:
        url (str): 리포지토리 URL
        path (Optional[str], optional): 클론할 경로 (없으면 기본 경로 사용)
        branch (Optional[str], optional): 클론할 브랜치 (없으면 기본 브랜치 사용)
    
    Returns:
        Tuple[bool, str]: (성공 여부, 결과 또는 오류 메시지)
    """
    # URL에서 리포지토리 이름 추출 (.git 확장자 제거)
    repo_name = url.split('/')[-1].replace('.git', '')
    
    # 클론 기본 경로 설정
    if not path:
        base_path = get_clone_base_path()
        path = os.path.join(base_path, repo_name)
    
    # 경로가 이미 존재하는지 확인
    if os.path.exists(path):
        error_msg = f"경로가 이미 존재합니다: {path}"
        logger.error(error_msg)
        return False, error_msg
    
    # 부모 디렉토리 생성
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    # 클론 명령어 구성
    command = ['git', 'clone', url, path]
    if branch:
        command.extend(['--branch', branch])
    
    return run_git_command(command)


def check_git_repo(path: str) -> bool:
    """
    지정된 경로가 유효한 Git 리포지토리인지 확인합니다.
    
    Args:
        path (str): 확인할 경로
    
    Returns:
        bool: Git 리포지토리 여부
    """
    if not os.path.exists(path):
        logger.warning(f"경로가 존재하지 않습니다: {path}")
        return False
    
    success, result = run_git_command(['git', 'rev-parse', '--is-inside-work-tree'], cwd=path)
    return success and result.strip() == 'true'


def get_branches(path: str) -> Tuple[bool, Union[List[str], str]]:
    """
    리포지토리의 로컬 브랜치 목록을 가져옵니다.
    
    Args:
        path (str): 리포지토리 경로
    
    Returns:
        Tuple[bool, Union[List[str], str]]: 
            (성공 여부, 브랜치 목록 또는 오류 메시지)
    """
    if not check_git_repo(path):
        return False, f"유효한 Git 리포지토리가 아닙니다: {path}"
    
    success, result = run_git_command(['git', 'branch', '--format=%(refname:short)'], cwd=path)
    if not success:
        return False, result
    
    branches = [branch.strip() for branch in result.split('\n') if branch.strip()]
    return True, branches


def get_current_branch(path: str) -> Tuple[bool, str]:
    """
    현재 체크아웃된 브랜치 이름을 가져옵니다.
    
    Args:
        path (str): 리포지토리 경로
    
    Returns:
        Tuple[bool, str]: (성공 여부, 브랜치 이름 또는 오류 메시지)
    """
    if not check_git_repo(path):
        return False, f"유효한 Git 리포지토리가 아닙니다: {path}"
    
    success, result = run_git_command(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=path)
    return success, result.strip() if success else result


def checkout_branch(path: str, branch: str, create: bool = False) -> Tuple[bool, str]:
    """
    브랜치를 체크아웃합니다.
    
    Args:
        path (str): 리포지토리 경로
        branch (str): 체크아웃할 브랜치 이름
        create (bool, optional): 브랜치가 없으면 생성 여부
    
    Returns:
        Tuple[bool, str]: (성공 여부, 결과 또는 오류 메시지)
    """
    if not check_git_repo(path):
        return False, f"유효한 Git 리포지토리가 아닙니다: {path}"
    
    # 명령어 구성
    command = ['git', 'checkout']
    if create:
        command.append('-b')
    command.append(branch)
    
    return run_git_command(command, cwd=path)


def update_repo_remote(path: str, new_url: str) -> Tuple[bool, str]:
    """
    리포지토리의 원격 URL을 업데이트합니다.
    (리포지토리 이름 변경 후 호출됨)
    
    Args:
        path (str): 리포지토리 경로
        new_url (str): 새 원격 URL
    
    Returns:
        Tuple[bool, str]: (성공 여부, 결과 또는 오류 메시지)
    """
    if not check_git_repo(path):
        return False, f"유효한 Git 리포지토리가 아닙니다: {path}"
    
    command = ['git', 'remote', 'set-url', 'origin', new_url]
    return run_git_command(command, cwd=path)


def rename_local_repo_folder(old_path: str, new_name: str) -> Tuple[bool, str]:
    """
    로컬 리포지토리 폴더 이름을 변경합니다.
    
    Args:
        old_path (str): 현재 리포지토리 경로
        new_name (str): 새 폴더 이름
    
    Returns:
        Tuple[bool, str]: (성공 여부, 새 경로 또는 오류 메시지)
    """
    try:
        if not os.path.exists(old_path):
            error_msg = f"경로가 존재하지 않습니다: {old_path}"
            logger.error(error_msg)
            return False, error_msg
        
        # 새 경로 생성
        parent_dir = os.path.dirname(old_path)
        new_path = os.path.join(parent_dir, new_name)
        
        if os.path.exists(new_path):
            error_msg = f"새 경로가 이미 존재합니다: {new_path}"
            logger.error(error_msg)
            return False, error_msg
        
        # 폴더 이름 변경
        shutil.move(old_path, new_path)
        logger.info(f"리포지토리 폴더 이름을 변경했습니다: {old_path} -> {new_path}")
        
        return True, new_path
    except Exception as e:
        error_msg = f"리포지토리 폴더 이름 변경 중 오류 발생: {str(e)}"
        logger.error(error_msg)
        return False, error_msg 