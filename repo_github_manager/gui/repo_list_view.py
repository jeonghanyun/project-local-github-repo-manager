"""
리포지토리 목록 뷰 모듈
좌측 패널에 표시되는 리포지토리 목록을 관리합니다.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Any, Callable, Optional

from utils.logger import setup_logger

# 로거 설정
logger = setup_logger(__name__)


class RepoListView(ttk.Frame):
    """리포지토리 목록을 표시하는 뷰"""
    
    def __init__(self, parent, on_select_callback: Callable[[Dict[str, Any]], None], **kwargs):
        """
        리포지토리 목록 뷰 초기화
        
        Args:
            parent: 부모 위젯
            on_select_callback (Callable[[Dict[str, Any]], None]): 리포지토리 선택 시 호출할 콜백
            **kwargs: ttk.Frame에 전달할 추가 인자
        """
        super().__init__(parent, **kwargs)
        
        self.on_select_callback = on_select_callback
        self.repositories = []
        self.repo_id_map = {}  # id -> repository_data
        
        # 컨트롤 프레임
        self.control_frame = ttk.Frame(self)
        self.control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 검색 입력 필드
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search_changed)
        
        ttk.Label(self.control_frame, text="검색:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry = ttk.Entry(self.control_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 새로고침 버튼
        self.refresh_button = ttk.Button(
            self.control_frame, text="새로고침", command=self._on_refresh_clicked
        )
        self.refresh_button.pack(side=tk.RIGHT, padx=5)
        
        # 목록 표시 TreeView
        columns = ("name", "description", "private")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")
        
        # 컬럼 설정
        self.tree.heading("name", text="이름")
        self.tree.heading("description", text="설명")
        self.tree.heading("private", text="비공개")
        
        self.tree.column("name", width=150, anchor=tk.W)
        self.tree.column("description", width=250, anchor=tk.W)
        self.tree.column("private", width=60, anchor=tk.CENTER)
        
        # 스크롤바
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # 위젯 배치
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)
        
        # 이벤트 바인딩
        self.tree.bind("<<TreeviewSelect>>", self._on_repo_selected)
        self.tree.bind("<Double-1>", self._on_repo_double_clicked)
        
        # 컨텍스트 메뉴
        self.context_menu = self._create_context_menu()
        self.tree.bind("<Button-3>", self._on_right_click)  # 우클릭 이벤트
    
    def _create_context_menu(self) -> tk.Menu:
        """
        컨텍스트 메뉴 생성
        
        Returns:
            tk.Menu: 컨텍스트 메뉴
        """
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="클론", command=self._on_clone_clicked)
        menu.add_command(label="브라우저에서 열기", command=self._on_open_in_browser_clicked)
        menu.add_separator()
        menu.add_command(label="이름 변경", command=self._on_rename_clicked)
        menu.add_command(label="삭제", command=self._on_delete_clicked)
        return menu
    
    def set_repositories(self, repositories: List[Dict[str, Any]]):
        """
        리포지토리 목록 설정
        
        Args:
            repositories (List[Dict[str, Any]]): 리포지토리 정보 목록
        """
        self.repositories = repositories
        self.repo_id_map = {repo["id"]: repo for repo in repositories}
        self._refresh_tree()
    
    def _refresh_tree(self):
        """트리 뷰 갱신"""
        # 기존 항목 삭제
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 검색 필터링
        search_text = self.search_var.get().lower()
        filtered_repos = [
            repo for repo in self.repositories
            if (
                search_text == "" or
                search_text in repo["name"].lower() or
                (repo["description"] and search_text in repo["description"].lower())
            )
        ]
        
        # 새 항목 추가
        for repo in filtered_repos:
            private_text = "예" if repo["private"] else "아니오"
            description = repo["description"] if repo["description"] else ""
            
            self.tree.insert(
                "", "end", 
                values=(repo["name"], description, private_text),
                tags=("private" if repo["private"] else "public",),
                iid=str(repo["id"]),
            )
        
        # 태그 설정
        self.tree.tag_configure("private", foreground="darkred")
    
    def _on_search_changed(self, *args):
        """검색 텍스트 변경 이벤트 핸들러"""
        self._refresh_tree()
    
    def _on_refresh_clicked(self):
        """새로고침 버튼 클릭 이벤트 핸들러"""
        # 부모 메인 윈도우의 refresh_repos 메서드 호출
        parent = self.winfo_toplevel()
        if hasattr(parent, "refresh_repos") and callable(parent.refresh_repos):
            parent.refresh_repos()
    
    def _on_repo_selected(self, event):
        """리포지토리 선택 이벤트 핸들러"""
        selection = self.tree.selection()
        if selection:
            repo_id = int(selection[0])
            if repo_id in self.repo_id_map:
                repo_data = self.repo_id_map[repo_id]
                self.on_select_callback(repo_data)
    
    def _on_repo_double_clicked(self, event):
        """리포지토리 더블 클릭 이벤트 핸들러"""
        # 더블 클릭 시 브라우저에서 열기
        self._on_open_in_browser_clicked()
    
    def _on_right_click(self, event):
        """우클릭 이벤트 핸들러 (컨텍스트 메뉴 표시)"""
        # 클릭된 항목 선택
        clicked_item = self.tree.identify_row(event.y)
        if clicked_item:
            self.tree.selection_set(clicked_item)
            self._on_repo_selected(None)  # 선택 콜백 호출
            self.context_menu.post(event.x_root, event.y_root)
    
    def _get_selected_repo(self) -> Optional[Dict[str, Any]]:
        """
        현재 선택된 리포지토리 정보 반환
        
        Returns:
            Optional[Dict[str, Any]]: 선택된 리포지토리 정보 또는 None
        """
        selection = self.tree.selection()
        if selection:
            repo_id = int(selection[0])
            if repo_id in self.repo_id_map:
                return self.repo_id_map[repo_id]
        return None
    
    def _on_clone_clicked(self):
        """클론 메뉴 클릭 이벤트 핸들러"""
        repo_data = self._get_selected_repo()
        if not repo_data:
            return
        
        # 부모 앱에 클론 요청
        parent = self.winfo_toplevel()
        if hasattr(parent, "repo_details_view") and hasattr(parent.repo_details_view, "clone_repository"):
            parent.repo_details_view.clone_repository(repo_data)
    
    def _on_open_in_browser_clicked(self):
        """브라우저에서 열기 메뉴 클릭 이벤트 핸들러"""
        import webbrowser
        
        repo_data = self._get_selected_repo()
        if not repo_data or "html_url" not in repo_data:
            return
        
        # 브라우저에서 리포지토리 페이지 열기
        webbrowser.open(repo_data["html_url"])
    
    def _on_rename_clicked(self):
        """이름 변경 메뉴 클릭 이벤트 핸들러"""
        repo_data = self._get_selected_repo()
        if not repo_data:
            return
        
        # 부모 앱에 이름 변경 요청
        parent = self.winfo_toplevel()
        if hasattr(parent, "repo_details_view") and hasattr(parent.repo_details_view, "rename_repository"):
            parent.repo_details_view.rename_repository(repo_data)
    
    def _on_delete_clicked(self):
        """삭제 메뉴 클릭 이벤트 핸들러"""
        repo_data = self._get_selected_repo()
        if not repo_data:
            return
        
        # 부모 앱에 삭제 요청
        parent = self.winfo_toplevel()
        if hasattr(parent, "repo_details_view") and hasattr(parent.repo_details_view, "delete_repository"):
            parent.repo_details_view.delete_repository(repo_data) 