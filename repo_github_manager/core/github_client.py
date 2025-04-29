"""
GitHub API 클라이언트 모듈
GitHub API와 통신하여 리포지토리, 브랜치, PR 등의 정보를 가져오고 관리합니다.
"""
import logging
import base64
from typing import List, Dict, Any, Optional, Tuple, Union

from github import Github, GithubException, Repository, ContentFile, PaginatedList
from github.GithubException import UnknownObjectException, BadCredentialsException

from utils.config_manager import load_github_pat
from utils.logger import setup_logger

# 로거 설정
logger = setup_logger(__name__)


class GitHubClient:
    """GitHub API 클라이언트 클래스"""
    
    def __init__(self):
        """GitHub API 클라이언트 초기화"""
        self.client = None
        self.user = None
        self.token = None
        self.error_message = None
    
    def initialize(self) -> bool:
        """
        GitHub API 클라이언트를 초기화합니다.
        
        Returns:
            bool: 초기화 성공 여부
        """
        self.token = load_github_pat()
        if not self.token:
            self.error_message = "GitHub 개인 액세스 토큰(PAT)이 설정되지 않았습니다."
            logger.error(self.error_message)
            return False
        
        try:
            self.client = Github(self.token)
            self.user = self.client.get_user()
            logger.info(f"GitHub API 클라이언트가 초기화되었습니다. 사용자: {self.user.login}")
            return True
        except BadCredentialsException:
            self.error_message = "GitHub 인증 실패: 토큰이 유효하지 않습니다."
            logger.error(self.error_message)
            return False
        except Exception as e:
            self.error_message = f"GitHub API 클라이언트 초기화 중 오류 발생: {str(e)}"
            logger.error(self.error_message)
            return False
    
    def get_repositories(self) -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
        """
        사용자의 모든 리포지토리 목록을 가져옵니다.
        
        Returns:
            Tuple[bool, Union[List[Dict[str, Any]], str]]: 
                (성공 여부, 리포지토리 목록 또는 오류 메시지)
        """
        if not self.client:
            return False, "GitHub API 클라이언트가 초기화되지 않았습니다."
        
        try:
            repositories = []
            for repo in self.user.get_repos():
                repositories.append({
                    "id": repo.id,
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "description": repo.description,
                    "html_url": repo.html_url,
                    "clone_url": repo.clone_url,
                    "ssh_url": repo.ssh_url,
                    "private": repo.private,
                    "fork": repo.fork,
                    "default_branch": repo.default_branch,
                    "created_at": repo.created_at.isoformat() if repo.created_at else None,
                    "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
                })
            
            logger.info(f"{len(repositories)}개의 리포지토리를 조회했습니다.")
            return True, repositories
        except Exception as e:
            error_msg = f"리포지토리 목록 조회 중 오류 발생: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_repository(self, repo_name: str) -> Tuple[bool, Union[Repository.Repository, str]]:
        """
        리포지토리 객체를 가져옵니다.
        
        Args:
            repo_name (str): 리포지토리 이름 또는 full_name
        
        Returns:
            Tuple[bool, Union[Repository.Repository, str]]: 
                (성공 여부, 리포지토리 객체 또는 오류 메시지)
        """
        if not self.client:
            return False, "GitHub API 클라이언트가 초기화되지 않았습니다."
        
        try:
            # full_name으로 검색 (사용자명/리포명)
            if "/" in repo_name:
                repo = self.client.get_repo(repo_name)
            else:
                # 사용자 본인의 리포지토리일 경우
                repo = self.user.get_repo(repo_name)
            
            logger.info(f"리포지토리를 조회했습니다: {repo.full_name}")
            return True, repo
        except UnknownObjectException:
            error_msg = f"리포지토리를 찾을 수 없습니다: {repo_name}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"리포지토리 조회 중 오류 발생: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_readme(self, repo_name: str) -> Tuple[bool, Union[str, None]]:
        """
        리포지토리의 README 내용을 가져옵니다.
        
        Args:
            repo_name (str): 리포지토리 이름 또는 full_name
        
        Returns:
            Tuple[bool, Union[str, None]]: 
                (성공 여부, README 내용 또는 오류 메시지)
        """
        if not self.client:
            return False, "GitHub API 클라이언트가 초기화되지 않았습니다."
        
        success, repo_or_error = self.get_repository(repo_name)
        if not success:
            return False, repo_or_error
        
        repo = repo_or_error
        try:
            readme = repo.get_readme()
            content = base64.b64decode(readme.content).decode('utf-8')
            logger.info(f"README를 조회했습니다: {repo.full_name}")
            return True, content
        except UnknownObjectException:
            logger.warning(f"README 파일이 없습니다: {repo.full_name}")
            return True, None  # README가 없는 것은 오류가 아님
        except Exception as e:
            error_msg = f"README 조회 중 오류 발생: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def create_repository(self, name: str, description: str = "", private: bool = False,
                          auto_init: bool = True) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """
        새 리포지토리를 생성합니다.
        
        Args:
            name (str): 리포지토리 이름
            description (str, optional): 리포지토리 설명
            private (bool, optional): 비공개 여부
            auto_init (bool, optional): README로 초기화 여부
        
        Returns:
            Tuple[bool, Union[Dict[str, Any], str]]: 
                (성공 여부, 리포지토리 정보 또는 오류 메시지)
        """
        if not self.client:
            return False, "GitHub API 클라이언트가 초기화되지 않았습니다."
        
        try:
            repo = self.user.create_repo(
                name=name,
                description=description,
                private=private,
                auto_init=auto_init
            )
            
            repo_info = {
                "id": repo.id,
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description,
                "html_url": repo.html_url,
                "clone_url": repo.clone_url,
                "ssh_url": repo.ssh_url,
                "private": repo.private,
            }
            
            logger.info(f"리포지토리를 생성했습니다: {repo.full_name}")
            return True, repo_info
        except GithubException as e:
            error_msg = f"리포지토리 생성 중 GitHub API 오류 발생: {e.data.get('message', str(e))}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"리포지토리 생성 중 오류 발생: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def rename_repository(self, repo_name: str, new_name: str) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """
        리포지토리 이름을 변경합니다.
        
        Args:
            repo_name (str): 현재 리포지토리 이름
            new_name (str): 새 리포지토리 이름
        
        Returns:
            Tuple[bool, Union[Dict[str, Any], str]]: 
                (성공 여부, 업데이트된 리포지토리 정보 또는 오류 메시지)
        """
        if not self.client:
            return False, "GitHub API 클라이언트가 초기화되지 않았습니다."
        
        success, repo_or_error = self.get_repository(repo_name)
        if not success:
            return False, repo_or_error
        
        repo = repo_or_error
        try:
            repo.edit(name=new_name)
            
            repo_info = {
                "id": repo.id,
                "name": new_name,
                "full_name": f"{self.user.login}/{new_name}",
                "html_url": repo.html_url.replace(repo_name, new_name),
                "clone_url": repo.clone_url.replace(repo_name, new_name),
                "ssh_url": repo.ssh_url.replace(repo_name, new_name),
            }
            
            logger.info(f"리포지토리 이름을 변경했습니다: {repo_name} -> {new_name}")
            return True, repo_info
        except GithubException as e:
            error_msg = f"리포지토리 이름 변경 중 GitHub API 오류 발생: {e.data.get('message', str(e))}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"리포지토리 이름 변경 중 오류 발생: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def delete_repository(self, repo_name: str) -> Tuple[bool, Optional[str]]:
        """
        리포지토리를 삭제합니다.
        
        Args:
            repo_name (str): 리포지토리 이름
        
        Returns:
            Tuple[bool, Optional[str]]: (성공 여부, 오류 메시지)
        """
        if not self.client:
            return False, "GitHub API 클라이언트가 초기화되지 않았습니다."
        
        success, repo_or_error = self.get_repository(repo_name)
        if not success:
            return False, repo_or_error
        
        repo = repo_or_error
        try:
            repo.delete()
            logger.info(f"리포지토리를 삭제했습니다: {repo_name}")
            return True, None
        except GithubException as e:
            error_msg = f"리포지토리 삭제 중 GitHub API 오류 발생: {e.data.get('message', str(e))}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"리포지토리 삭제 중 오류 발생: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_commits(self, repo_name: str, branch: Optional[str] = None, 
                    per_page: int = 30, page: int = 1) -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
        """
        리포지토리의 커밋 목록을 가져옵니다 (페이지네이션 지원).
        
        Args:
            repo_name (str): 리포지토리 이름
            branch (Optional[str], optional): 브랜치 이름 (None이면 기본 브랜치)
            per_page (int, optional): 페이지당 커밋 수
            page (int, optional): 페이지 번호
        
        Returns:
            Tuple[bool, Union[List[Dict[str, Any]], str]]: 
                (성공 여부, 커밋 목록 또는 오류 메시지)
        """
        if not self.client:
            return False, "GitHub API 클라이언트가 초기화되지 않았습니다."
        
        success, repo_or_error = self.get_repository(repo_name)
        if not success:
            return False, repo_or_error
        
        repo = repo_or_error
        try:
            if branch:
                commits = repo.get_commits(sha=branch)
            else:
                commits = repo.get_commits()
            
            # 페이지네이션 적용
            commits = commits.get_page(page - 1)  # 0-indexed
            
            result = []
            for commit in commits:
                author_name = commit.commit.author.name if commit.commit.author else "Unknown"
                result.append({
                    "sha": commit.sha,
                    "message": commit.commit.message,
                    "author": author_name,
                    "date": commit.commit.author.date.isoformat() if commit.commit.author else None,
                    "html_url": commit.html_url,
                })
            
            logger.info(f"{len(result)}개의 커밋을 조회했습니다: {repo.full_name}")
            return True, result
        except Exception as e:
            error_msg = f"커밋 목록 조회 중 오류 발생: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_pull_requests(self, repo_name: str, state: str = "all", 
                          per_page: int = 30, page: int = 1) -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
        """
        리포지토리의 Pull Request 목록을 가져옵니다 (페이지네이션 지원).
        
        Args:
            repo_name (str): 리포지토리 이름
            state (str, optional): 상태 필터 ("open", "closed", "all")
            per_page (int, optional): 페이지당 PR 수
            page (int, optional): 페이지 번호
        
        Returns:
            Tuple[bool, Union[List[Dict[str, Any]], str]]: 
                (성공 여부, PR 목록 또는 오류 메시지)
        """
        if not self.client:
            return False, "GitHub API 클라이언트가 초기화되지 않았습니다."
        
        success, repo_or_error = self.get_repository(repo_name)
        if not success:
            return False, repo_or_error
        
        repo = repo_or_error
        try:
            pulls = repo.get_pulls(state=state)
            
            # 페이지네이션 적용
            pulls = pulls.get_page(page - 1)  # 0-indexed
            
            result = []
            for pr in pulls:
                result.append({
                    "number": pr.number,
                    "title": pr.title,
                    "state": pr.state,
                    "user": pr.user.login if pr.user else "Unknown",
                    "created_at": pr.created_at.isoformat() if pr.created_at else None,
                    "updated_at": pr.updated_at.isoformat() if pr.updated_at else None,
                    "html_url": pr.html_url,
                    "base": pr.base.ref,
                    "head": pr.head.ref,
                })
            
            logger.info(f"{len(result)}개의 Pull Request를 조회했습니다: {repo.full_name}")
            return True, result
        except Exception as e:
            error_msg = f"Pull Request 목록 조회 중 오류 발생: {str(e)}"
            logger.error(error_msg)
            return False, error_msg


# 싱글톤 인스턴스
github_client = GitHubClient() 