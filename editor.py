"""Editor de fotos: girar, voltejar, retallar, canviar la mida, ajustos de color i efectes."""

import os
import tempfile

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from PyQt6.QtCore import QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QGridLayout,
                             QGroupBox, QHBoxLayout, QLabel, QMessageBox, QPushButton, QScrollArea, QSlider, QSpinBox,
                             QVBoxLayout, QWidget)

import config
import estil as E
import imatges as IM
from i18n import t
from visor import Llenc

FORMATS_DESA = {"jpg": "JPEG", "jpeg": "JPEG", "jpe": "JPEG", "jfif": "JPEG", "png": "PNG", "bmp": "BMP",
                "webp": "WEBP", "tif": "TIFF", "tiff": "TIFF", "gif": "GIF", "ico": "ICO", "tga": "TGA"}


# ------------------------------------------------------------- operacions
def _per_canals(im, f):
    """Aplica f a la part RGB i conserva el canal alfa."""
    if im.mode == "RGBA":
        rgb, a = im.convert("RGB"), im.getchannel("A")
        out = f(rgb).convert("RGB")
        out.putalpha(a)
        return out
    return f(im)


def aplica_ajustos(im, v):
    def f(x):
        if v["brillantor"]:
            x = ImageEnhance.Brightness(x).enhance(1 + v["brillantor"] / 100)
        if v["contrast"]:
            x = ImageEnhance.Contrast(x).enhance(1 + v["contrast"] / 100)
        if v["saturacio"]:
            x = ImageEnhance.Color(x).enhance(1 + v["saturacio"] / 100)
        if v["gamma"]:
            g = 2 ** (v["gamma"] / 50)            # -100..100 -> 0.25..4
            lut = [min(255, round(255 * (i / 255) ** (1 / g))) for i in range(256)]
            x = x.point(lut * 3)
        if v["temperatura"]:
            k = v["temperatura"] / 100 * 0.25
            r = [min(255, round(i * (1 + k))) for i in range(256)]
            b = [min(255, round(i * (1 - k))) for i in range(256)]
            x = x.point(r + list(range(256)) + b)
        if v["nitidesa"]:
            x = ImageEnhance.Sharpness(x).enhance(1 + v["nitidesa"] / 40)
        return x
    return _per_canals(im, f)


def sepia(x):
    g = ImageOps.grayscale(x)
    return ImageOps.colorize(g, "#2a1a0a", "#f4e4c4", mid="#a8805a")


EFECTES = {
    "auto": lambda im: _per_canals(im, lambda x: ImageOps.autocontrast(x, cutoff=0.5)),
    "equalitza": lambda im: _per_canals(im, ImageOps.equalize),
    "bn": lambda im: _per_canals(im, lambda x: ImageOps.grayscale(x).convert("RGB")),
    "sepia": lambda im: _per_canals(im, sepia),
    "negatiu": lambda im: _per_canals(im, ImageOps.invert),
    "enfoca": lambda im: _per_canals(im, lambda x: x.filter(ImageFilter.UnsharpMask(2, 80, 2))),
    "difumina": lambda im: _per_canals(im, lambda x: x.filter(ImageFilter.GaussianBlur(2))),
    "vinyeta": lambda im: _per_canals(im, vinyeta),
}


def vinyeta(x):
    w, h = x.size
    m = Image.radial_gradient("L").resize((w, h))          # 0 al centre, 255 a fora
    m = m.point(lambda i: max(0, min(255, int((i - 110) * 1.6))))
    fosc = Image.new("RGB", (w, h), (0, 0, 0))
    return Image.composite(fosc, x, m.point(lambda i: int(i * 0.75)))


def _exif_net(im_original):
    try:
        ex = im_original.getexif()
        if ex:
            ex[274] = 1   # orientació: ja està aplicada als píxels
            return ex.tobytes()
    except Exception:
        pass
    return None


def desa(im, cami, qualitat=92, original=None):
    """Desa de manera segura (fitxer temporal + reemplaçament) conservant l'EXIF i el perfil de color."""
    ext = os.path.splitext(cami)[1][1:].lower()
    fmt = FORMATS_DESA.get(ext, "PNG")
    kw = {}
    exif = info_icc = None
    if original and os.path.exists(original):
        try:
            with Image.open(original) as o:
                exif = _exif_net(o)
                info_icc = o.info.get("icc_profile")
        except Exception:
            pass
    out = im
    if fmt in ("JPEG", "BMP") and out.mode != "RGB":
        fons = Image.new("RGB", out.size, (255, 255, 255))
        if out.mode == "RGBA":
            fons.paste(out, mask=out.getchannel("A"))
            out = fons
        else:
            out = out.convert("RGB")
    if fmt == "JPEG":
        kw.update(quality=int(qualitat), optimize=True, subsampling=0 if qualitat >= 90 else 2)
    elif fmt == "WEBP":
        kw.update(quality=int(qualitat), method=4)
    elif fmt == "PNG":
        kw.update(compress_level=6)
    elif fmt == "TIFF":
        kw.update(compression="tiff_lzw")
    if exif and fmt in ("JPEG", "WEBP", "PNG", "TIFF"):
        kw["exif"] = exif
    if info_icc and fmt in ("JPEG", "WEBP", "PNG", "TIFF"):
        kw["icc_profile"] = info_icc
    carpeta = os.path.dirname(os.path.abspath(cami))
    fd, tmp = tempfile.mkstemp(suffix="." + ext, dir=carpeta)
    os.close(fd)
    try:
        out.save(tmp, fmt, **kw)
        os.replace(tmp, cami)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def desa_girada(cami, graus, qualitat=92):
    """JPEG: sense pèrdua (només canvia l'orientació EXIF). Altres formats: es tornen a desar."""
    import orientacio
    if orientacio.es_jpeg(cami) and config.get("gir_sense_perdua") is not False:
        orientacio.aplica(cami, [{90: "cw", -90: "ccw", 180: "180", -180: "180"}[graus]])
        return
    im = IM.obre_pil(cami)
    im = im.rotate(-graus, expand=True)
    desa(im, cami, qualitat, original=cami)


# ------------------------------------------------------------ diàlegs
class DialegMida(QDialog):
    def __init__(self, w, h, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("ed_mida"))
        self.w0, self.h0 = w, h
        f = QFormLayout(self)
        self.sw = QSpinBox(maximum=60000, minimum=1, value=w, suffix=" px")
        self.sh = QSpinBox(maximum=60000, minimum=1, value=h, suffix=" px")
        self.sp = QSpinBox(maximum=1000, minimum=1, value=100, suffix=" %")
        self.prop = QCheckBox(t("ed_mantén_proporcio"), checked=True)
        f.addRow(QLabel(t("ed_actual", w=w, h=h), objectName="suau"))
        f.addRow(t("ed_amplada"), self.sw)
        f.addRow(t("ed_alcada"), self.sh)
        f.addRow(t("ed_percentatge"), self.sp)
        f.addRow(self.prop)
        self._bloc = False
        self.sw.valueChanged.connect(lambda v: self._canvi("w", v))
        self.sh.valueChanged.connect(lambda v: self._canvi("h", v))
        self.sp.valueChanged.connect(lambda v: self._canvi("p", v))
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setObjectName("primari")
        bb.button(QDialogButtonBox.StandardButton.Cancel).setText(t("cancel·la"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)

    def _canvi(self, quin, v):
        if self._bloc:
            return
        self._bloc = True
        if quin == "p":
            self.sw.setValue(max(1, round(self.w0 * v / 100)))
            self.sh.setValue(max(1, round(self.h0 * v / 100)))
        elif self.prop.isChecked():
            if quin == "w":
                self.sh.setValue(max(1, round(v * self.h0 / self.w0)))
            else:
                self.sw.setValue(max(1, round(v * self.w0 / self.h0)))
            self.sp.setValue(max(1, round(self.sw.value() / self.w0 * 100)))
        self._bloc = False

    def valors(self):
        return self.sw.value(), self.sh.value()


class DialegQualitat(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("ed_qualitat"))
        lay = QVBoxLayout(self)
        fila = QHBoxLayout()
        self.sl = QSlider(Qt.Orientation.Horizontal, minimum=30, maximum=100, value=config.get("qualitat_jpeg"))
        self.lbl = QLabel(str(self.sl.value()))
        self.sl.valueChanged.connect(lambda v: self.lbl.setText(str(v)))
        fila.addWidget(self.sl)
        fila.addWidget(self.lbl)
        lay.addWidget(QLabel(t("ed_qualitat_txt")))
        lay.addLayout(fila)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Cancel).setText(t("cancel·la"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.resize(360, 120)


# ------------------------------------------------------------ finestra
class Editor(QWidget):
    desat = pyqtSignal(str)

    AJUSTOS = [("brillantor", -100, 100), ("contrast", -100, 100), ("saturacio", -100, 100),
               ("gamma", -100, 100), ("temperatura", -100, 100), ("nitidesa", 0, 100)]

    def __init__(self, cami, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setObjectName("fons")
        self.setWindowIcon(E.icona_app())
        self.cami = cami
        self.im = IM.obre_pil(cami)
        self.desfer, self.refer = [], []
        self.modificat = False
        self.proxy = None
        self._en_ajust = False

        self.llenc = Llenc(self, roda_navega=False)
        self.llenc.retall_canviat.connect(self._retall_canviat)
        self.llenc.zoom_canviat.connect(lambda z: self._estat())

        # ---- panell lateral
        panell = QWidget()
        pl = QVBoxLayout(panell)
        pl.setContentsMargins(6, 6, 6, 6)

        g = QGroupBox(t("ed_transforma"))
        gl = QGridLayout(g)
        for i, (txt, ic, mir, f) in enumerate([
            (t("ed_gira_e"), "gira", True, lambda: self.op(lambda im: im.rotate(90, expand=True))),
            (t("ed_gira_d"), "gira", False, lambda: self.op(lambda im: im.rotate(-90, expand=True))),
            (t("ed_volteja_h"), "volteja", False, lambda: self.op(ImageOps.mirror)),
            (t("ed_volteja_v"), "volteja", False, lambda: self.op(ImageOps.flip)),
        ]):
            b = QPushButton(E.icona(ic, mirall=mir, mida=16), txt)
            b.clicked.connect(f)
            gl.addWidget(b, i // 2, i % 2)
        b = QPushButton(E.icona("mida", mida=16), t("ed_mida") + "…")
        b.clicked.connect(self.canvia_mida)
        gl.addWidget(b, 2, 0, 1, 2)
        pl.addWidget(g)

        g = QGroupBox(t("ed_retalla"))
        gl = QVBoxLayout(g)
        fila = QHBoxLayout()
        self.b_retall = QPushButton(E.icona("retalla", mida=16), t("ed_selecciona"), checkable=True)
        self.b_retall.toggled.connect(self._mode_retall)
        self.c_prop = QComboBox()
        self.c_prop.addItems([t("ed_lliure"), "1:1", "4:3", "3:2", "16:9", "3:4", "2:3", "9:16"])
        self.c_prop.currentIndexChanged.connect(self._proporcio)
        fila.addWidget(self.b_retall)
        fila.addWidget(self.c_prop)
        gl.addLayout(fila)
        self.b_aplica_retall = QPushButton(t("ed_aplica_retall"), objectName="primari", enabled=False)
        self.b_aplica_retall.clicked.connect(self.aplica_retall)
        gl.addWidget(self.b_aplica_retall)
        pl.addWidget(g)

        g = QGroupBox(t("ed_ajustos"))
        gl = QGridLayout(g)
        self.sliders = {}
        for i, (clau, mn, mx) in enumerate(self.AJUSTOS):
            lbl = QLabel(t("aj_" + clau))
            s = QSlider(Qt.Orientation.Horizontal, minimum=mn, maximum=mx, value=0)
            val = QLabel("0", minimumWidth=30, alignment=Qt.AlignmentFlag.AlignRight)
            s.valueChanged.connect(lambda v, l=val: (l.setText(str(v)), self._ajust_canviat()))
            s.setPageStep(10)
            gl.addWidget(lbl, i, 0)
            gl.addWidget(s, i, 1)
            gl.addWidget(val, i, 2)
            self.sliders[clau] = s
        fila = QHBoxLayout()
        self.b_aplica_aj = QPushButton(t("ed_aplica"), objectName="primari", enabled=False)
        self.b_aplica_aj.clicked.connect(self.aplica_ajustos)
        self.b_reset_aj = QPushButton(t("ed_restableix"), enabled=False)
        self.b_reset_aj.clicked.connect(self.restableix_ajustos)
        fila.addWidget(self.b_reset_aj)
        fila.addWidget(self.b_aplica_aj)
        gl.addLayout(fila, len(self.AJUSTOS), 0, 1, 3)
        pl.addWidget(g)

        g = QGroupBox(t("ed_efectes"))
        gl = QGridLayout(g)
        for i, clau in enumerate(EFECTES):
            b = QPushButton(t("ef_" + clau))
            b.clicked.connect(lambda _, c=clau: self.op(EFECTES[c]))
            gl.addWidget(b, i // 2, i % 2)
        n = len(EFECTES)
        import eines_foto as EF
        for i, (txt, f) in enumerate([(t("ef_nivells") + "…", lambda: self._dialeg(EF.DialegNivells)),
                                      (t("ef_corbes") + "…", lambda: self._dialeg(EF.DialegCorbes)),
                                      (t("ef_text") + "…", lambda: self._dialeg(EF.DialegText)),
                                      (t("ef_ulls"), self.ulls_vermells)]):
            b = QPushButton(txt)
            b.clicked.connect(f)
            gl.addWidget(b, (n + i) // 2, (n + i) % 2)
        pl.addWidget(g)
        pl.addStretch()

        sc = QScrollArea()
        sc.setWidget(panell)
        sc.setWidgetResizable(True)
        sc.setFixedWidth(330)
        sc.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # ---- barra inferior
        barra = QHBoxLayout()
        self.b_desfes = QPushButton(E.icona("desfes", mida=16), t("ed_desfes"), enabled=False)
        self.b_desfes.clicked.connect(self.desfes)
        self.b_refes = QPushButton(E.icona("refes", mida=16), t("ed_refes"), enabled=False)
        self.b_refes.clicked.connect(self.refes)
        b_aj = QPushButton(E.icona("ajusta", mida=16), t("v_ajusta"))
        b_aj.clicked.connect(self.llenc.posa_ajusta)
        b_100 = QPushButton("1:1")
        b_100.clicked.connect(lambda: self.llenc.posa_zoom(1.0))
        self.lbl_estat = QLabel(objectName="suau")
        b_desa = QPushButton(E.icona("desa", color=E.BG_B, mida=16), t("ed_desa"), objectName="primari")
        b_desa.clicked.connect(self.desa)
        b_desacom = QPushButton(E.icona("desacom", mida=16), t("ed_desa_com") + "…")
        b_desacom.clicked.connect(self.desa_com)
        b_tanca = QPushButton(t("v_tanca"))
        b_tanca.clicked.connect(self.close)
        for w in (self.b_desfes, self.b_refes, b_aj, b_100):
            barra.addWidget(w)
        barra.addWidget(self.lbl_estat, 1)
        for w in (b_desacom, b_desa, b_tanca):
            barra.addWidget(w)

        dalt = QHBoxLayout()
        dalt.addWidget(self.llenc, 1)
        dalt.addWidget(sc)
        lay = QVBoxLayout(self)
        lay.addLayout(dalt, 1)
        lay.addLayout(barra)

        for tecla, f in {"Ctrl+Z": self.desfes, "Ctrl+Y": self.refes, "Ctrl+Shift+Z": self.refes,
                         "Ctrl+S": self.desa, "Ctrl+Shift+S": self.desa_com, "Esc": self._esc,
                         "Return": self._intro, "Enter": self._intro,
                         "+": lambda: self.llenc.zoom_pas(1), "-": lambda: self.llenc.zoom_pas(-1),
                         "F": self.llenc.posa_ajusta, "1": lambda: self.llenc.posa_zoom(1.0)}.items():
            QShortcut(QKeySequence(tecla), self, activated=f)

        self._temps_aj = QTimer(self, singleShot=True, timeout=self._previsualitza)
        self._mostra()
        self.resize(1300, 850)

    # ----------------------------------------------------------- estat
    def _titol(self):
        self.setWindowTitle(("• " if self.modificat else "") + os.path.basename(self.cami) + " — " +
                            t("ed_titol") + " — Xoriguer Fotos")

    def _estat(self):
        self.lbl_estat.setText(f"   {self.im.width} × {self.im.height} px    {round(self.llenc.z * 100)}%")

    def _mostra(self, conserva=False):
        self.llenc.posa_imatge(IM.pil_a_qimage(self.im), conserva_vista=conserva)
        self.b_desfes.setEnabled(bool(self.desfer))
        self.b_refes.setEnabled(bool(self.refer))
        self._titol()
        self._estat()

    def op(self, funcio):
        self._confirma_ajustos()
        self._surt_retall()
        try:
            QApplication_setOverride(True)
            nova = funcio(self.im)
        except Exception as e:
            QMessageBox.warning(self, "Xoriguer Fotos", str(e))
            return
        finally:
            QApplication_setOverride(False)
        self.desfer.append(self.im)
        del self.desfer[:-15]
        self.refer.clear()
        mida_igual = nova.size == self.im.size
        self.im = nova
        self.modificat = True
        self._mostra(conserva=mida_igual)

    def desfes(self):
        self._descarta_ajustos()
        if self.desfer:
            self.refer.append(self.im)
            self.im = self.desfer.pop()
            self.modificat = True
            self._mostra()

    def refes(self):
        self._descarta_ajustos()
        if self.refer:
            self.desfer.append(self.im)
            self.im = self.refer.pop()
            self.modificat = True
            self._mostra()

    # ---------------------------------------------------------- retall
    def _mode_retall(self, actiu):
        if actiu:
            self._confirma_ajustos()
        self.llenc.posa_mode_retall(actiu)
        self._proporcio()

    def _surt_retall(self):
        if self.b_retall.isChecked():
            self.b_retall.setChecked(False)

    def _proporcio(self):
        txt = self.c_prop.currentText()
        if ":" in txt:
            a, b = txt.split(":")
            self.llenc.proporcio = int(a) / int(b)
        else:
            self.llenc.proporcio = None

    def _retall_canviat(self, r):
        self.b_aplica_retall.setEnabled(not r.isNull() and r.width() >= 2)

    def aplica_retall(self):
        r = self.llenc.retall
        if r.isNull():
            return
        caixa = (int(round(r.left())), int(round(r.top())), int(round(r.right())), int(round(r.bottom())))
        self.op(lambda im: im.crop(caixa))

    # --------------------------------------------------------- ajustos
    def _valors(self):
        return {k: s.value() for k, s in self.sliders.items()}

    def _ajust_canviat(self):
        if self._en_ajust:
            return
        actiu = any(self._valors().values())
        self.b_aplica_aj.setEnabled(actiu)
        self.b_reset_aj.setEnabled(actiu)
        if self.proxy is None:
            self.proxy = self.im.copy()
            costat = max(800, max(self.llenc.width(), self.llenc.height()))
            if max(self.proxy.size) > costat:
                self.proxy.thumbnail((costat, costat), Image.Resampling.BILINEAR)
        self._temps_aj.start(25)

    def _previsualitza(self):
        if self.proxy is None:
            return
        prev = aplica_ajustos(self.proxy, self._valors())
        self.llenc.posa_imatge(IM.pil_a_qimage(prev))

    def aplica_ajustos(self):
        v = self._valors()
        if not any(v.values()):
            return
        self._reset_sliders()
        self.proxy = None
        self.op(lambda im: aplica_ajustos(im, v))

    def _confirma_ajustos(self):
        if self.proxy is not None and any(self._valors().values()):
            v = self._valors()
            self._reset_sliders()
            self.proxy = None
            self.desfer.append(self.im)
            self.refer.clear()
            self.im = aplica_ajustos(self.im, v)
            self.modificat = True
            self._mostra()
        self.proxy = None

    def _descarta_ajustos(self):
        if self.proxy is not None:
            self._reset_sliders()
            self.proxy = None
            self._mostra()

    def restableix_ajustos(self):
        self._descarta_ajustos()

    def _reset_sliders(self):
        self._en_ajust = True
        for s in self.sliders.values():
            s.setValue(0)
        self._en_ajust = False
        self.b_aplica_aj.setEnabled(False)
        self.b_reset_aj.setEnabled(False)

    # ------------------------------------------------- eines avançades
    def _dialeg(self, classe):
        import eines_foto as EF
        self._confirma_ajustos()
        self._surt_retall()
        f = EF.amb_previsualitzacio(self, self.llenc, self.im, classe)
        if f:
            self.op(f)

    def ulls_vermells(self):
        import eines_foto as EF
        r = self.llenc.retall if self.b_retall.isChecked() else None
        if r is None or r.isNull():
            QMessageBox.information(self, "Xoriguer Fotos", t("ed_ulls_primer"))
            self.b_retall.setChecked(True)
            self.c_prop.setCurrentIndex(0)
            return
        caixa = (int(round(r.left())), int(round(r.top())), int(round(r.right())), int(round(r.bottom())))
        self.op(lambda im: EF.ulls_vermells(im, caixa))

    # ------------------------------------------------------ redimensiona
    def canvia_mida(self):
        self._confirma_ajustos()
        d = DialegMida(self.im.width, self.im.height, self)
        if d.exec():
            w, h = d.valors()
            if (w, h) != self.im.size:
                self.op(lambda im: im.resize((w, h), Image.Resampling.LANCZOS))

    # ------------------------------------------------------------ desar
    def desa(self):
        self._confirma_ajustos()
        if not self.modificat:
            return True
        if IM.extensio(self.cami) in IM.NOMES_LECTURA or IM.extensio(self.cami) not in FORMATS_DESA:
            QMessageBox.information(self, "Xoriguer Fotos", t("e_nomes_lectura"))
            self.desa_com()
            return not self.modificat
        return self._desa_a(self.cami)

    def _desa_a(self, cami):
        ext = os.path.splitext(cami)[1][1:].lower()
        qualitat = config.get("qualitat_jpeg")
        if FORMATS_DESA.get(ext) in ("JPEG", "WEBP"):
            d = DialegQualitat(self)
            if not d.exec():
                return False
            qualitat = d.sl.value()
            config.set("qualitat_jpeg", qualitat)
        try:
            QApplication_setOverride(True)
            desa(self.im, cami, qualitat, original=self.cami)
        except Exception as e:
            QMessageBox.warning(self, "Xoriguer Fotos", t("e_no_desat") + f"\n{e}")
            return False
        finally:
            QApplication_setOverride(False)
        self.modificat = False
        self.cami = cami
        self._titol()
        self.desat.emit(cami)
        return True

    def desa_com(self):
        self._confirma_ajustos()
        base, ext = os.path.splitext(self.cami)
        filtre = "JPEG (*.jpg);;PNG (*.png);;WebP (*.webp);;BMP (*.bmp);;TIFF (*.tif)"
        sel = {"jpg": "JPEG (*.jpg)", "jpeg": "JPEG (*.jpg)", "png": "PNG (*.png)", "webp": "WebP (*.webp)",
               "bmp": "BMP (*.bmp)", "tif": "TIFF (*.tif)", "tiff": "TIFF (*.tif)"}.get(ext[1:].lower(), "JPEG (*.jpg)")
        cami, filt = QFileDialog.getSaveFileName(self, t("ed_desa_com"), base + "_edit" + ext, filtre, sel)
        if not cami:
            return
        if not os.path.splitext(cami)[1]:
            cami += "." + filt.split("*.")[1].rstrip(")")
        self._desa_a(cami)

    def _esc(self):
        if self.b_retall.isChecked():
            self.b_retall.setChecked(False)
        elif self.proxy is not None:
            self._descarta_ajustos()
        else:
            self.close()

    def _intro(self):
        if self.b_retall.isChecked() and self.b_aplica_retall.isEnabled():
            self.aplica_retall()
        elif self.proxy is not None:
            self.aplica_ajustos()

    def closeEvent(self, ev):
        if self.proxy is not None and any(self._valors().values()):
            self._confirma_ajustos()
        if self.modificat:
            r = QMessageBox.question(self, "Xoriguer Fotos", t("p_desa_canvis"),
                                     QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                                     QMessageBox.StandardButton.Cancel)
            if r == QMessageBox.StandardButton.Cancel or (r == QMessageBox.StandardButton.Save and not self.desa()):
                ev.ignore()
                return
        super().closeEvent(ev)


def QApplication_setOverride(on):
    from PyQt6.QtWidgets import QApplication
    if on:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    else:
        QApplication.restoreOverrideCursor()
