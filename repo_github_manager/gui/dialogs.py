"""
UI 다이얼로그 모듈
사용자 입력을 받거나 정보를 표시하는 다양한 다이얼로그 창을 제공합니다.
"""
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Callable, Dict, Any, List, Tuple

from utils.logger import setup_logger

# 로거 설정
logger = setup_logger(__name__)


class InputDialog(tk.Toplevel):
    """사용자 입력을 받는 다이얼로그"""
    
    def __init__(self, parent, title: str, message: str, 
                 fields: List[Dict[str, Any]], width: int = 400, height: int = 200):
        """
        입력 다이얼로그 초기화
        
        Args:
            parent: 부모 윈도우
            title (str): 창 제목
            message (str): 안내 메시지
            fields (List[Dict[str, Any]]): 입력 필드 정보 목록
                [{"name": "name", "label": "이름", "type": "entry", "default": "", "required": True}, ...]
                type: "entry", "password", "combobox", "checkbox", "radiobutton"
            width (int, optional): 창 너비
            height (int, optional): 창 높이
        """
        super().__init__(parent)
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self.result = None
        self.fields = fields
        self.field_widgets = {}
        
        # 메시지 레이블
        ttk.Label(self, text=message, wraplength=width-40).pack(pady=(15, 10), padx=20)
        
        # 입력 필드 프레임
        frame = ttk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # 필드 생성
        for row, field in enumerate(fields):
            field_name = field.get("name", "")
            field_label = field.get("label", field_name)
            field_type = field.get("type", "entry")
            field_default = field.get("default", "")
            field_options = field.get("options", [])
            field_required = field.get("required", False)
            
            # 레이블
            label_text = field_label
            if field_required:
                label_text += " *"
            label = ttk.Label(frame, text=label_text)
            label.grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
            
            # 입력 위젯
            if field_type == "entry":
                widget = ttk.Entry(frame)
                widget.insert(0, field_default)
                widget.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
                self.field_widgets[field_name] = widget
            
            elif field_type == "password":
                widget = ttk.Entry(frame, show="*")
                widget.insert(0, field_default)
                widget.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
                self.field_widgets[field_name] = widget
            
            elif field_type == "combobox":
                widget = ttk.Combobox(frame, values=field_options)
                if field_default in field_options:
                    widget.set(field_default)
                elif field_options:
                    widget.set(field_options[0])
                widget.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
                self.field_widgets[field_name] = widget
            
            elif field_type == "checkbox":
                var = tk.BooleanVar(value=field_default)
                widget = ttk.Checkbutton(frame, variable=var)
                widget.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
                self.field_widgets[field_name] = var
            
            elif field_type == "radiobutton":
                var = tk.StringVar(value=field_default)
                radio_frame = ttk.Frame(frame)
                radio_frame.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
                
                for i, option in enumerate(field_options):
                    rb = ttk.Radiobutton(
                        radio_frame, text=option, value=option, variable=var
                    )
                    rb.pack(side=tk.LEFT, padx=5)
                
                self.field_widgets[field_name] = var
        
        # 컬럼 설정
        frame.columnconfigure(1, weight=1)
        
        # 버튼 프레임
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
        
        # 취소 버튼
        ttk.Button(button_frame, text="취소", command=self.cancel).pack(side=tk.RIGHT, padx=5)
        
        # 확인 버튼
        ttk.Button(button_frame, text="확인", command=self.submit).pack(side=tk.RIGHT, padx=5)
        
        # ESC 키 바인딩
        self.bind("<Escape>", lambda event: self.cancel())
        
        # 다이얼로그가 닫힐 때까지 대기
        self.wait_window()
    
    def submit(self) -> None:
        """입력 값 제출"""
        # 필수 필드 확인
        for field in self.fields:
            field_name = field.get("name", "")
            field_required = field.get("required", False)
            
            if field_required:
                widget = self.field_widgets.get(field_name)
                if widget is None:
                    continue
                
                if isinstance(widget, (ttk.Entry, ttk.Combobox)):
                    if not widget.get().strip():
                        messagebox.showerror("오류", f"{field.get('label', field_name)}은(는) 필수 항목입니다.")
                        return
                elif isinstance(widget, (tk.BooleanVar, tk.StringVar)):
                    # 변수 기반 위젯은 항상 값이 있음
                    pass
        
        # 결과 수집
        self.result = {}
        for field in self.fields:
            field_name = field.get("name", "")
            widget = self.field_widgets.get(field_name)
            
            if widget is None:
                continue
            
            if isinstance(widget, (ttk.Entry, ttk.Combobox)):
                self.result[field_name] = widget.get()
            elif isinstance(widget, (tk.BooleanVar, tk.StringVar)):
                self.result[field_name] = widget.get()
        
        self.destroy()
    
    def cancel(self) -> None:
        """다이얼로그 취소"""
        self.result = None
        self.destroy()


class ConfirmDialog(tk.Toplevel):
    """사용자 확인을 받는 다이얼로그"""
    
    def __init__(self, parent, title: str, message: str, 
                 confirm_text: str = "확인", 
                 cancel_text: str = "취소",
                 width: int = 400, height: int = 150,
                 danger: bool = False,
                 verification_text: Optional[str] = None):
        """
        확인 다이얼로그 초기화
        
        Args:
            parent: 부모 윈도우
            title (str): 창 제목
            message (str): 확인 메시지
            confirm_text (str, optional): 확인 버튼 텍스트
            cancel_text (str, optional): 취소 버튼 텍스트
            width (int, optional): 창 너비
            height (int, optional): 창 높이
            danger (bool, optional): 위험 작업 여부 (빨간색 확인 버튼)
            verification_text (Optional[str], optional): 
                검증 텍스트 (지정 시 사용자가 텍스트를 입력해야 확인 가능)
        """
        super().__init__(parent)
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self.result = False
        self.verification_text = verification_text
        self.verification_entry = None
        
        # 메시지 레이블
        ttk.Label(self, text=message, wraplength=width-40).pack(pady=(15, 10), padx=20)
        
        # 검증 텍스트 입력 필드
        if verification_text:
            frame = ttk.Frame(self)
            frame.pack(fill=tk.X, padx=20, pady=5)
            
            ttk.Label(frame, text=f"확인을 위해 다음을 입력하세요: '{verification_text}'").pack(anchor=tk.W)
            self.verification_entry = ttk.Entry(frame, width=40)
            self.verification_entry.pack(pady=5, fill=tk.X)
        
        # 버튼 프레임
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=20, pady=(5, 15))
        
        # 취소 버튼
        ttk.Button(button_frame, text=cancel_text, command=self.cancel).pack(side=tk.RIGHT, padx=5)
        
        # 확인 버튼
        confirm_button = ttk.Button(button_frame, text=confirm_text, command=self.confirm)
        confirm_button.pack(side=tk.RIGHT, padx=5)
        
        # 위험 작업의 경우 확인 버튼에 스타일 적용
        if danger:
            self.style = ttk.Style()
            self.style.configure("Danger.TButton", foreground="red")
            confirm_button.configure(style="Danger.TButton")
        
        # ESC 키 바인딩
        self.bind("<Escape>", lambda event: self.cancel())
        
        # 다이얼로그가 닫힐 때까지 대기
        self.wait_window()
    
    def confirm(self) -> None:
        """확인 버튼 클릭"""
        # 검증 텍스트 확인
        if self.verification_text and self.verification_entry:
            entered_text = self.verification_entry.get()
            if entered_text != self.verification_text:
                messagebox.showerror("오류", "입력한 텍스트가 일치하지 않습니다.")
                return
        
        self.result = True
        self.destroy()
    
    def cancel(self) -> None:
        """취소 버튼 클릭"""
        self.result = False
        self.destroy()


class ProgressDialog(tk.Toplevel):
    """진행 상황을 표시하는 다이얼로그"""
    
    def __init__(self, parent, title: str, message: str, width: int = 400, height: int = 150):
        """
        진행 다이얼로그 초기화
        
        Args:
            parent: 부모 윈도우
            title (str): 창 제목
            message (str): 진행 메시지
            width (int, optional): 창 너비
            height (int, optional): 창 높이
        """
        super().__init__(parent)
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self.is_cancelled = False
        
        # 메시지 레이블
        self.message_label = ttk.Label(self, text=message, wraplength=width-40)
        self.message_label.pack(pady=(15, 10), padx=20)
        
        # 진행 표시줄
        self.progressbar = ttk.Progressbar(self, mode="indeterminate", length=width-40)
        self.progressbar.pack(padx=20, pady=10, fill=tk.X)
        self.progressbar.start(10)
        
        # 버튼 프레임
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=20, pady=(5, 15))
        
        # 취소 버튼
        self.cancel_button = ttk.Button(button_frame, text="취소", command=self.cancel)
        self.cancel_button.pack(side=tk.RIGHT, padx=5)
        
        # ESC 키 바인딩
        self.bind("<Escape>", lambda event: self.cancel())
        
        # 창 닫기 버튼 비활성화 (프로토콜 무시)
        self.protocol("WM_DELETE_WINDOW", lambda: None)
    
    def update_message(self, message: str) -> None:
        """
        진행 메시지 업데이트
        
        Args:
            message (str): 새 메시지
        """
        self.message_label.config(text=message)
        self.update()
    
    def set_progress(self, value: float) -> None:
        """
        진행률 설정 (0-100)
        
        Args:
            value (float): 진행률
        """
        if value < 0:
            value = 0
        elif value > 100:
            value = 100
        
        if self.progressbar["mode"] == "indeterminate":
            self.progressbar.stop()
            self.progressbar["mode"] = "determinate"
        
        self.progressbar["value"] = value
        self.update()
    
    def cancel(self) -> None:
        """취소 버튼 클릭"""
        self.is_cancelled = True
        self.cancel_button.config(state=tk.DISABLED)
        self.update_message("작업을 취소하는 중...")
    
    def close(self) -> None:
        """다이얼로그 닫기"""
        self.grab_release()
        self.destroy()


def show_input_dialog(parent, title: str, message: str, 
                      fields: List[Dict[str, Any]], **kwargs) -> Optional[Dict[str, Any]]:
    """
    입력 다이얼로그 표시
    
    Args:
        parent: 부모 윈도우
        title (str): 창 제목
        message (str): 안내 메시지
        fields (List[Dict[str, Any]]): 입력 필드 정보 목록
        **kwargs: InputDialog에 전달할 추가 인자
    
    Returns:
        Optional[Dict[str, Any]]: 입력 결과 또는 None (취소 시)
    """
    dialog = InputDialog(parent, title, message, fields, **kwargs)
    return dialog.result


def show_confirm_dialog(parent, title: str, message: str, **kwargs) -> bool:
    """
    확인 다이얼로그 표시
    
    Args:
        parent: 부모 윈도우
        title (str): 창 제목
        message (str): 확인 메시지
        **kwargs: ConfirmDialog에 전달할 추가 인자
    
    Returns:
        bool: 확인 여부
    """
    dialog = ConfirmDialog(parent, title, message, **kwargs)
    return dialog.result


def show_progress_dialog(parent, title: str, message: str, task_func: Callable,
                         success_callback: Optional[Callable] = None,
                         error_callback: Optional[Callable] = None,
                         **kwargs) -> Optional[Any]:
    """
    진행 다이얼로그 표시 및 작업 실행
    
    Args:
        parent: 부모 윈도우
        title (str): 창 제목
        message (str): 진행 메시지
        task_func (Callable): 실행할 작업 함수
        success_callback (Optional[Callable], optional): 성공 시 콜백
        error_callback (Optional[Callable], optional): 오류 시 콜백
        **kwargs: ProgressDialog에 전달할 추가 인자
    
    Returns:
        Optional[Any]: 작업 결과 또는 None (취소 또는 오류 시)
    """
    dialog = ProgressDialog(parent, title, message, **kwargs)
    result = None
    error = None
    
    def worker():
        nonlocal result, error
        try:
            result = task_func(dialog)
        except Exception as e:
            error = e
        finally:
            parent.after(100, finish)
    
    def finish():
        dialog.close()
        
        if dialog.is_cancelled:
            if error_callback:
                error_callback("작업이 취소되었습니다.")
        elif error:
            if error_callback:
                error_callback(str(error))
            else:
                messagebox.showerror("오류", f"작업 중 오류가 발생했습니다: {str(error)}")
        else:
            if success_callback:
                success_callback(result)
        
    # 작업 스레드 시작
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    
    return result


def show_directory_dialog(parent, title: str = "디렉토리 선택", 
                          initialdir: Optional[str] = None) -> Optional[str]:
    """
    디렉토리 선택 다이얼로그 표시
    
    Args:
        parent: 부모 윈도우
        title (str, optional): 창 제목
        initialdir (Optional[str], optional): 초기 디렉토리
    
    Returns:
        Optional[str]: 선택한 디렉토리 경로 또는 None (취소 시)
    """
    if initialdir and not os.path.exists(initialdir):
        initialdir = os.path.expanduser("~")
    
    directory = filedialog.askdirectory(parent=parent, title=title, initialdir=initialdir)
    
    if directory:
        return directory
    return None 