"""Arka plan işleri: arayüzü dondurmadan çalışan, iptal edilebilir QThread görevleri.

Görev fonksiyonları ``fn(job, *args)`` imzasına sahiptir ve arayüz nesnelerine
DOKUNMAZ; yalnızca ``job.status`` / ``job.progress`` sinyallerini kullanır.
"""

import logging
import threading
from collections import deque

from PyQt5.QtCore import QObject, QThread, pyqtSignal

from .downloader import Cancelled
from .i18n import T

log = logging.getLogger(__name__)


class Job(QThread):
    status = pyqtSignal(str)
    progress = pyqtSignal(int, int)  # done, total (total=0 -> belirsiz)
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, name: str, fn, *args, parent=None):
        super().__init__(parent)
        self.name = name
        self.fn = fn
        self.args = args
        self.cancel_event = threading.Event()

    def cancel(self) -> None:
        self.cancel_event.set()

    def emit_status(self, text: str) -> None:
        log.info("[%s] %s", self.name, text)
        self.status.emit(text)

    def emit_progress(self, done: int, total: int) -> None:
        # Qt int sinyali 32 bit; büyük byte değerlerini KB'ye indir
        if total > 2 ** 31 - 1 or done > 2 ** 31 - 1:
            done, total = done // 1024, total // 1024
        self.progress.emit(int(done), int(total))

    def run(self) -> None:
        try:
            result = self.fn(self, *self.args)
            self.succeeded.emit(result)
        except Cancelled:
            log.info("[%s] iptal edildi", self.name)
            self.failed.emit(T("İşlem iptal edildi.", "Operation cancelled."))
        except Exception as e:  # noqa: BLE001
            log.exception("[%s] hata", self.name)
            self.failed.emit(str(e) or e.__class__.__name__)


class JobQueue(QObject):
    """İşleri sırayla çalıştırır; aynı anda yalnızca bir motor/kurulum işi yürür."""

    busy_changed = pyqtSignal(bool)
    status = pyqtSignal(str)
    progress = pyqtSignal(int, int)
    error = pyqtSignal(str, str)  # iş adı, mesaj

    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue = deque()
        self.current = None
        self._finished_jobs = []

    @property
    def busy(self) -> bool:
        return self.current is not None

    def submit(self, name: str, fn, *args, on_success=None, on_error=None) -> None:
        self._queue.append((name, fn, args, on_success, on_error))
        if self.current is None:
            self._next()

    def clear_pending(self) -> None:
        self._queue.clear()

    def cancel_all(self) -> None:
        self._queue.clear()
        if self.current is not None:
            self.current.cancel()

    def wait(self, ms: int = 5000) -> None:
        if self.current is not None:
            self.current.wait(ms)

    def _next(self) -> None:
        if not self._queue:
            self.current = None
            self.busy_changed.emit(False)
            return
        name, fn, args, on_success, on_error = self._queue.popleft()
        job = Job(name, fn, *args, parent=self)
        job.status.connect(self.status)
        job.progress.connect(self.progress)

        def _ok(result, cb=on_success):
            if cb:
                try:
                    cb(result)
                except Exception:  # noqa: BLE001
                    log.exception("on_success hatası")

        def _err(msg, cb=on_error, n=name):
            if cb:
                cb(msg)
            else:
                self.error.emit(n, msg)
            self._queue.clear()  # bağımlı işler anlamsızlaşır

        job.succeeded.connect(_ok)
        job.failed.connect(_err)
        job.finished.connect(lambda j=job: self._on_finished(j))
        if self.current is None:
            self.busy_changed.emit(True)
        self.current = job
        job.start()

    def _on_finished(self, job) -> None:
        job.deleteLater()
        if self.current is job:
            self.current = None
        if self._queue:
            self._next()
        else:
            self.busy_changed.emit(False)


class BackgroundTask(QThread):
    """Kuyruk dışı küçük işler (logcat pid sorgusu, uygulama listesi vb.)."""

    done = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, fn, *args, parent=None):
        super().__init__(parent)
        self.fn, self.args = fn, args

    def run(self) -> None:
        try:
            self.done.emit(self.fn(*self.args))
        except Exception as e:  # noqa: BLE001
            log.exception("Arka plan görevi hatası")
            self.error.emit(str(e))


_running_tasks = set()


def run_bg(parent, fn, *args, on_done=None, on_error=None) -> BackgroundTask:
    t = BackgroundTask(fn, *args, parent=parent)
    _running_tasks.add(t)
    if on_done:
        t.done.connect(on_done)
    if on_error:
        t.error.connect(on_error)
    t.finished.connect(lambda: (_running_tasks.discard(t), t.deleteLater()))
    t.start()
    return t
