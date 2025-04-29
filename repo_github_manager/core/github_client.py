"""
GitHub API 클라이언트 모듈
PyGithub을 사용하여 GitHub API에 접근하는 기능을 제공합니다.
"""
import os
import logging
from typing import Dict, List, Any, Tuple, Optional, Union

import github
from github import Github, Repository, GithubException

from utils.logger import setup_logger
from utils.config_manager import load_github_pat

# 로거 설정
logger = setup_logger(__name__)


class GitHubClient:
    """GitHub API 클라이언트 클래스"""
    
    def __init__(self):
        """GitHub 클라이언트 초기화"""
        self.github = None
        self.user = None
        self.is_authenticated = False
        self.error_message = None
    
    def initialize(self) -> bool:
        """
        GitHub API 클라이언트 초기화
        
        Returns:
            bool: 인증 성공 여부
        """
        # GitHub PAT 로드
        github_pat = load_github_pat()
        
        if not github_pat:
            self.error_message = "GitHub PAT를 찾을 수 없습니다. .env 파일을 확인하세요."
            logger.error(self.error_message)
            return False
        
        try:
            # PyGithub 인스턴스 생성
            self.github = Github(github_pat)
            
            # 인증 테스트 (현재 로그인한 사용자 정보 가져오기)
            self.user = self.github.get_user()
            _ = self.user.login  # API 호출을 통해 인증 확인
            
            self.is_authenticated = True
            logger.info(f"GitHub API 인증 성공 (사용자: {self.user.login})")
            return True
        
        except GithubException as e:
            self.error_message = f"GitHub API 인증 실패: {e.data.get('message', str(e))}"
            logger.error(self.error_message)
            return False
        
        except Exception as e:
            self.error_message = f"GitHub API 인증 중 오류 발생: {str(e)}"
            logger.error(self.error_message)
            return False
    
    def get_repositories(self) -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
        """
        현재 사용자의 리포지토리 목록을 가져옵니다.
        
        Returns:
            Tuple[bool, Union[List[Dict[str, Any]], str]]: 
                (성공 여부, 리포지토리 목록 또는 오류 메시지)
        """
        if not self.is_authenticated:
            return False, "GitHub API에 인증되지 않았습니다."
        
        try:
            # 리포지토리 목록 가져오기
            repos = self.user.get_repos()
            
            # 필요한 정보만 추출하여 반환
            result = []
            for repo in repos:
                result.append({
                    "id": repo.id,
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "description": repo.description,
                    "html_url": repo.html_url,
                    "clone_url": repo.clone_url,
                    "ssh_url": repo.ssh_url,
                    "private": repo.private,
                    "fork": repo.fork,
                    "created_at": repo.created_at.isoformat() if repo.created_at else None,
                    "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
                    "owner": {
                        "login": repo.owner.login,
                        "id": repo.owner.id,
                        "avatar_url": repo.owner.avatar_url,
                    } if repo.owner else None,
                })
            
            logger.info(f"{len(result)}개의 리포지토리를 가져왔습니다.")
            return True, result
        
        except GithubException as e:
            error_msg = f"리포지토리 목록 가져오기 실패: {e.data.get('message', str(e))}"
            logger.error(error_msg)
            return False, error_msg
        
        except Exception as e:
            error_msg = f"리포지토리 목록 가져오는 중 오류 발생: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_repository(self, repo_name: str) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """
        지정된 이름의 리포지토리 정보를 가져옵니다.
        
        Args:
            repo_name (str): 리포지토리 이름 (사용자명/리포지토리명 형식)
        
        Returns:
            Tuple[bool, Union[Dict[str, Any], str]]: 
                (성공 여부, 리포지토리 정보 또는 오류 메시지)
        """
        if not self.is_authenticated:
            return False, "GitHub API에 인증되지 않았습니다."
        
        try:
            # 리포지토리 정보 가져오기
            repo = self.github.get_repo(repo_name)
            
            # 필요한 정보 추출
            result = {
                "id": repo.id,
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description,
                "html_url": repo.html_url,
                "clone_url": repo.clone_url,
                "ssh_url": repo.ssh_url,
                "private": repo.private,
                "fork": repo.fork,
                "created_at": repo.created_at.isoformat() if repo.created_at else None,
                "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
                "owner": {
                    "login": repo.owner.login,
                    "id": repo.owner.id,
                    "avatar_url": repo.owner.avatar_url,
                } if repo.owner else None,
                "default_branch": repo.default_branch,
                "language": repo.language,
                "forks_count": repo.forks_count,
                "stargazers_count": repo.stargazers_count,
                "watchers_count": repo.watchers_count,
                "open_issues_count": repo.open_issues_count,
            }
            
            logger.info(f"리포지토리 '{repo_name}' 정보를 가져왔습니다.")
            return True, result
        
        except GithubException as e:
            error_msg = f"리포지토리 정보 가져오기 실패: {e.data.get('message', str(e))}"
            logger.error(error_msg)
            return False, error_msg
        
        except Exception as e:
            error_msg = f"리포지토리 정보 가져오는 중 오류 발생: {str(e)}"
            logger.error(error_msg)
            return False, error_msg


# 싱글톤 인스턴스
github_client = GitHubClient() 