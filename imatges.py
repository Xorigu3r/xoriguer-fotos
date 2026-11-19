"""Càrrega ràpida d'imatges: miniatures en fils, memòria cau del visor i EXIF."""

import collections
import os
import re
import threading

from PyQt6.QtCore import QObject, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QImage, QImageReader

from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = 400_000_000

_QT = {bytes(f).decode().lower() for f in QImageReader.supportedImageFormats()}
_QT_EXT = {e for e in ("jpg", "jpeg", "jpe", "jfif", "png", "bmp", "gif", "webp", "tif", "tiff", "ico") if
           (e in _QT or {"jpe": "jpeg", "jfif": "jpeg", "tif": "tiff"}.get(e, "") in _QT)}
_PIL_EXT = {"tga", "psd", "pcx", "ppm", "pgm", "pbm", "dds", "jp2", "j2k"}
EXTENSIONS = _QT_EXT | _PIL_EXT


def es_imatge(nom):
    return os.path.splitext(nom)[1][1:].lower() in EXTENSIONS


def clau_natural(text):
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", text)]


# ---------------------------------------------------------------- conversions
def pil_a_qimage(im):
    if im.mode == "RGB":
        dades = im.tobytes("raw", "RGB")
        return QImage(dades, im.width, im.height, im.width * 3, QImage.Format.Format_RGB888).copy()
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    dades = im.tobytes("raw", "RGBA")
    return QImage(dades, im.width, im.height, im.width * 4, QImage.Format.Format_RGBA8888).copy()


def obre_pil(cami):
    """Obre amb Pillow, aplica l'orientació EXIF i normalitza el mode (RGB/RGBA)."""
    im = Image.open(cami)
    im.load()
    try:
        im = ImageOps.exif_transpose(im)
    except Exception:
        pass
    if im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
    elif im.mode != "RGB":
        im = im.convert("RGB")
    return im


def carrega_qimage(cami, costat_max=None):
    """Llegeix una imatge tan ràpid com es pugui. Amb costat_max, el JPEG es descodifica ja reduït."""
    lector = QImageReader(cami)
    lector.setAutoTransform(True)
    if costat_max:
        mida = lector.size()
        if mida.isValid() and max(mida.width(), mida.height()) > costat_max:
            lector.setScaledSize(mida.scaled(costat_max, costat_max, Qt.AspectRatioMode.KeepAspectRatio))
    img = lector.read()
    if not img.isNull():
        if costat_max and max(img.width(), img.height()) > costat_max * 1.05:
            img = img.scaled(costat_max, costat_max, Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
        return img
    try:  # formats que Qt no coneix (PSD, TGA...)
        with Image.open(cami) as im:
            if costat_max:
                im.draft("RGB", (costat_max, costat_max))
            im = ImageOps.exif_transpose(im)
            if costat_max:
                im.thumbnail((costat_max, costat_max), Image.Resampling.LANCZOS)
            return pil_a_qimage(im)
    except Exception:
        return QImage()


def mida_imatge(cami):
    lector = QImageReader(cami)
    lector.setAutoTransform(True)
    s = lector.size()
    if s.isValid():
        if lector.transformation().value & 4:  # Rotate90 dins la transformació EXIF
            s = QSize(s.height(), s.width())
        return s.width(), s.height()
    try:
        with Image.open(cami) as im:
            return im.size
    except Exception:
        return 0, 0


def info_exif(cami):
    """Retorna un dict amb les dades EXIF principals (claus fixes, valors en text)."""
    res = {}
    try:
        with Image.open(cami) as im:
            ex = im.getexif()
            ifd = ex.get_ifd(0x8769)
            marca = str(ex.get(271, "")).strip()
            model = str(ex.get(272, "")).strip()
            if model:
                res["camera"] = model if marca and marca.split()[0].lower() in model.lower() else f"{marca} {model}".strip()
            data = ifd.get(36867) or ex.get(306)
            if data:
                d = str(data)
                res["data"] = d[:10].replace(":", "-") + d[10:16] if len(d) >= 16 else d
            t = ifd.get(33434)
            if t:
                t = float(t)
                res["exposicio"] = f"1/{round(1 / t)} s" if 0 < t < 1 else f"{t:g} s"
            f = ifd.get(33437)
            if f:
                res["diafragma"] = f"f/{float(f):.1f}"
            iso = ifd.get(34855)
            if iso:
                res["iso"] = f"ISO {iso[0] if isinstance(iso, tuple) else iso}"
            fl = ifd.get(37386)
            if fl:
                res["focal"] = f"{float(fl):.0f} mm"
            lent = ifd.get(42036)
            if lent:
                res["objectiu"] = str(lent).strip()
            if marca:
                res["marca"] = marca
            if model:
                res["model"] = model
            sw = str(ex.get(305, "")).strip()
            if sw:
                res["software"] = sw
            prog = ifd.get(34850)
            if prog:
                res["programa"] = int(prog)
            bias = ifd.get(37380)
            if bias is not None:
                res["compensacio"] = f"{float(bias):+.1f} EV"
            fl = ifd.get(37385)
            if fl is not None:
                res["flash"] = bool(int(fl) & 1)
            f35 = ifd.get(41989)
            if f35:
                res["focal35"] = f"{int(f35)} mm"
            gps = ex.get_ifd(0x8825)
            if gps and 2 in gps and 4 in gps:
                def graus(v, ref):
                    d = float(v[0]) + float(v[1]) / 60 + float(v[2]) / 3600
                    return -d if str(ref).upper() in ("S", "W") else d
                res["gps"] = (graus(gps[2], gps.get(1, "N")), graus(gps[4], gps.get(3, "E")))
            res["dpi"] = im.info.get("dpi")
            res["format"] = im.format
    except Exception:
        pass
    return res


# ---------------------------------------------------------- miniatures (fils)
class CarregadorMiniatures(QObject):
    """Cua LIFO amb diversos fils: el que es demana l'últim (el que es veu) va primer."""
    feta = pyqtSignal(str, int, QImage)

    def __init__(self, fils=None):
        super().__init__()
        self._cua = collections.deque()
        self._pendents = set()
        self._cond = threading.Condition()
        self._viu = True
        fils = fils or max(2, min(6, (os.cpu_count() or 4) - 1))
        for _ in range(fils):
            threading.Thread(target=self._treballa, daemon=True).start()

    def demana(self, cami, costat):
        clau = (cami, costat)
        with self._cond:
            if clau in self._pendents:
                try:
                    self._cua.remove(clau)
                except ValueError:
                    return  # ja s'està fent
            self._pendents.add(clau)
            self._cua.append(clau)
            self._cond.notify()

    def buida(self):
        with self._cond:
            for clau in self._cua:
                self._pendents.discard(clau)
            self._cua.clear()

    def atura(self):
        with self._cond:
            self._viu = False
            self._cua.clear()
            self._cond.notify_all()

    def _treballa(self):
        while True:
            with self._cond:
                while self._viu and not self._cua:
                    self._cond.wait()
                if not self._viu:
                    return
                cami, costat = self._cua.pop()
            try:
                img = carrega_qimage(cami, costat)
            except Exception:
                img = QImage()
            with self._cond:
                self._pendents.discard((cami, costat))
            if self._viu:
                self.feta.emit(cami, costat, img)


# ------------------------------------------------------- memòria cau del visor
class MemoriaVisor(QObject):
    """Guarda les imatges senceres ja descodificades i precarrega les veïnes en segon pla."""
    llesta = pyqtSignal(str)

    def __init__(self, limit_mb=900):
        super().__init__()
        self._cau = collections.OrderedDict()   # cami -> (mtime, QImage)
        self._limit = limit_mb * 1024 * 1024
        self._bloc = threading.Lock()
        self._cua = []
        self._cond = threading.Condition()
        self._viu = True
        self._fent = None
        for _ in range(2):
            threading.Thread(target=self._treballa, daemon=True).start()

    @staticmethod
    def _mtime(cami):
        try:
            return os.path.getmtime(cami)
        except OSError:
            return 0

    def obte(self, cami):
        with self._bloc:
            e = self._cau.get(cami)
            if e and e[0] == self._mtime(cami):
                self._cau.move_to_end(cami)
                return e[1]
        return None

    def carrega(self, cami):
        img = self.obte(cami)
        if img is None:
            img = carrega_qimage(cami)
            self._desa(cami, img)
        return img

    def oblida(self, cami):
        with self._bloc:
            self._cau.pop(cami, None)

    def _desa(self, cami, img):
        if img.isNull():
            return
        with self._bloc:
            self._cau[cami] = (self._mtime(cami), img)
            self._cau.move_to_end(cami)
            total = sum(i.sizeInBytes() for _, i in self._cau.values())
            while total > self._limit and len(self._cau) > 1:
                _, (_, vella) = self._cau.popitem(last=False)
                total -= vella.sizeInBytes()

    def precarrega(self, camins):
        with self._cond:
            self._cua = [c for c in camins if self.obte(c) is None]
            self._cond.notify_all()

    def atura(self):
        with self._cond:
            self._viu = False
            self._cond.notify_all()

    def _treballa(self):
        while True:
            with self._cond:
                while self._viu and not self._cua:
                    self._cond.wait()
                if not self._viu:
                    return
                cami = self._cua.pop(0)
            if self.obte(cami) is None:
                try:
                    img = carrega_qimage(cami)
                    self._desa(cami, img)
                    self.llesta.emit(cami)
                except Exception:
                    pass
