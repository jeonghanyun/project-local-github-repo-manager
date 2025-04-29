"""
기본 UI 레이아웃 모듈
Tkinter를 사용하여 애플리케이션의 기본 UI 레이아웃을 구현합니다.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import sys
import logging

from utils.logger import setup_logger
from utils.macos_utils import check_system_requirements

# 로거 설정
logger = logging.getLogger(__name__)


class MainWindow(tk.Tk):
    """
    메인 윈도우 클래스
    GitHub 저장소 관리자의 기본 UI 레이아웃을 구현합니다.
    """
    
    def __init__(self):
        """메인 윈도우 초기화"""
        super().__init__()
        
        # 시스템 요구사항 확인
        self._check_requirements()
        
        # 윈도우 기본 설정
        self.title("GitHub 저장소 관리자")
        self.geometry("1024x768")  # 기본 창 크기
        self.minsize(800, 600)     # 최소 창 크기
        
        # macOS 스타일 설정
        if sys.platform == 'darwin':
            self.style = ttk.Style()
            self.style.theme_use('aqua')
        
        # UI 컴포넌트 초기화
        self._init_menu()
        self._init_main_layout()
        self._init_status_bar()
        
        # 초기 상태 메시지
        self.status_message("준비")
        
        logger.info("메인 윈도우가 초기화되었습니다.")
    
    def _check_requirements(self):
        """시스템 요구사항 확인"""
        requirements = check_system_requirements()
        
        if not requirements["is_macos"]:
            messagebox.showerror(
                "시스템 요구사항 오류",
                "이 애플리케이션은 macOS에서만 실행할 수 있습니다."
            )
            sys.exit(1)
        
        if not requirements["git_available"]:
            messagebox.showerror(
                "시스템 요구사항 오류",
                "Git이 설치되어 있지 않습니다. Git을 설치한 후 다시 실행하세요."
            )
            sys.exit(1)
        
        if not requirements["config_permission"]:
            messagebox.showerror(
                "권한 오류",
                "애플리케이션 설정 디렉토리에 쓰기 권한이 없습니다."
            )
            sys.exit(1)
        
        logger.info("시스템 요구사항 확인 완료")
    
    def _init_menu(self):
        """메뉴 바 초기화"""
        self.menu_bar = tk.Menu(self)
        
        # 파일 메뉴
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="새 리포지토리", command=self._placeholder)
        file_menu.add_separator()
        file_menu.add_command(label="종료", command=self.quit)
        self.menu_bar.add_cascade(label="파일", menu=file_menu)
        
        # 보기 메뉴
        view_menu = tk.Menu(self.menu_bar, tearoff=0)
        view_menu.add_command(label="리포지토리 목록 새로고침", command=self._placeholder)
        self.menu_bar.add_cascade(label="보기", menu=view_menu)
        
        # 도움말 메뉴
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        help_menu.add_command(label="정보", command=self._show_about)
        self.menu_bar.add_cascade(label="도움말", menu=help_menu)
        
        self.config(menu=self.menu_bar)
        logger.debug("메뉴 바가 초기화되었습니다.")
    
    def _init_main_layout(self):
        """중앙 분할 영역 및 패널 초기화"""
        # 메인 프레임
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 중앙 분할 영역 (Paned Window)
        self.paned_window = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        # 좌측 패널: 리포지토리 목록
        self.left_panel = ttk.Frame(self.paned_window)
        self._init_left_panel()
        
        # 우측 패널: 리포지토리 상세 정보
        self.right_panel = ttk.Frame(self.paned_window)
        self._init_right_panel()
        
        # Paned Window에 패널 추가
        self.paned_window.add(self.left_panel, weight=1)  # 1:2 비율로 공간 분할
        self.paned_window.add(self.right_panel, weight=2)
        
        logger.debug("중앙 분할 영역이 초기화되었습니다.")
    
    def _init_left_panel(self):
        """좌측 패널: 리포지토리 목록 영역 초기화"""
        # 검색 및 새로고침 영역
        control_frame = ttk.Frame(self.left_panel)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(control_frame, text="검색:").pack(side=tk.LEFT, padx=(0, 5))
        search_entry = ttk.Entry(control_frame)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        refresh_button = ttk.Button(control_frame, text="새로고침", command=self._placeholder)
        refresh_button.pack(side=tk.RIGHT, padx=5)
        
        # 리포지토리 목록 트리뷰
        columns = ("name", "description", "private")
        self.repo_tree = ttk.Treeview(self.left_panel, columns=columns, show="headings")
        
        # 컬럼 설정
        self.repo_tree.heading("name", text="이름")
        self.repo_tree.heading("description", text="설명")
        self.repo_tree.heading("private", text="비공개")
        
        self.repo_tree.column("name", width=150, anchor=tk.W)
        self.repo_tree.column("description", width=250, anchor=tk.W)
        self.repo_tree.column("private", width=60, anchor=tk.CENTER)
        
        # 스크롤바
        scrollbar = ttk.Scrollbar(self.left_panel, orient=tk.VERTICAL, command=self.repo_tree.yview)
        self.repo_tree.configure(yscrollcommand=scrollbar.set)
        
        # 위젯 배치
        self.repo_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)
        
        logger.debug("좌측 패널이 초기화되었습니다.")
    
    def _init_right_panel(self):
        """우측 패널: 탭 영역 초기화"""
        # 노트북 (탭 컨테이너)
        self.notebook = ttk.Notebook(self.right_panel)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 정보 탭
        self.info_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.info_tab, text="정보")
        
        # 브랜치 탭
        self.branches_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.branches_tab, text="브랜치")
        
        # 커밋 탭
        self.commits_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.commits_tab, text="커밋")
        
        # Pull Requests 탭
        self.pr_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.pr_tab, text="Pull Requests")
        
        # CI/CD 탭
        self.cicd_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.cicd_tab, text="CI/CD")
        
        # 간단한 정보 메시지 추가 (실제 구현 전 임시)
        for tab in [self.info_tab, self.branches_tab, self.commits_tab, self.pr_tab, self.cicd_tab]:
            ttk.Label(tab, text="이 탭의 콘텐츠는 추후 구현될 예정입니다.").pack(pady=20)
        
        logger.debug("우측 패널이 초기화되었습니다.")
    
    def _init_status_bar(self):
        """하단 상태 표시줄 영역 초기화"""
        self.status_bar = ttk.Frame(self)
        self.status_bar.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        self.status_label = ttk.Label(self.status_bar, text="준비")
        self.status_label.pack(side=tk.LEFT)
        
        self.progress_bar = ttk.Progressbar(
            self.status_bar, mode="indeterminate", length=100
        )
        # 기본적으로 진행 표시줄은 숨김
        # 필요할 때만 표시됨
        
        logger.debug("상태 표시줄이 초기화되었습니다.")
    
    def status_message(self, message, show_progress=False):
        """상태 메시지 표시"""
        self.status_label.config(text=message)
        
        if show_progress:
            self.progress_bar.start(10)
            self.progress_bar.pack(side=tk.RIGHT)
        else:
            self.progress_bar.stop()
            self.progress_bar.pack_forget()
        
        self.update_idletasks()
    
    def _placeholder(self):
        """임시 함수 (실제 기능이 구현되기 전까지 사용)"""
        messagebox.showinfo("알림", "이 기능은 아직 구현되지 않았습니다.")
    
    def _show_about(self):
        """정보 다이얼로그 표시"""
        messagebox.showinfo(
            "GitHub 저장소 관리자 정보",
            "GitHub 저장소 관리자\n\n"
            "버전: 0.1.0\n"
            "macOS용 GitHub 리포지토리 관리 도구\n"
        )
    
    def on_close(self):
        """애플리케이션 종료 이벤트 핸들러"""
        self.destroy()


def main():
    """애플리케이션 진입점"""
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # 애플리케이션 실행
    app = MainWindow()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()


if __name__ == "__main__":
    main() 