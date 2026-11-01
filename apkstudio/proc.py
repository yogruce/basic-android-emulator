"""Konsol penceresi açmadan, zaman aşımlı alt süreç yardımcıları."""

import logging
import subprocess

log = logging.getLogger(__name__)
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def run(cmd, timeout: float = 30, text: bool = True, env=None, input=None, cwd=None) -> subprocess.CompletedProcess:
    """subprocess.run sarmalayıcı; zaman aşımında istisna yerine returncode=-1 döner."""
    try:
        return subprocess.run(
            [str(c) for c in cmd], capture_output=True, text=text, timeout=timeout, env=env,
            input=input, cwd=cwd, creationflags=NO_WINDOW,
            **({"encoding": "utf-8", "errors": "replace"} if text else {}),
        )
    except subprocess.TimeoutExpired:
        log.warning("Zaman aşımı (%ss): %s", timeout, " ".join(map(str, cmd)))
        return subprocess.CompletedProcess(cmd, -1, "" if text else b"", "timeout" if text else b"timeout")
    except OSError as e:
        log.error("Süreç başlatılamadı: %s (%s)", cmd[0], e)
        return subprocess.CompletedProcess(cmd, -2, "" if text else b"", str(e) if text else str(e).encode())


def popen(cmd, **kwargs) -> subprocess.Popen:
    kwargs.setdefault("creationflags", NO_WINDOW)
    return subprocess.Popen([str(c) for c in cmd], **kwargs)
