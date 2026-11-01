"""APK / split paket (.apks, .xapk, .apkm) çözümleme.

Paket adı, ek bir araca gerek kalmadan APK içindeki ikili AndroidManifest.xml
(AXML) dosyası doğrudan okunarak bulunur. Başarısız olursa aapt/aapt2 denenir.
"""

import json
import logging
import os
import re
import shutil
import struct
import tempfile
import zipfile
from dataclasses import dataclass, field

from . import proc

log = logging.getLogger(__name__)

RES_STRING_POOL_TYPE = 0x0001
RES_XML_TYPE = 0x0003
RES_XML_START_ELEMENT_TYPE = 0x0102
TYPE_STRING = 0x03
TYPE_INT_DEC = 0x10
TYPE_INT_HEX = 0x11
NO_ENTRY = 0xFFFFFFFF
UTF8_FLAG = 0x100


class ApkError(Exception):
    pass


# ---------------------------------------------------------------- AXML ------
def _len8(d: bytes, p: int):
    n = d[p]
    p += 1
    if n & 0x80:
        n = ((n & 0x7F) << 8) | d[p]
        p += 1
    return n, p


def _len16(d: bytes, p: int):
    n = struct.unpack_from("<H", d, p)[0]
    p += 2
    if n & 0x8000:
        n = ((n & 0x7FFF) << 16) | struct.unpack_from("<H", d, p)[0]
        p += 2
    return n, p


def _parse_string_pool(d: bytes, pos: int) -> list:
    _t, hsize, _size = struct.unpack_from("<HHI", d, pos)
    count, _styles, flags, strings_start, _styles_start = struct.unpack_from("<IIIII", d, pos + 8)
    offsets = struct.unpack_from(f"<{count}I", d, pos + hsize)
    base = pos + strings_start
    utf8 = bool(flags & UTF8_FLAG)
    out = []
    for off in offsets:
        p = base + off
        try:
            if utf8:
                _chars, p = _len8(d, p)
                nbytes, p = _len8(d, p)
                out.append(d[p:p + nbytes].decode("utf-8", errors="replace"))
            else:
                n, p = _len16(d, p)
                out.append(d[p:p + 2 * n].decode("utf-16-le", errors="replace"))
        except (IndexError, struct.error):
            out.append("")
    return out


def parse_manifest_attributes(data: bytes) -> dict:
    """İkili AndroidManifest.xml içindeki <manifest> öğesinin özniteliklerini döndürür."""
    if len(data) < 8:
        raise ApkError("AndroidManifest.xml çok kısa")
    t, hsize, _size = struct.unpack_from("<HHI", data, 0)
    if t != RES_XML_TYPE:
        raise ApkError("AndroidManifest.xml ikili XML değil")
    strings: list = []

    def s(i):
        return strings[i] if 0 <= i < len(strings) else ""

    pos = hsize
    while pos + 8 <= len(data):
        ctype, chsize, csize = struct.unpack_from("<HHI", data, pos)
        if csize < 8:
            break
        if ctype == RES_STRING_POOL_TYPE and not strings:
            strings = _parse_string_pool(data, pos)
        elif ctype == RES_XML_START_ELEMENT_TYPE:
            ext = pos + chsize
            _ns, name, attr_start, attr_size, attr_count = struct.unpack_from("<IIHHH", data, ext)
            if s(name) == "manifest":
                attrs = {}
                for i in range(attr_count):
                    a = ext + attr_start + i * attr_size
                    _ans, aname, raw = struct.unpack_from("<III", data, a)
                    _vsize, _res0, dtype, dval = struct.unpack_from("<HBBI", data, a + 12)
                    if raw != NO_ENTRY:
                        val = s(raw)
                    elif dtype == TYPE_STRING:
                        val = s(dval)
                    else:
                        val = dval
                    attrs[s(aname)] = val
                return attrs
        pos += csize
    raise ApkError("<manifest> öğesi bulunamadı")


@dataclass
class ApkInfo:
    package: str
    version_name: str = ""
    version_code: int = 0


def read_apk_info(apk_path: str, aapt_path: str = None) -> ApkInfo:
    try:
        with zipfile.ZipFile(apk_path) as zf:
            attrs = parse_manifest_attributes(zf.read("AndroidManifest.xml"))
        pkg = attrs.get("package")
        if isinstance(pkg, str) and pkg:
            vc = attrs.get("versionCode", 0)
            return ApkInfo(pkg, str(attrs.get("versionName", "") or ""), vc if isinstance(vc, int) else 0)
    except (zipfile.BadZipFile, KeyError, ApkError, struct.error) as e:
        log.warning("AXML okunamadı (%s): %s", os.path.basename(apk_path), e)

    if aapt_path:
        res = proc.run([aapt_path, "dump", "badging", apk_path], timeout=60)
        m = re.search(r"package:\s+name='([^']+)'(?:\s+versionCode='(\d*)')?(?:\s+versionName='([^']*)')?", res.stdout or "")
        if m:
            return ApkInfo(m.group(1), m.group(3) or "", int(m.group(2) or 0))
    raise ApkError(f"Paket adı okunamadı: {os.path.basename(apk_path)}")


# ------------------------------------------------------- split paketler -----
@dataclass
class InstallBundle:
    """Kuruluma hazır dosya grubu."""
    source: str
    apks: list
    obb: list = field(default_factory=list)  # [(yerel_yol, cihaz_yolu)]
    package: str = ""
    version_name: str = ""
    temp_dir: str = ""

    def cleanup(self) -> None:
        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)


def prepare_bundle(path: str, work_root: str, aapt_path: str = None) -> InstallBundle:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".aab":
        raise ApkError("AAB dosyaları doğrudan kurulamaz; bundletool ile .apks dosyasına dönüştürün.")
    if ext == ".apk":
        info = read_apk_info(path, aapt_path)
        return InstallBundle(path, [path], package=info.package, version_name=info.version_name)
    if ext not in (".apks", ".xapk", ".apkm"):
        raise ApkError(f"Desteklenmeyen dosya türü: {ext}")

    tmp = tempfile.mkdtemp(prefix="bundle_", dir=work_root)
    bundle = InstallBundle(path, [], temp_dir=tmp)
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            manifest = {}
            if "manifest.json" in names:
                try:
                    manifest = json.loads(zf.read("manifest.json").decode("utf-8", errors="replace"))
                except ValueError:
                    manifest = {}
            apk_names = [n for n in names if n.lower().endswith(".apk") and not n.startswith("standalones/")]
            if "universal.apk" in apk_names:
                apk_names = ["universal.apk"]
            for n in apk_names:
                target = os.path.join(tmp, f"{len(bundle.apks):02d}_{os.path.basename(n)}")
                with zf.open(n) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                bundle.apks.append(target)
            for n in names:
                if n.startswith("Android/obb/") and not n.endswith("/"):
                    target = os.path.join(tmp, "obb", os.path.basename(n))
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with zf.open(n) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    bundle.obb.append((target, "/sdcard/" + n))
        if not bundle.apks:
            raise ApkError("Paket içinde APK bulunamadı.")
        base = next((a for a in bundle.apks if os.path.basename(a).split("_", 1)[-1] in ("base.apk", "base-master.apk")), bundle.apks[0])
        info = read_apk_info(base, aapt_path)
        bundle.package = manifest.get("package_name") or info.package
        bundle.version_name = info.version_name
        return bundle
    except Exception:
        bundle.cleanup()
        raise
