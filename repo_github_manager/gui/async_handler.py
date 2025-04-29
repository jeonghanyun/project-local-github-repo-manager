"""
비동기 작업 처리 모듈
백그라운드 스레드에서 시간이 오래 걸리는 작업을 실행하고 GUI에 결과를 전달합니다.
"""
import threading
import queue
import time
import traceback
from typing import Callable, Dict, Any, Optional, Tuple, List, Union

from utils.logger import setup_logger

# 로거 설정
logger = setup_logger(__name__)


class AsyncTask:
    """비동기 작업을 나타내는 클래스"""
    
    def __init__(self, task_id: str, task_func: Callable, callback: Callable, 
                 error_callback: Callable, *args, **kwargs):
        """
        비동기 작업 초기화
        
        Args:
            task_id (str): 작업 ID
            task_func (Callable): 실행할 함수
            callback (Callable): 성공 시 호출할 콜백
            error_callback (Callable): 오류 발생 시 호출할 콜백
            *args: task_func에 전달할 위치 인자
            **kwargs: task_func에 전달할 키워드 인자
        """
        self.task_id = task_id
        self.task_func = task_func
        self.callback = callback
        self.error_callback = error_callback
        self.args = args
        self.kwargs = kwargs
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None
        self.is_cancelled = False
    
    def execute(self) -> None:
        """작업을 실행하고 결과 또는 오류를 저장"""
        if self.is_cancelled:
            return
        
        self.start_time = time.time()
        try:
            self.result = self.task_func(*self.args, **self.kwargs)
            self.end_time = time.time()
        except Exception as e:
            self.error = e
            self.end_time = time.time()
            logger.error(f"비동기 작업 '{self.task_id}' 실행 중 오류 발생: {str(e)}")
            logger.debug(traceback.format_exc())
    
    def cancel(self) -> None:
        """작업 취소 (아직 시작하지 않은 경우)"""
        self.is_cancelled = True
    
    def get_duration(self) -> Optional[float]:
        """작업 실행 시간 반환 (초)"""
        if self.start_time is None:
            return None
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time


class AsyncHandler:
    """비동기 작업 처리기"""
    
    def __init__(self, max_workers: int = 5):
        """
        비동기 처리기 초기화
        
        Args:
            max_workers (int, optional): 최대 작업자 스레드 수
        """
        self.tasks_queue = queue.Queue()
        self.results_queue = queue.Queue()
        self.workers = []
        self.running = False
        self.max_workers = max_workers
        self.active_tasks = {}  # 작업 ID -> AsyncTask
        self.task_id_counter = 0
        self.lock = threading.Lock()
    
    def start(self) -> None:
        """작업자 스레드를 시작"""
        if self.running:
            return
        
        self.running = True
        
        # 작업자 스레드 생성
        for _ in range(self.max_workers):
            worker = threading.Thread(target=self._worker_loop, daemon=True)
            worker.start()
            self.workers.append(worker)
        
        # 결과 처리 스레드 생성
        self.result_thread = threading.Thread(target=self._process_results, daemon=True)
        self.result_thread.start()
        
        logger.info(f"비동기 작업 처리기가 시작되었습니다. 작업자 수: {self.max_workers}")
    
    def stop(self) -> None:
        """모든 작업자 스레드 종료"""
        self.running = False
        
        # 대기 중인 모든 작업 취소
        while not self.tasks_queue.empty():
            try:
                task = self.tasks_queue.get_nowait()
                task.cancel()
                self.tasks_queue.task_done()
            except queue.Empty:
                break
        
        logger.info("비동기 작업 처리기가 중지되었습니다.")
    
    def _worker_loop(self) -> None:
        """작업자 스레드의 메인 루프"""
        while self.running:
            try:
                task = self.tasks_queue.get(timeout=0.5)  # 0.5초 대기
                
                if not task.is_cancelled:
                    task.execute()
                    self.results_queue.put(task)
                
                self.tasks_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"작업자 스레드에서 예기치 않은 오류 발생: {str(e)}")
                logger.debug(traceback.format_exc())
    
    def _process_results(self) -> None:
        """결과 처리 스레드의 메인 루프"""
        while self.running:
            try:
                task = self.results_queue.get(timeout=0.5)  # 0.5초 대기
                
                with self.lock:
                    if task.task_id in self.active_tasks:
                        del self.active_tasks[task.task_id]
                
                if task.error:
                    if task.error_callback:
                        task.error_callback(task.error)
                else:
                    if task.callback:
                        task.callback(task.result)
                
                self.results_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"결과 처리 스레드에서 예기치 않은 오류 발생: {str(e)}")
                logger.debug(traceback.format_exc())
    
    def submit_task(self, task_func: Callable, callback: Callable = None, 
                    error_callback: Callable = None, *args, **kwargs) -> str:
        """
        비동기 작업 제출
        
        Args:
            task_func (Callable): 실행할 함수
            callback (Callable, optional): 성공 시 호출할 콜백
            error_callback (Callable, optional): 오류 발생 시 호출할 콜백
            *args: task_func에 전달할 위치 인자
            **kwargs: task_func에 전달할 키워드 인자
        
        Returns:
            str: 작업 ID
        """
        if not self.running:
            self.start()
        
        with self.lock:
            task_id = f"task_{self.task_id_counter}"
            self.task_id_counter += 1
        
        task = AsyncTask(task_id, task_func, callback, error_callback, *args, **kwargs)
        
        with self.lock:
            self.active_tasks[task_id] = task
        
        self.tasks_queue.put(task)
        logger.debug(f"작업 '{task_id}'이(가) 제출되었습니다.")
        
        return task_id
    
    def cancel_task(self, task_id: str) -> bool:
        """
        지정된 ID의 작업을 취소 (아직 시작하지 않은 경우)
        
        Args:
            task_id (str): 취소할 작업 ID
        
        Returns:
            bool: 취소 성공 여부
        """
        with self.lock:
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                task.cancel()
                logger.debug(f"작업 '{task_id}'이(가) 취소되었습니다.")
                return True
        return False
    
    def get_active_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        현재 활성 작업 목록 반환
        
        Returns:
            Dict[str, Dict[str, Any]]: 작업 ID -> 작업 정보
        """
        result = {}
        with self.lock:
            for task_id, task in self.active_tasks.items():
                result[task_id] = {
                    'id': task_id,
                    'start_time': task.start_time,
                    'duration': task.get_duration(),
                    'is_cancelled': task.is_cancelled,
                }
        return result


# 싱글톤 인스턴스
async_handler = AsyncHandler() 