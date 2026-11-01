"""Devam ettirilebilir, zaman aşımlı, iptal edilebilir ve hash doğrulamalı indirici."""

import hashlib
import http.client
import logging
import os
import threading
import time
import urllib.error
import urllib.request

from . import __version__

log = logging.getLogger(__name__)
USER_AGENT = f"APKStudio/{__version__}"
CHUNK = 256 * 1024


class Cancelled(Exception):
    """Kullanıcı işlemi iptal etti."""


class ChecksumError(Exception):
    """İndirilen dosyanın hash değeri beklenenden farklı."""


def check_cancel(cancel: threading.Event = None) -> None:
    if cancel is not None and cancel.is_set():
        raise Cancelled()


def fetch_text(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def file_hash(path: str, algo: str = "sha256") -> str:
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def download(url: str, dest: str, progress=None, cancel: threading.Event = None,
             expected: tuple = None, timeout: int = 30, retries: int = 4) -> str:
    """``url``'yi ``dest``'e indirir.

    progress(done_bytes, total_bytes) çağrılır (total bilinmiyorsa 0).
    expected = ("sha256", "abcd...") verilirse doğrulanır, uyuşmazsa ChecksumError.
    Yarım kalan indirmeler ``dest + '.part'`` dosyasından Range ile devam eder.
    """
    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    part = dest + ".part"

    for attempt in range(1, retries + 1):
        check_cancel(cancel)
        existing = os.path.getsize(part) if os.path.exists(part) else 0
        headers = {"User-Agent": USER_AGENT}
        if existing:
            headers["Range"] = f"bytes={existing}-"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                status = getattr(r, "status", 200)
                if existing and status != 206:
                    existing = 0  # sunucu Range desteklemiyor, baştan indir
                mode = "ab" if existing else "wb"
                length = int(r.headers.get("Content-Length") or 0)
                total = existing + length if length else 0
                done = existing
                last_emit = 0.0
                with open(part, mode) as f:
                    while True:
                        check_cancel(cancel)
                        chunk = r.read(CHUNK)
                        if not chunk:
                            break
                        f.write(chunk)
                        done += len(chunk)
                        now = time.monotonic()
                        if progress and (now - last_emit > 0.15):
                            progress(done, total)
                            last_emit = now
                if total and done < total:
                    raise http.client.IncompleteRead(b"", total - done)
                if progress:
                    progress(done, total or done)
            break
        except urllib.error.HTTPError as e:
            if e.code == 416 and existing:
                log.info("Range 416: parça dosya zaten tam kabul ediliyor (%s)", part)
                break
            log.warning("İndirme HTTP hatası (%s/%s) %s: %s", attempt, retries, url, e)
            if attempt == retries or e.code in (403, 404):
                raise
        except (urllib.error.URLError, OSError, http.client.HTTPException) as e:
            log.warning("İndirme hatası (%s/%s) %s: %s", attempt, retries, url, e)
            if attempt == retries:
                raise
        time.sleep(min(2 * attempt, 8))

    if expected:
        algo, want = expected
        got = file_hash(part, algo)
        if got.lower() != want.lower():
            os.remove(part)
            raise ChecksumError(f"{os.path.basename(dest)}: {algo} uyuşmuyor (beklenen {want}, gelen {got})")
        log.info("%s doğrulandı (%s)", os.path.basename(dest), algo)
    else:
        log.warning("%s için hash doğrulaması yapılamadı", os.path.basename(dest))

    os.replace(part, dest)
    return dest
