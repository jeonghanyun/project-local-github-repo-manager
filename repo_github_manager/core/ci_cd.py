"""
로컬 CI/CD 기능 관리 모듈
로컬 CI/CD 설정 파일을 파싱하고 명령어를 안전하게 실행합니다.
"""
import os
import yaml
import time
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union

from utils.logger import setup_logger

# 로거 설정
logger = setup_logger(__name__)

# CI/CD 설정 파일 기본 이름
CI_CONFIG_FILE = '.local_ci.yaml'


def load_ci_config(repo_path: str) -> Tuple[bool, Union[Dict[str, Any], str]]:
    """
    리포지토리의 CI/CD 설정 파일을 로드합니다.
    
    Args:
        repo_path (str): 리포지토리 경로
    
    Returns:
        Tuple[bool, Union[Dict[str, Any], str]]: 
            (성공 여부, CI/CD 설정 또는 오류 메시지)
    """
    config_path = os.path.join(repo_path, CI_CONFIG_FILE)
    
    if not os.path.exists(config_path):
        error_msg = f"CI/CD 설정 파일을 찾을 수 없습니다: {config_path}"
        logger.warning(error_msg)
        return False, error_msg
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        logger.info(f"CI/CD 설정 파일을 로드했습니다: {config_path}")
        return True, config
    except yaml.YAMLError as e:
        error_msg = f"CI/CD 설정 파일 파싱 중 오류 발생: {str(e)}"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"CI/CD 설정 파일 로드 중 오류 발생: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def get_command_list(config: Dict[str, Any]) -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
    """
    CI/CD 설정에서 실행할 명령어 목록을 추출합니다.
    
    Args:
        config (Dict[str, Any]): CI/CD 설정
    
    Returns:
        Tuple[bool, Union[List[Dict[str, Any]], str]]: 
            (성공 여부, 명령어 목록 또는 오류 메시지)
    """
    try:
        if not config:
            return False, "CI/CD 설정이 비어 있습니다."
        
        steps = config.get('steps', [])
        if not steps:
            return False, "CI/CD 설정에 실행 단계가 정의되지 않았습니다."
        
        commands = []
        for idx, step in enumerate(steps):
            if 'name' not in step:
                return False, f"단계 {idx+1}에 이름이 없습니다."
            
            if 'run' not in step:
                return False, f"단계 '{step['name']}'에 실행 명령어가 없습니다."
            
            commands.append({
                'name': step['name'],
                'command': step['run'],
                'working_dir': step.get('working_dir', ''),
                'allow_failure': step.get('allow_failure', False),
                'timeout': step.get('timeout', 300),  # 기본 5분 타임아웃
            })
        
        logger.info(f"{len(commands)}개의 CI/CD 명령어를 추출했습니다.")
        return True, commands
    except Exception as e:
        error_msg = f"CI/CD 명령어 목록 추출 중 오류 발생: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def execute_command(command_info: Dict[str, Any], repo_path: str) -> Tuple[bool, Dict[str, Any]]:
    """
    단일 CI/CD 명령어를 안전하게 실행합니다.
    
    Args:
        command_info (Dict[str, Any]): 명령어 정보
        repo_path (str): 리포지토리 경로
    
    Returns:
        Tuple[bool, Dict[str, Any]]: 
            (성공 여부, 결과 정보)
    """
    name = command_info['name']
    command = command_info['command']
    working_dir = command_info.get('working_dir', '')
    allow_failure = command_info.get('allow_failure', False)
    timeout = command_info.get('timeout', 300)
    
    # 작업 디렉토리 설정
    if working_dir:
        cwd = os.path.join(repo_path, working_dir)
    else:
        cwd = repo_path
    
    # 작업 디렉토리 존재 확인
    if not os.path.exists(cwd):
        error_msg = f"작업 디렉토리가 존재하지 않습니다: {cwd}"
        logger.error(error_msg)
        return False, {
            'name': name,
            'success': False,
            'error': error_msg,
            'stdout': '',
            'stderr': error_msg,
            'duration': 0,
        }
    
    logger.info(f"CI/CD 명령어 실행 시작: {name}")
    start_time = time.time()
    
    try:
        # 명령어 실행 (shell=True는 보안상 권장되지 않으나, 복잡한 셸 명령어를 실행하기 위해 필요)
        # 실제 애플리케이션에서는 사용자에게 명령어를 보여주고 확인을 받은 후 실행해야 함
        process = subprocess.Popen(
            command,
            cwd=cwd,
            shell=True,  # 주의: 신뢰할 수 있는 명령어만 실행
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            universal_newlines=True,
            bufsize=1,
        )
        
        stdout, stderr = process.communicate(timeout=timeout)
        duration = time.time() - start_time
        
        success = process.returncode == 0 or allow_failure
        result = {
            'name': name,
            'success': success,
            'return_code': process.returncode,
            'stdout': stdout,
            'stderr': stderr,
            'duration': duration,
            'allow_failure': allow_failure,
        }
        
        log_level = logger.info if success else logger.error
        log_level(f"CI/CD 명령어 '{name}' 실행 완료: {'성공' if success else '실패'} ({duration:.2f}초)")
        
        return success, result
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        error_msg = f"명령어 실행 타임아웃 ({timeout}초)"
        logger.error(f"CI/CD 명령어 '{name}' {error_msg}")
        
        # 프로세스 강제 종료
        try:
            process.kill()
            _, _ = process.communicate()
        except:
            pass
        
        return allow_failure, {
            'name': name,
            'success': allow_failure,
            'error': error_msg,
            'stdout': '',
            'stderr': error_msg,
            'duration': duration,
            'allow_failure': allow_failure,
        }
    except Exception as e:
        duration = time.time() - start_time
        error_msg = f"명령어 실행 중 오류 발생: {str(e)}"
        logger.error(f"CI/CD 명령어 '{name}' {error_msg}")
        
        return allow_failure, {
            'name': name,
            'success': allow_failure,
            'error': error_msg,
            'stdout': '',
            'stderr': str(e),
            'duration': duration,
            'allow_failure': allow_failure,
        }


def run_ci_cd_pipeline(repo_path: str) -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
    """
    리포지토리의 CI/CD 파이프라인을 실행합니다.
    
    Args:
        repo_path (str): 리포지토리 경로
    
    Returns:
        Tuple[bool, Union[List[Dict[str, Any]], str]]: 
            (성공 여부, 결과 목록 또는 오류 메시지)
    """
    # CI/CD 설정 로드
    success, config = load_ci_config(repo_path)
    if not success:
        return False, config
    
    # 명령어 목록 추출
    success, commands = get_command_list(config)
    if not success:
        return False, commands
    
    # 각 명령어 실행
    results = []
    pipeline_success = True
    
    for command_info in commands:
        success, result = execute_command(command_info, repo_path)
        results.append(result)
        
        # 명령어가 실패하고 allow_failure가 False이면 파이프라인 중단
        if not success and not command_info.get('allow_failure', False):
            pipeline_success = False
            break
    
    logger.info(f"CI/CD 파이프라인 실행 완료: {'성공' if pipeline_success else '실패'}")
    return pipeline_success, results 