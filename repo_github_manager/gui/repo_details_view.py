"""
리포지토리 상세 뷰 모듈
우측 패널에 표시되는, 선택된 리포지토리의 상세 정보를 관리합니다.
"""
import os
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import webbrowser
from typing import Dict, Any, List, Optional, Tuple, Callable

from utils.logger import setup_logger
from utils.config_manager import get_clone_base_path
from core.github_client import github_client
from core.git_utils import clone_repository, update_repo_remote, rename_local_repo_folder
from core.git_utils import get_branches, get_current_branch, checkout_branch
from core.ci_cd import run_ci_cd_pipeline
from gui.async_handler import async_handler
from gui.dialogs import (
    show_input_dialog, show_confirm_dialog, show_progress_dialog, show_directory_dialog
)

# 로거 설정
logger = setup_logger(__name__)


class RepoDetailsView(ttk.Frame):
    """리포지토리 상세 정보를 표시하는 뷰"""
    
    def __init__(self, parent, app, **kwargs):
        """
        리포지토리 상세 뷰 초기화
        
        Args:
            parent: 부모 위젯
            app: 메인 애플리케이션 인스턴스
            **kwargs: ttk.Frame에 전달할 추가 인자
        """
        super().__init__(parent, **kwargs)
        
        self.app = app
        self.current_repo = None
        self.local_repo_path = None
        
        # 상세 정보 탭 영역 생성
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 탭 생성
        self.info_tab = ttk.Frame(self.notebook)
        self.branches_tab = ttk.Frame(self.notebook)
        self.commits_tab = ttk.Frame(self.notebook)
        self.pr_tab = ttk.Frame(self.notebook)
        self.cicd_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.info_tab, text="정보")
        self.notebook.add(self.branches_tab, text="브랜치")
        self.notebook.add(self.commits_tab, text="커밋")
        self.notebook.add(self.pr_tab, text="풀 리퀘스트")
        self.notebook.add(self.cicd_tab, text="CI/CD")
        
        # 탭 내용 초기화
        self._init_info_tab()
        self._init_branches_tab()
        self._init_commits_tab()
        self._init_pr_tab()
        self._init_cicd_tab()
        
        # 탭 변경 이벤트 바인딩
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        
        # 초기 상태 설정
        self.clear()
    
    def _init_info_tab(self):
        """정보 탭 초기화"""
        # 정보 표시 영역
        self.info_frame = ttk.Frame(self.info_tab)
        self.info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 기본 정보 영역
        info_inner_frame = ttk.LabelFrame(self.info_frame, text="리포지토리 정보")
        info_inner_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 정보 그리드
        self.repo_info_grid = ttk.Frame(info_inner_frame)
        self.repo_info_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # 이름
        ttk.Label(self.repo_info_grid, text="이름:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.name_label = ttk.Label(self.repo_info_grid, text="")
        self.name_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        # 설명
        ttk.Label(self.repo_info_grid, text="설명:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.description_label = ttk.Label(self.repo_info_grid, text="")
        self.description_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        # 비공개 여부
        ttk.Label(self.repo_info_grid, text="비공개:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.private_label = ttk.Label(self.repo_info_grid, text="")
        self.private_label.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        # URL
        ttk.Label(self.repo_info_grid, text="URL:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.url_frame = ttk.Frame(self.repo_info_grid)
        self.url_frame.grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
        self.url_label = ttk.Label(self.url_frame, text="")
        self.url_label.pack(side=tk.LEFT)
        self.open_url_button = ttk.Button(self.url_frame, text="열기", command=self._on_open_url_clicked)
        self.open_url_button.pack(side=tk.LEFT, padx=5)
        
        # 로컬 경로
        ttk.Label(self.repo_info_grid, text="로컬 경로:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
        self.local_path_frame = ttk.Frame(self.repo_info_grid)
        self.local_path_frame.grid(row=4, column=1, sticky=tk.W, padx=5, pady=2)
        self.local_path_label = ttk.Label(self.local_path_frame, text="")
        self.local_path_label.pack(side=tk.LEFT)
        self.open_local_button = ttk.Button(
            self.local_path_frame, text="열기", command=self._on_open_local_clicked
        )
        self.open_local_button.pack(side=tk.LEFT, padx=5)
        
        # 컬럼 설정
        self.repo_info_grid.columnconfigure(1, weight=1)
        
        # 버튼 영역
        button_frame = ttk.Frame(self.info_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=10)
        
        self.clone_button = ttk.Button(
            button_frame, text="클론", command=lambda: self.clone_repository(self.current_repo)
        )
        self.clone_button.pack(side=tk.LEFT, padx=5)
        
        self.rename_button = ttk.Button(
            button_frame, text="이름 변경", command=lambda: self.rename_repository(self.current_repo)
        )
        self.rename_button.pack(side=tk.LEFT, padx=5)
        
        self.delete_button = ttk.Button(
            button_frame, text="삭제", command=lambda: self.delete_repository(self.current_repo)
        )
        self.delete_button.pack(side=tk.LEFT, padx=5)
        
        # README 영역
        readme_frame = ttk.LabelFrame(self.info_frame, text="README")
        readme_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.readme_text = scrolledtext.ScrolledText(readme_frame, wrap=tk.WORD)
        self.readme_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.readme_text.config(state=tk.DISABLED)  # 읽기 전용
    
    def _init_branches_tab(self):
        """브랜치 탭 초기화"""
        # 브랜치 관리 프레임
        branch_frame = ttk.Frame(self.branches_tab)
        branch_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 현재 브랜치 선택 영역
        current_branch_frame = ttk.LabelFrame(branch_frame, text="현재 브랜치")
        current_branch_frame.pack(fill=tk.X, padx=5, pady=5)
        
        branch_control_frame = ttk.Frame(current_branch_frame)
        branch_control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(branch_control_frame, text="브랜치:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.branch_combobox = ttk.Combobox(branch_control_frame, width=30)
        self.branch_combobox.pack(side=tk.LEFT, padx=5)
        
        self.checkout_button = ttk.Button(
            branch_control_frame, text="체크아웃", command=self._on_checkout_clicked
        )
        self.checkout_button.pack(side=tk.LEFT, padx=5)
        
        self.refresh_branches_button = ttk.Button(
            branch_control_frame, text="새로고침", command=self._on_refresh_branches_clicked
        )
        self.refresh_branches_button.pack(side=tk.LEFT, padx=5)
        
        # 새 브랜치 영역
        new_branch_frame = ttk.LabelFrame(branch_frame, text="새 브랜치 생성")
        new_branch_frame.pack(fill=tk.X, padx=5, pady=5)
        
        new_branch_control_frame = ttk.Frame(new_branch_frame)
        new_branch_control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(new_branch_control_frame, text="이름:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.new_branch_entry = ttk.Entry(new_branch_control_frame, width=30)
        self.new_branch_entry.pack(side=tk.LEFT, padx=5)
        
        self.create_branch_button = ttk.Button(
            new_branch_control_frame, text="생성", command=self._on_create_branch_clicked
        )
        self.create_branch_button.pack(side=tk.LEFT, padx=5)
    
    def _init_commits_tab(self):
        """커밋 탭 초기화"""
        # 커밋 목록 프레임
        commits_frame = ttk.Frame(self.commits_tab)
        commits_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 컨트롤 영역
        control_frame = ttk.Frame(commits_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(control_frame, text="브랜치:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.commit_branch_combobox = ttk.Combobox(control_frame, width=30)
        self.commit_branch_combobox.pack(side=tk.LEFT, padx=5)
        
        self.refresh_commits_button = ttk.Button(
            control_frame, text="커밋 불러오기", command=self._on_refresh_commits_clicked
        )
        self.refresh_commits_button.pack(side=tk.LEFT, padx=5)
        
        # 커밋 트리뷰
        commit_list_frame = ttk.Frame(commits_frame)
        commit_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 컬럼 설정
        columns = ("sha", "message", "author", "date")
        self.commits_tree = ttk.Treeview(
            commit_list_frame, columns=columns, show="headings", selectmode="browse"
        )
        
        self.commits_tree.heading("sha", text="SHA")
        self.commits_tree.heading("message", text="메시지")
        self.commits_tree.heading("author", text="작성자")
        self.commits_tree.heading("date", text="날짜")
        
        self.commits_tree.column("sha", width=80, anchor=tk.W)
        self.commits_tree.column("message", width=300, anchor=tk.W)
        self.commits_tree.column("author", width=150, anchor=tk.W)
        self.commits_tree.column("date", width=150, anchor=tk.W)
        
        # 스크롤바
        scrollbar = ttk.Scrollbar(commit_list_frame, orient=tk.VERTICAL, command=self.commits_tree.yview)
        self.commits_tree.configure(yscrollcommand=scrollbar.set)
        
        # 위젯 배치
        self.commits_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 이벤트 바인딩
        self.commits_tree.bind("<Double-1>", self._on_commit_double_clicked)
    
    def _init_pr_tab(self):
        """풀 리퀘스트 탭 초기화"""
        # PR 목록 프레임
        pr_frame = ttk.Frame(self.pr_tab)
        pr_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 컨트롤 영역
        control_frame = ttk.Frame(pr_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(control_frame, text="상태:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.pr_state_combobox = ttk.Combobox(
            control_frame, width=15, values=["all", "open", "closed"]
        )
        self.pr_state_combobox.set("all")
        self.pr_state_combobox.pack(side=tk.LEFT, padx=5)
        
        self.refresh_pr_button = ttk.Button(
            control_frame, text="PR 불러오기", command=self._on_refresh_pr_clicked
        )
        self.refresh_pr_button.pack(side=tk.LEFT, padx=5)
        
        # PR 트리뷰
        pr_list_frame = ttk.Frame(pr_frame)
        pr_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 컬럼 설정
        columns = ("number", "title", "state", "user", "updated_at")
        self.pr_tree = ttk.Treeview(
            pr_list_frame, columns=columns, show="headings", selectmode="browse"
        )
        
        self.pr_tree.heading("number", text="#")
        self.pr_tree.heading("title", text="제목")
        self.pr_tree.heading("state", text="상태")
        self.pr_tree.heading("user", text="작성자")
        self.pr_tree.heading("updated_at", text="업데이트")
        
        self.pr_tree.column("number", width=50, anchor=tk.W)
        self.pr_tree.column("title", width=300, anchor=tk.W)
        self.pr_tree.column("state", width=80, anchor=tk.W)
        self.pr_tree.column("user", width=150, anchor=tk.W)
        self.pr_tree.column("updated_at", width=150, anchor=tk.W)
        
        # 스크롤바
        scrollbar = ttk.Scrollbar(pr_list_frame, orient=tk.VERTICAL, command=self.pr_tree.yview)
        self.pr_tree.configure(yscrollcommand=scrollbar.set)
        
        # 위젯 배치
        self.pr_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 이벤트 바인딩
        self.pr_tree.bind("<Double-1>", self._on_pr_double_clicked)
    
    def _init_cicd_tab(self):
        """CI/CD 탭 초기화"""
        # CI/CD 프레임
        cicd_frame = ttk.Frame(self.cicd_tab)
        cicd_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 컨트롤 영역
        control_frame = ttk.Frame(cicd_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.run_cicd_button = ttk.Button(
            control_frame, text="CI/CD 파이프라인 실행", command=self._on_run_cicd_clicked
        )
        self.run_cicd_button.pack(side=tk.LEFT, padx=5)
        
        # 로그 영역
        log_frame = ttk.LabelFrame(cicd_frame, text="로그")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.cicd_log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD)
        self.cicd_log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.cicd_log_text.config(state=tk.DISABLED)  # 읽기 전용
    
    def clear(self):
        """상세 뷰 초기화 (리포지토리 선택 해제 시)"""
        self.current_repo = None
        self.local_repo_path = None
        
        # 정보 탭 초기화
        self.name_label.config(text="")
        self.description_label.config(text="")
        self.private_label.config(text="")
        self.url_label.config(text="")
        self.local_path_label.config(text="")
        
        self.readme_text.config(state=tk.NORMAL)
        self.readme_text.delete(1.0, tk.END)
        self.readme_text.config(state=tk.DISABLED)
        
        # 브랜치 탭 초기화
        self.branch_combobox.set("")
        self.branch_combobox["values"] = []
        self.new_branch_entry.delete(0, tk.END)
        
        # 커밋 탭 초기화
        self.commit_branch_combobox.set("")
        self.commit_branch_combobox["values"] = []
        for item in self.commits_tree.get_children():
            self.commits_tree.delete(item)
        
        # PR 탭 초기화
        for item in self.pr_tree.get_children():
            self.pr_tree.delete(item)
        
        # CI/CD 탭 초기화
        self.cicd_log_text.config(state=tk.NORMAL)
        self.cicd_log_text.delete(1.0, tk.END)
        self.cicd_log_text.config(state=tk.DISABLED)
        
        # 버튼 비활성화
        self.clone_button.config(state=tk.DISABLED)
        self.rename_button.config(state=tk.DISABLED)
        self.delete_button.config(state=tk.DISABLED)
        self.open_url_button.config(state=tk.DISABLED)
        self.open_local_button.config(state=tk.DISABLED)
        self.checkout_button.config(state=tk.DISABLED)
        self.refresh_branches_button.config(state=tk.DISABLED)
        self.create_branch_button.config(state=tk.DISABLED)
        self.refresh_commits_button.config(state=tk.DISABLED)
        self.refresh_pr_button.config(state=tk.DISABLED)
        self.run_cicd_button.config(state=tk.DISABLED)
    
    def show_repository(self, repo_data: Dict[str, Any]):
        """
        선택된 리포지토리 정보 표시
        
        Args:
            repo_data (Dict[str, Any]): 리포지토리 정보
        """
        self.current_repo = repo_data
        self.notebook.select(0)  # 정보 탭으로 이동
        
        # 기본 정보 표시
        self.name_label.config(text=repo_data.get("name", ""))
        self.description_label.config(text=repo_data.get("description", ""))
        self.private_label.config(text="예" if repo_data.get("private", False) else "아니오")
        self.url_label.config(text=repo_data.get("html_url", ""))
        
        # 로컬 경로 확인
        base_path = get_clone_base_path()
        repo_name = repo_data.get("name", "")
        potential_path = os.path.join(base_path, repo_name)
        
        if os.path.exists(potential_path) and os.path.isdir(potential_path):
            self.local_repo_path = potential_path
            self.local_path_label.config(text=potential_path)
            self.open_local_button.config(state=tk.NORMAL)
            
            # 로컬 리포지토리 있을 때만 활성화
            self.checkout_button.config(state=tk.NORMAL)
            self.refresh_branches_button.config(state=tk.NORMAL)
            self.create_branch_button.config(state=tk.NORMAL)
            self.refresh_commits_button.config(state=tk.NORMAL)
            self.run_cicd_button.config(state=tk.NORMAL)
            
            # 브랜치 정보 로드
            self._load_local_branches()
        else:
            self.local_repo_path = None
            self.local_path_label.config(text="로컬에 없음")
            self.open_local_button.config(state=tk.DISABLED)
        
        # 버튼 활성화
        self.clone_button.config(state=tk.NORMAL)
        self.rename_button.config(state=tk.NORMAL)
        self.delete_button.config(state=tk.NORMAL)
        self.open_url_button.config(state=tk.NORMAL)
        self.refresh_pr_button.config(state=tk.NORMAL)
        
        # README 로드
        self._load_readme()
    
    def _load_readme(self):
        """README 내용 로드 (비동기)"""
        self.readme_text.config(state=tk.NORMAL)
        self.readme_text.delete(1.0, tk.END)
        self.readme_text.insert(tk.END, "README 로드 중...")
        self.readme_text.config(state=tk.DISABLED)
        
        def load_task():
            if not self.current_repo:
                return False, "리포지토리가 선택되지 않았습니다."
            return github_client.get_readme(self.current_repo["full_name"])
        
        def on_success(result):
            success, data = result
            self.readme_text.config(state=tk.NORMAL)
            self.readme_text.delete(1.0, tk.END)
            
            if success and data:
                self.readme_text.insert(tk.END, data)
            elif success and data is None:
                self.readme_text.insert(tk.END, "README 파일이 없습니다.")
            else:
                self.readme_text.insert(tk.END, f"README 로드 실패: {data}")
            
            self.readme_text.config(state=tk.DISABLED)
        
        def on_error(error):
            self.readme_text.config(state=tk.NORMAL)
            self.readme_text.delete(1.0, tk.END)
            self.readme_text.insert(tk.END, f"README 로드 중 오류 발생: {str(error)}")
            self.readme_text.config(state=tk.DISABLED)
        
        async_handler.submit_task(load_task, on_success, on_error)
    
    def _load_local_branches(self):
        """로컬 브랜치 정보 로드 (비동기)"""
        if not self.local_repo_path:
            return
        
        def load_task():
            # 브랜치 목록 가져오기
            success, branches = get_branches(self.local_repo_path)
            if not success:
                return False, branches
            
            # 현재 브랜치 가져오기
            success, current_branch = get_current_branch(self.local_repo_path)
            if not success:
                current_branch = None
            
            return True, (branches, current_branch)
        
        def on_success(result):
            success, data = result
            if success:
                branches, current_branch = data
                
                # 브랜치 콤보박스 업데이트
                self.branch_combobox["values"] = branches
                self.commit_branch_combobox["values"] = branches
                
                if current_branch:
                    self.branch_combobox.set(current_branch)
                    self.commit_branch_combobox.set(current_branch)
        
        def on_error(error):
            messagebox.showerror("오류", f"브랜치 정보 로드 중 오류 발생: {str(error)}")
        
        async_handler.submit_task(load_task, on_success, on_error)
    
    def _on_tab_changed(self, event):
        """탭 변경 이벤트 핸들러"""
        selected_tab = self.notebook.index("current")
        
        # 커밋 탭으로 이동 시 자동 새로고침
        if selected_tab == 2 and self.local_repo_path and not self.commits_tree.get_children():
            self._on_refresh_commits_clicked()
        
        # PR 탭으로 이동 시 자동 새로고침
        if selected_tab == 3 and self.current_repo and not self.pr_tree.get_children():
            self._on_refresh_pr_clicked()
    
    def _on_open_url_clicked(self):
        """URL 열기 버튼 클릭 이벤트 핸들러"""
        if self.current_repo and "html_url" in self.current_repo:
            webbrowser.open(self.current_repo["html_url"])
    
    def _on_open_local_clicked(self):
        """로컬 경로 열기 버튼 클릭 이벤트 핸들러"""
        if self.local_repo_path and os.path.exists(self.local_repo_path):
            # 시스템에 맞는 파일 탐색기 열기
            if os.name == 'nt':  # Windows
                os.startfile(self.local_repo_path)
            elif os.name == 'posix':  # macOS, Linux
                import subprocess
                if sys.platform == 'darwin':  # macOS
                    subprocess.run(['open', self.local_repo_path])
                else:  # Linux
                    subprocess.run(['xdg-open', self.local_repo_path])
    
    def _on_checkout_clicked(self):
        """브랜치 체크아웃 버튼 클릭 이벤트 핸들러"""
        if not self.local_repo_path:
            messagebox.showerror("오류", "로컬 리포지토리가 없습니다.")
            return
        
        branch = self.branch_combobox.get()
        if not branch:
            messagebox.showerror("오류", "브랜치를 선택하세요.")
            return
        
        def task_func(dialog):
            dialog.update_message(f"브랜치 '{branch}'로 체크아웃 중...")
            success, result = checkout_branch(self.local_repo_path, branch)
            return success, result
        
        def success_callback(result):
            success, message = result
            if success:
                messagebox.showinfo("성공", f"브랜치 '{branch}'로 체크아웃되었습니다.")
                self._load_local_branches()  # 브랜치 정보 새로고침
            else:
                messagebox.showerror("오류", f"브랜치 체크아웃 실패: {message}")
        
        def error_callback(error):
            messagebox.showerror("오류", f"브랜치 체크아웃 중 오류 발생: {error}")
        
        show_progress_dialog(
            self, "브랜치 체크아웃", f"브랜치 '{branch}'로 체크아웃 중...",
            task_func, success_callback, error_callback
        )
    
    def _on_refresh_branches_clicked(self):
        """브랜치 새로고침 버튼 클릭 이벤트 핸들러"""
        self._load_local_branches()
    
    def _on_create_branch_clicked(self):
        """새 브랜치 생성 버튼 클릭 이벤트 핸들러"""
        if not self.local_repo_path:
            messagebox.showerror("오류", "로컬 리포지토리가 없습니다.")
            return
        
        branch_name = self.new_branch_entry.get().strip()
        if not branch_name:
            messagebox.showerror("오류", "브랜치 이름을 입력하세요.")
            return
        
        def task_func(dialog):
            dialog.update_message(f"브랜치 '{branch_name}' 생성 중...")
            success, result = checkout_branch(self.local_repo_path, branch_name, create=True)
            return success, result
        
        def success_callback(result):
            success, message = result
            if success:
                self.new_branch_entry.delete(0, tk.END)
                messagebox.showinfo("성공", f"브랜치 '{branch_name}'이(가) 생성되었습니다.")
                self._load_local_branches()  # 브랜치 정보 새로고침
            else:
                messagebox.showerror("오류", f"브랜치 생성 실패: {message}")
        
        def error_callback(error):
            messagebox.showerror("오류", f"브랜치 생성 중 오류 발생: {error}")
        
        show_progress_dialog(
            self, "브랜치 생성", f"브랜치 '{branch_name}' 생성 중...",
            task_func, success_callback, error_callback
        )
    
    def _on_refresh_commits_clicked(self):
        """커밋 새로고침 버튼 클릭 이벤트 핸들러"""
        if not self.local_repo_path:
            messagebox.showerror("오류", "로컬 리포지토리가 없습니다.")
            return
        
        branch = self.commit_branch_combobox.get()
        if not branch:
            messagebox.showerror("오류", "브랜치를 선택하세요.")
            return
        
        # 트리뷰 초기화
        for item in self.commits_tree.get_children():
            self.commits_tree.delete(item)
        
        def task_func(dialog):
            dialog.update_message(f"브랜치 '{branch}'의 커밋 로드 중...")
            try:
                # GitHub API를 통해 커밋 가져오기
                commits = github_client.get_commits(
                    self.current_repo["full_name"], branch=branch, max_count=30
                )
                return True, commits
            except Exception as e:
                return False, str(e)
        
        def success_callback(result):
            success, data = result
            if success:
                commits = data
                for commit in commits:
                    self.commits_tree.insert(
                        "", "end",
                        values=(
                            commit.get("sha", "")[:7],
                            commit.get("commit", {}).get("message", "").split("\n")[0],
                            commit.get("commit", {}).get("author", {}).get("name", ""),
                            commit.get("commit", {}).get("author", {}).get("date", "")[:10]
                        )
                    )
            else:
                messagebox.showerror("오류", f"커밋 로드 실패: {data}")
        
        def error_callback(error):
            messagebox.showerror("오류", f"커밋 로드 중 오류 발생: {error}")
        
        show_progress_dialog(
            self, "커밋 로드", f"브랜치 '{branch}'의 커밋 로드 중...",
            task_func, success_callback, error_callback
        )
    
    def _on_commit_double_clicked(self, event):
        """커밋 항목 더블 클릭 이벤트 핸들러"""
        selection = self.commits_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        commit_sha = self.commits_tree.item(item, "values")[0]
        
        if self.current_repo:
            # 커밋 URL 생성
            commit_url = f"{self.current_repo['html_url']}/commit/{commit_sha}"
            webbrowser.open(commit_url)
    
    def _on_refresh_pr_clicked(self):
        """PR 새로고침 버튼 클릭 이벤트 핸들러"""
        if not self.current_repo:
            messagebox.showerror("오류", "리포지토리가 선택되지 않았습니다.")
            return
        
        state = self.pr_state_combobox.get()
        
        # 트리뷰 초기화
        for item in self.pr_tree.get_children():
            self.pr_tree.delete(item)
        
        def task_func(dialog):
            dialog.update_message(f"풀 리퀘스트 로드 중...")
            try:
                prs = github_client.get_pull_requests(
                    self.current_repo["full_name"], state=state
                )
                return True, prs
            except Exception as e:
                return False, str(e)
        
        def success_callback(result):
            success, data = result
            if success:
                prs = data
                for pr in prs:
                    self.pr_tree.insert(
                        "", "end",
                        values=(
                            pr.get("number", ""),
                            pr.get("title", ""),
                            pr.get("state", ""),
                            pr.get("user", {}).get("login", ""),
                            pr.get("updated_at", "")[:10]
                        )
                    )
            else:
                messagebox.showerror("오류", f"PR 로드 실패: {data}")
        
        def error_callback(error):
            messagebox.showerror("오류", f"PR 로드 중 오류 발생: {error}")
        
        show_progress_dialog(
            self, "PR 로드", "풀 리퀘스트 로드 중...",
            task_func, success_callback, error_callback
        )
    
    def _on_pr_double_clicked(self, event):
        """PR 항목 더블 클릭 이벤트 핸들러"""
        selection = self.pr_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        pr_number = self.pr_tree.item(item, "values")[0]
        
        if self.current_repo:
            # PR URL 생성
            pr_url = f"{self.current_repo['html_url']}/pull/{pr_number}"
            webbrowser.open(pr_url)
    
    def _on_run_cicd_clicked(self):
        """CI/CD 파이프라인 실행 버튼 클릭 이벤트 핸들러"""
        if not self.local_repo_path:
            messagebox.showerror("오류", "로컬 리포지토리가 없습니다.")
            return
        
        # 로그 창 초기화
        self.cicd_log_text.config(state=tk.NORMAL)
        self.cicd_log_text.delete(1.0, tk.END)
        self.cicd_log_text.insert(tk.END, "CI/CD 파이프라인 실행 중...\n\n")
        self.cicd_log_text.config(state=tk.DISABLED)
        
        def task_func(dialog):
            dialog.update_message("CI/CD 파이프라인 실행 중...")
            
            def log_callback(message):
                # UI 스레드에서 로그 업데이트
                self.after(0, lambda: self._append_to_cicd_log(message))
            
            success, result = run_ci_cd_pipeline(
                self.local_repo_path, log_callback=log_callback
            )
            return success, result
        
        def success_callback(result):
            success, message = result
            self._append_to_cicd_log("\n" + "-" * 40 + "\n")
            
            if success:
                self._append_to_cicd_log("✅ CI/CD 파이프라인 실행 성공\n")
            else:
                self._append_to_cicd_log(f"❌ CI/CD 파이프라인 실행 실패: {message}\n")
        
        def error_callback(error):
            self._append_to_cicd_log(f"\n❌ CI/CD 파이프라인 실행 중 오류 발생: {error}\n")
        
        show_progress_dialog(
            self, "CI/CD 실행", "CI/CD 파이프라인 실행 중...",
            task_func, success_callback, error_callback
        )
    
    def _append_to_cicd_log(self, message):
        """CI/CD 로그 텍스트에 메시지 추가"""
        self.cicd_log_text.config(state=tk.NORMAL)
        self.cicd_log_text.insert(tk.END, message)
        self.cicd_log_text.see(tk.END)  # 스크롤을 항상 맨 아래로
        self.cicd_log_text.config(state=tk.DISABLED)
    
    def clone_repository(self, repo_data):
        """
        리포지토리 클론
        
        Args:
            repo_data (Dict[str, Any]): 리포지토리 정보
        """
        if not repo_data:
            return
        
        # 기본 클론 경로 가져오기
        base_path = get_clone_base_path()
        repo_name = repo_data.get("name", "")
        target_path = os.path.join(base_path, repo_name)
        
        # 경로가 이미 존재하는 경우
        if os.path.exists(target_path):
            if os.path.isdir(target_path):
                result = messagebox.askquestion(
                    "확인",
                    f"'{target_path}'에 이미 디렉토리가 존재합니다. 원격 저장소 URL을 업데이트할까요?"
                )
                
                if result == "yes":
                    def task_func(dialog):
                        dialog.update_message(f"원격 저장소 URL 업데이트 중...")
                        success, result = update_repo_remote(
                            target_path, repo_data.get("clone_url", "")
                        )
                        return success, result
                    
                    def success_callback(result):
                        success, message = result
                        if success:
                            messagebox.showinfo("성공", "원격 저장소 URL이 업데이트되었습니다.")
                            self.local_repo_path = target_path
                            self.local_path_label.config(text=target_path)
                            self.open_local_button.config(state=tk.NORMAL)
                            self._load_local_branches()
                        else:
                            messagebox.showerror("오류", f"원격 저장소 URL 업데이트 실패: {message}")
                    
                    def error_callback(error):
                        messagebox.showerror("오류", f"원격 저장소 URL 업데이트 중 오류 발생: {error}")
                    
                    show_progress_dialog(
                        self, "원격 URL 업데이트", "원격 저장소 URL 업데이트 중...",
                        task_func, success_callback, error_callback
                    )
            else:
                messagebox.showerror(
                    "오류", 
                    f"'{target_path}'에 파일이 이미 존재합니다. 다른 경로를 선택하세요."
                )
            
            return
        
        # 새로운 클론 실행
        def task_func(dialog):
            dialog.update_message(f"리포지토리 '{repo_name}' 클론 중...")
            success, result = clone_repository(
                repo_data.get("clone_url", ""), target_path
            )
            return success, result
        
        def success_callback(result):
            success, message = result
            if success:
                messagebox.showinfo("성공", f"리포지토리가 '{target_path}'에 클론되었습니다.")
                self.local_repo_path = target_path
                self.local_path_label.config(text=target_path)
                self.open_local_button.config(state=tk.NORMAL)
                
                # UI 업데이트
                self.checkout_button.config(state=tk.NORMAL)
                self.refresh_branches_button.config(state=tk.NORMAL)
                self.create_branch_button.config(state=tk.NORMAL)
                self.refresh_commits_button.config(state=tk.NORMAL)
                self.run_cicd_button.config(state=tk.NORMAL)
                
                # 브랜치 정보 로드
                self._load_local_branches()
            else:
                messagebox.showerror("오류", f"리포지토리 클론 실패: {message}")
        
        def error_callback(error):
            messagebox.showerror("오류", f"리포지토리 클론 중 오류 발생: {error}")
        
        show_progress_dialog(
            self, "리포지토리 클론", f"리포지토리 '{repo_name}' 클론 중...",
            task_func, success_callback, error_callback
        )
    
    def rename_repository(self, repo_data):
        """
        리포지토리 이름 변경
        
        Args:
            repo_data (Dict[str, Any]): 리포지토리 정보
        """
        if not repo_data:
            return
        
        current_name = repo_data.get("name", "")
        
        def on_ok(new_name):
            if not new_name or new_name == current_name:
                return
            
            def task_func(dialog):
                dialog.update_message(f"리포지토리 이름 변경 중...")
                
                # GitHub에서 리포지토리 이름 변경
                success, result = github_client.rename_repository(
                    repo_data.get("full_name", ""), new_name
                )
                
                if not success:
                    return False, result
                
                # 로컬 리포지토리가 있으면 로컬 폴더도 이름 변경
                local_rename_success = True
                local_rename_msg = ""
                
                if self.local_repo_path and os.path.exists(self.local_repo_path):
                    base_path = os.path.dirname(self.local_repo_path)
                    new_path = os.path.join(base_path, new_name)
                    
                    local_rename_success, local_rename_msg = rename_local_repo_folder(
                        self.local_repo_path, new_path
                    )
                    
                    if local_rename_success:
                        self.local_repo_path = new_path
                
                return success and local_rename_success, {
                    "github_result": result,
                    "local_result": local_rename_msg,
                    "new_name": new_name
                }
            
            def success_callback(result):
                success, data = result
                
                if success:
                    messagebox.showinfo(
                        "성공", 
                        f"리포지토리 이름이 '{current_name}'에서 '{data['new_name']}'으로 변경되었습니다."
                    )
                    
                    # UI 업데이트
                    if self.local_repo_path:
                        self.local_path_label.config(text=self.local_repo_path)
                    
                    # 목록 새로고침
                    self.app.refresh_repos()
                else:
                    error_msg = data.get("github_result", "알 수 없는 오류")
                    if "local_result" in data and data["local_result"]:
                        error_msg += f"\n\n로컬 폴더 이름 변경 실패: {data['local_result']}"
                    
                    messagebox.showerror("오류", f"리포지토리 이름 변경 실패:\n{error_msg}")
            
            def error_callback(error):
                messagebox.showerror("오류", f"리포지토리 이름 변경 중 오류 발생: {error}")
            
            show_progress_dialog(
                self, "리포지토리 이름 변경", "리포지토리 이름 변경 중...",
                task_func, success_callback, error_callback
            )
        
        show_input_dialog(
            self, "리포지토리 이름 변경", "새 리포지토리 이름을 입력하세요:",
            initial_value=current_name, on_ok=on_ok
        )
    
    def delete_repository(self, repo_data):
        """
        리포지토리 삭제
        
        Args:
            repo_data (Dict[str, Any]): 리포지토리 정보
        """
        if not repo_data:
            return
        
        repo_name = repo_data.get("name", "")
        
        def on_confirm():
            def task_func(dialog):
                dialog.update_message(f"리포지토리 '{repo_name}' 삭제 중...")
                
                # GitHub에서 리포지토리 삭제
                success, result = github_client.delete_repository(
                    repo_data.get("full_name", "")
                )
                
                return success, result
            
            def success_callback(result):
                success, message = result
                
                if success:
                    messagebox.showinfo(
                        "성공", 
                        f"리포지토리 '{repo_name}'이(가) 삭제되었습니다."
                    )
                    
                    # 목록 새로고침 및 상세 뷰 초기화
                    self.clear()
                    self.app.refresh_repos()
                else:
                    messagebox.showerror("오류", f"리포지토리 삭제 실패: {message}")
            
            def error_callback(error):
                messagebox.showerror("오류", f"리포지토리 삭제 중 오류 발생: {error}")
            
            show_progress_dialog(
                self, "리포지토리 삭제", f"리포지토리 '{repo_name}' 삭제 중...",
                task_func, success_callback, error_callback
            )
        
        show_confirm_dialog(
            self, "리포지토리 삭제 확인",
            f"정말로 '{repo_name}' 리포지토리를 삭제하시겠습니까?\n\n"
            "이 작업은 되돌릴 수 없으며, 모든 데이터가 영구적으로 삭제됩니다.",
            on_confirm=on_confirm
        )