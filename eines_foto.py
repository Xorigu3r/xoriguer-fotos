"""Eines d'edició avançades: ulls vermells, text i marca d'aigua, nivells i corbes (amb previsualització)."""

import os

from PIL import Image

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFontComboBox,
                             QFormLayout, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSlider, QSpinBox,
                             QVBoxLayout, QWidget)

import config
import estil as E
import imatges as IM
from i18n import t


# ================================================================ ulls vermells
def ulls_vermells(im, caixa):
    """Treu el vermell de les pupil·les dins de la caixa (x0, y0, x1, y1)."""
    im = im.copy()
    zona = im.crop(caixa).convert("RGBA" if im.mode == "RGBA" else "RGB")
    canals = zona.split()
    r, g, b = canals[:3]
    pr, pg, pb = r.load(), g.load(), b.load()
    w, h = zona.size
    cx, cy = w / 2, h / 2
    for y in range(h):
        for x in range(w):
            vr, vg, vb = pr[x, y], pg[x, y], pb[x, y]
            mig = (vg + vb) / 2
            if vr > 60 and vr > mig * 1.6:
                # suavitzat a la vora de l'el·lipse perquè no quedi una taca
                d = ((x - cx) / max(cx, 1)) ** 2 + ((y - cy) / max(cy, 1)) ** 2
                if d <= 1.2:
                    pr[x, y] = int(mig * 0.9)
    zona = Image.merge(zona.mode, (r, g, b) + tuple(canals[3:]))
    im.paste(zona, caixa[:2])
    return im


# ================================================================== base
class DialegPrevi(QDialog):
    """Diàleg amb previsualització: crida en_canvi(funcio) cada cop que es toca un control."""

    def __init__(self, parent, titol, en_canvi):
        super().__init__(parent)
        self.setWindowTitle(titol)
        self.en_canvi = en_canvi
        self._temps = QTimer(self, singleShot=True, timeout=lambda: self.en_canvi(self.funcio()))
        self.cos = QVBoxLayout(self)

    def canvi(self, *_):
        self._temps.start(40)

    def botons(self, extra=None):
        fila = QHBoxLayout()
        for b in extra or []:
            fila.addWidget(b)
        fila.addStretch()
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText(t("ed_aplica"))
        bb.button(QDialogButtonBox.StandardButton.Ok).setObjectName("primari")
        bb.button(QDialogButtonBox.StandardButton.Cancel).setText(t("cancel·la"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        fila.addWidget(bb)
        self.cos.addLayout(fila)

    def funcio(self):
        raise NotImplementedError


def _lut_rgb(im, luts):
    """luts = (r, g, b) de 256 valors; conserva l'alfa."""
    pla = list(luts[0]) + list(luts[1]) + list(luts[2])
    if im.mode == "RGBA":
        a = im.getchannel("A")
        out = im.convert("RGB").point(pla)
        out.putalpha(a)
        return out
    return im.convert("RGB").point(pla)


# ================================================================== nivells
class DialegNivells(DialegPrevi):
    def __init__(self, parent, base, en_canvi):
        super().__init__(parent, t("ef_nivells"), en_canvi)
        self.base = base
        from panells import Histograma
        self.hist = Histograma()
        self.hist.setMinimumSize(380, 130)
        self.hist.posa_imatge(IM.pil_a_qimage(base))
        self.cos.addWidget(self.hist)
        f = QFormLayout()
        self.c_canal = QComboBox()
        self.c_canal.addItems(["RGB", t("cv_vermell"), t("cv_verd"), t("cv_blau")])
        self.c_canal.currentIndexChanged.connect(self._canvi_canal)
        f.addRow(t("cv_canal"), self.c_canal)
        self.vals = {c: [0, 255, 100, 0, 255] for c in range(4)}   # negre, blanc, gamma*100, sortida negre, blanc
        self.s = []
        self.etiq = []
        for nom, mn, mx in (("nv_negre", 0, 254), ("nv_blanc", 1, 255), ("nv_gamma", 10, 500),
                            ("nv_sort_negre", 0, 255), ("nv_sort_blanc", 0, 255)):
            fila = QHBoxLayout()
            sl = QSlider(Qt.Orientation.Horizontal, minimum=mn, maximum=mx)
            lbl = QLabel(minimumWidth=40, alignment=Qt.AlignmentFlag.AlignRight)
            sl.valueChanged.connect(lambda v, l=lbl, n=nom: (l.setText(f"{v / 100:.2f}" if n == "nv_gamma" else str(v)),
                                                             self._desa_canal(), self.canvi()))
            fila.addWidget(sl)
            fila.addWidget(lbl)
            f.addRow(t(nom), fila)
            self.s.append(sl)
            self.etiq.append((lbl, nom))
        self.cos.addLayout(f)
        b_auto = QPushButton(t("ef_auto"))
        b_auto.clicked.connect(self._auto)
        b_reset = QPushButton(t("ed_restableix"))
        b_reset.clicked.connect(self._reset)
        self.botons([b_auto, b_reset])
        self._carregant = False
        self._canvi_canal()

    def _canvi_canal(self):
        self._carregant = True
        for sl, v, (lbl, nom) in zip(self.s, self.vals[self.c_canal.currentIndex()], self.etiq):
            sl.setValue(v)
            lbl.setText(f"{v / 100:.2f}" if nom == "nv_gamma" else str(v))
        self._carregant = False

    def _desa_canal(self):
        if not self._carregant:
            self.vals[self.c_canal.currentIndex()] = [sl.value() for sl in self.s]

    def _auto(self):
        h = self.base.convert("L").histogram()
        total = sum(h)
        acc, negre = 0, 0
        for i, v in enumerate(h):
            acc += v
            if acc > total * 0.005:
                negre = i
                break
        acc, blanc = 0, 255
        for i in range(255, -1, -1):
            acc += h[i]
            if acc > total * 0.005:
                blanc = i
                break
        self.c_canal.setCurrentIndex(0)
        self.vals[0] = [negre, max(blanc, negre + 1), 100, 0, 255]
        self._canvi_canal()
        self.canvi()

    def _reset(self):
        self.vals = {c: [0, 255, 100, 0, 255] for c in range(4)}
        self._canvi_canal()
        self.canvi()

    @staticmethod
    def _lut(v):
        ib, iw, g, ob, ow = v
        g = g / 100
        iw = max(iw, ib + 1)
        res = []
        for x in range(256):
            u = min(1.0, max(0.0, (x - ib) / (iw - ib)))
            res.append(int(round(ob + (u ** (1 / g)) * (ow - ob))))
        return res

    def funcio(self):
        tots = self._lut(self.vals[0])
        luts = [[self._lut(self.vals[k])[tots[x]] for x in range(256)] for k in (1, 2, 3)]
        return lambda im: _lut_rgb(im, luts)


# =================================================================== corbes
def _monotona(punts):
    """Interpolació cúbica monòtona (Fritsch-Carlson) -> taula de 256 valors."""
    punts = sorted(punts)
    xs = [p[0] for p in punts]
    ys = [p[1] for p in punts]
    n = len(punts)
    if n == 2:
        return [int(round(min(255, max(0, ys[0] + (ys[1] - ys[0]) * (x - xs[0]) / max(1, xs[1] - xs[0])))))
                if xs[0] <= x <= xs[1] else (ys[0] if x < xs[0] else ys[1]) for x in range(256)]
    d = [(ys[i + 1] - ys[i]) / max(1e-9, xs[i + 1] - xs[i]) for i in range(n - 1)]
    m = [d[0]] + [(d[i - 1] + d[i]) / 2 if d[i - 1] * d[i] > 0 else 0 for i in range(1, n - 1)] + [d[-1]]
    for i in range(n - 1):
        if d[i] == 0:
            m[i] = m[i + 1] = 0
        else:
            a, b = m[i] / d[i], m[i + 1] / d[i]
            s = a * a + b * b
            if s > 9:
                k = 3 / s ** 0.5
                m[i], m[i + 1] = k * a * d[i], k * b * d[i]
    res = []
    for x in range(256):
        if x <= xs[0]:
            res.append(ys[0])
            continue
        if x >= xs[-1]:
            res.append(ys[-1])
            continue
        i = max(k for k in range(n - 1) if xs[k] <= x)
        h = xs[i + 1] - xs[i]
        tt = (x - xs[i]) / h
        h00, h10 = 2 * tt ** 3 - 3 * tt ** 2 + 1, tt ** 3 - 2 * tt ** 2 + tt
        h01, h11 = -2 * tt ** 3 + 3 * tt ** 2, tt ** 3 - tt ** 2
        res.append(h00 * ys[i] + h10 * h * m[i] + h01 * ys[i + 1] + h11 * h * m[i + 1])
    return [int(round(min(255, max(0, v)))) for v in res]


class EditorCorba(QWidget):
    """Gràfic de la corba: clic per afegir un punt, arrossegar per moure'l, botó dret per treure'l."""

    def __init__(self, en_canvi, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 300)
        self.en_canvi = en_canvi
        self.punts = [(0, 0), (255, 255)]
        self.color = QColor(E.CREAM)
        self._mou = None
        self.hist = None

    def _a_pantalla(self, p):
        r = self.rect().adjusted(8, 8, -8, -8)
        return QPointF(r.left() + p[0] / 255 * r.width(), r.bottom() - p[1] / 255 * r.height())

    def _a_valor(self, pos):
        r = self.rect().adjusted(8, 8, -8, -8)
        x = round((pos.x() - r.left()) / r.width() * 255)
        y = round((r.bottom() - pos.y()) / r.height() * 255)
        return min(255, max(0, x)), min(255, max(0, y))

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect().adjusted(8, 8, -8, -8))
        p.fillRect(r, QColor(E.BG_B))
        if self.hist:
            mx = max(self.hist[2:254]) or 1
            cami = QPainterPath(QPointF(r.left(), r.bottom()))
            for x in range(256):
                cami.lineTo(r.left() + x / 255 * r.width(), r.bottom() - min(1, self.hist[x] / mx) * r.height() * 0.9)
            cami.lineTo(r.right(), r.bottom())
            p.fillPath(cami, QColor(65, 80, 106, 160))
        p.setPen(QPen(QColor(E.LINE), 1, Qt.PenStyle.DashLine))
        for i in (1, 2, 3):
            p.drawLine(QPointF(r.left() + r.width() * i / 4, r.top()), QPointF(r.left() + r.width() * i / 4, r.bottom()))
            p.drawLine(QPointF(r.left(), r.top() + r.height() * i / 4), QPointF(r.right(), r.top() + r.height() * i / 4))
        p.drawLine(r.bottomLeft(), r.topRight())
        lut = _monotona(self.punts)
        cami = QPainterPath(self._a_pantalla((0, lut[0])))
        for x in range(1, 256):
            cami.lineTo(self._a_pantalla((x, lut[x])))
        p.setPen(QPen(self.color, 2))
        p.drawPath(cami)
        p.setBrush(QColor(E.OR1))
        p.setPen(QPen(QColor(E.BG_B), 1))
        for pt in self.punts:
            p.drawEllipse(self._a_pantalla(pt), 5, 5)

    def _proper(self, pos):
        for i, pt in enumerate(self.punts):
            q = self._a_pantalla(pt)
            if abs(q.x() - pos.x()) < 9 and abs(q.y() - pos.y()) < 9:
                return i
        return None

    def mousePressEvent(self, ev):
        i = self._proper(ev.position())
        if ev.button() == Qt.MouseButton.RightButton:
            if i is not None and 0 < i < len(self.punts) - 1:
                del self.punts[i]
                self._avisa()
            return
        if i is None:
            v = self._a_valor(ev.position())
            if any(abs(v[0] - p[0]) < 4 for p in self.punts):
                return
            self.punts.append(v)
            self.punts.sort()
            i = self.punts.index(v)
        self._mou = i
        self._avisa()

    def mouseMoveEvent(self, ev):
        if self._mou is None:
            return
        x, y = self._a_valor(ev.position())
        i = self._mou
        if i == 0:
            x = min(x, self.punts[1][0] - 1)
        elif i == len(self.punts) - 1:
            x = max(x, self.punts[-2][0] + 1)
        else:
            x = min(max(x, self.punts[i - 1][0] + 1), self.punts[i + 1][0] - 1)
        self.punts[i] = (x, y)
        self._avisa()

    def mouseReleaseEvent(self, ev):
        self._mou = None

    def _avisa(self):
        self.update()
        self.en_canvi()


class DialegCorbes(DialegPrevi):
    CANALS = ("rgb", "r", "g", "b")
    COLORS = (E.CREAM, "#F05046", "#5AC86E", "#5096F0")

    def __init__(self, parent, base, en_canvi):
        super().__init__(parent, t("ef_corbes"), en_canvi)
        self.base = base.convert("RGB")
        self.corbes = {c: [(0, 0), (255, 255)] for c in self.CANALS}
        fila = QHBoxLayout()
        fila.addWidget(QLabel(t("cv_canal")))
        self.c_canal = QComboBox()
        self.c_canal.addItems(["RGB", t("cv_vermell"), t("cv_verd"), t("cv_blau")])
        self.c_canal.currentIndexChanged.connect(self._canvi_canal)
        fila.addWidget(self.c_canal)
        fila.addStretch()
        self.cos.addLayout(fila)
        self.ed = EditorCorba(self.canvi)
        self.cos.addWidget(self.ed)
        self.cos.addWidget(QLabel(t("cv_ajuda"), objectName="suau", wordWrap=True))
        b_reset = QPushButton(t("ed_restableix"))
        b_reset.clicked.connect(self._reset)
        b_s = QPushButton(t("cv_corba_s"))
        b_s.clicked.connect(self._corba_s)
        self.botons([b_s, b_reset])
        self._hist = [self.base.convert("L").histogram()] + [self.base.histogram()[k * 256:(k + 1) * 256] for k in range(3)]
        self._canvi_canal()
        self.resize(420, 520)

    def _canvi_canal(self):
        i = self.c_canal.currentIndex()
        self.ed.punts = self.corbes[self.CANALS[i]]
        self.ed.color = QColor(self.COLORS[i])
        self.ed.hist = self._hist[i]
        self.ed.update()

    def _reset(self):
        self.corbes = {c: [(0, 0), (255, 255)] for c in self.CANALS}
        self._canvi_canal()
        self.canvi()

    def _corba_s(self):
        self.corbes["rgb"] = [(0, 0), (64, 50), (192, 206), (255, 255)]
        self.c_canal.setCurrentIndex(0)
        self._canvi_canal()
        self.canvi()

    def funcio(self):
        tots = _monotona(self.corbes["rgb"])
        luts = []
        for c in ("r", "g", "b"):
            lc = _monotona(self.corbes[c])
            luts.append([lc[tots[x]] for x in range(256)])
        return lambda im: _lut_rgb(im, luts)


# ========================================================= text / marca d'aigua
POSICIONS = ["tl", "tc", "tr", "ml", "mc", "mr", "bl", "bc", "br"]


def pinta_text(im, o):
    """Escriu el text i/o el logotip a la imatge (mida relativa a la foto, així la previsualització és fidel)."""
    q = IM.pil_a_qimage(im.convert("RGBA")).convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    W, H = q.width(), q.height()
    p = QPainter(q)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.setOpacity(o["opacitat"] / 100)
    costat = min(W, H)
    marge = costat * o["marge"] / 100
    font = QFont(o["font"])
    font.setPixelSize(max(6, int(costat * o["mida"] / 100)))
    font.setBold(o["negreta"])
    font.setItalic(o["cursiva"])
    p.setFont(font)
    fm = p.fontMetrics()
    text = o["text"]
    tw = fm.horizontalAdvance(text) if text else 0
    th = fm.height() if text else 0
    logo = None
    if o.get("logo") and os.path.exists(o["logo"]):
        logo = QImage(o["logo"])
        if not logo.isNull():
            lh = costat * o["mida_logo"] / 100
            logo = logo.scaledToHeight(max(4, int(lh)), Qt.TransformationMode.SmoothTransformation)
        else:
            logo = None
    lw, lh = (logo.width(), logo.height()) if logo else (0, 0)
    sep = marge * 0.5 if (logo and text) else 0
    bw, bh = lw + sep + tw, max(lh, th)
    pos = o["posicio"]
    x = {"l": marge, "c": (W - bw) / 2, "r": W - bw - marge}[pos[1]]
    y = {"t": marge, "m": (H - bh) / 2, "b": H - bh - marge}[pos[0]]
    if logo:
        p.drawImage(QPointF(x, y + (bh - lh) / 2), logo)
    if text:
        tx, ty = x + lw + sep, y + (bh - th) / 2 + fm.ascent()
        if o["ombra"]:
            p.setPen(QColor(0, 0, 0, 160))
            d = max(1, font.pixelSize() / 18)
            p.drawText(QPointF(tx + d, ty + d), text)
        p.setPen(QColor(o["color"]))
        p.drawText(QPointF(tx, ty), text)
    p.end()
    out = IM.qimage_a_pil(q)
    return out if im.mode == "RGBA" else out.convert("RGB")


class DialegText(DialegPrevi):
    def __init__(self, parent, en_canvi):
        super().__init__(parent, t("ef_text"), en_canvi)
        o = config.get("marca_aigua") or {}
        f = QFormLayout()
        self.e_text = QLineEdit(o.get("text", "© " + os.environ.get("USERNAME", "")))
        self.e_text.textChanged.connect(self.canvi)
        f.addRow(t("tx_text"), self.e_text)
        fila = QHBoxLayout()
        self.c_font = QFontComboBox()
        self.c_font.setCurrentFont(QFont(o.get("font", "Segoe UI")))
        self.c_font.currentFontChanged.connect(self.canvi)
        self.ch_b = QCheckBox("B", checked=o.get("negreta", True))
        self.ch_i = QCheckBox("I", checked=o.get("cursiva", False))
        for w in (self.ch_b, self.ch_i):
            w.toggled.connect(self.canvi)
        fila.addWidget(self.c_font, 1)
        fila.addWidget(self.ch_b)
        fila.addWidget(self.ch_i)
        f.addRow(t("tx_font"), fila)
        self.s_mida = self._slider(1, 30, o.get("mida", 5), " %")
        f.addRow(t("tx_mida"), self.s_mida[1])
        fila = QHBoxLayout()
        self.color = o.get("color", "#FFFFFF")
        self.b_color = QPushButton()
        self.b_color.setFixedWidth(60)
        self.b_color.clicked.connect(self._tria_color)
        self._pinta_color()
        self.ch_ombra = QCheckBox(t("tx_ombra"), checked=o.get("ombra", True))
        self.ch_ombra.toggled.connect(self.canvi)
        fila.addWidget(self.b_color)
        fila.addWidget(self.ch_ombra)
        fila.addStretch()
        f.addRow(t("tx_color"), fila)
        self.s_opac = self._slider(5, 100, o.get("opacitat", 80), " %")
        f.addRow(t("tx_opacitat"), self.s_opac[1])
        self.c_pos = QComboBox()
        for k in POSICIONS:
            self.c_pos.addItem(t("pos_" + k), k)
        self.c_pos.setCurrentIndex(max(0, self.c_pos.findData(o.get("posicio", "br"))))
        self.c_pos.currentIndexChanged.connect(self.canvi)
        f.addRow(t("tx_posicio"), self.c_pos)
        self.s_marge = self._slider(0, 20, o.get("marge", 3), " %")
        f.addRow(t("tx_marge"), self.s_marge[1])
        fila = QHBoxLayout()
        self.e_logo = QLineEdit(o.get("logo", ""))
        self.e_logo.setPlaceholderText(t("tx_sense_logo"))
        self.e_logo.textChanged.connect(self.canvi)
        b = QPushButton("…")
        b.setFixedWidth(34)
        b.clicked.connect(self._tria_logo)
        fila.addWidget(self.e_logo)
        fila.addWidget(b)
        f.addRow(t("tx_logo"), fila)
        self.s_mlogo = self._slider(2, 50, o.get("mida_logo", 10), " %")
        f.addRow(t("tx_mida_logo"), self.s_mlogo[1])
        self.cos.addLayout(f)
        self.botons()
        self.resize(460, 420)

    def _slider(self, mn, mx, v, suf):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        s = QSlider(Qt.Orientation.Horizontal, minimum=mn, maximum=mx, value=v)
        l = QLabel(f"{v}{suf}", minimumWidth=44, alignment=Qt.AlignmentFlag.AlignRight)
        s.valueChanged.connect(lambda x: (l.setText(f"{x}{suf}"), self.canvi()))
        h.addWidget(s)
        h.addWidget(l)
        return s, w

    def _pinta_color(self):
        self.b_color.setStyleSheet(f"background:{self.color}; border:1px solid {E.LINE}; border-radius:6px;")

    def _tria_color(self):
        c = QColorDialog.getColor(QColor(self.color), self, t("tx_color"))
        if c.isValid():
            self.color = c.name()
            self._pinta_color()
            self.canvi()

    def _tria_logo(self):
        f, _ = QFileDialog.getOpenFileName(self, t("tx_logo"), "", "PNG, JPG (*.png *.jpg *.jpeg *.webp *.bmp)")
        if f:
            self.e_logo.setText(f)

    def opcions(self):
        return dict(text=self.e_text.text(), font=self.c_font.currentFont().family(), negreta=self.ch_b.isChecked(),
                    cursiva=self.ch_i.isChecked(), mida=self.s_mida[0].value(), color=self.color,
                    ombra=self.ch_ombra.isChecked(), opacitat=self.s_opac[0].value(),
                    posicio=self.c_pos.currentData(), marge=self.s_marge[0].value(),
                    logo=self.e_logo.text().strip(), mida_logo=self.s_mlogo[0].value())

    def funcio(self):
        o = self.opcions()
        return lambda im: pinta_text(im, o)

    def accept(self):
        config.set("marca_aigua", self.opcions())
        super().accept()


# ============================================== utilitat comuna visor/editor
def amb_previsualitzacio(parent, llenc, base_pil, classe):
    """Obre un diàleg sobre una còpia reduïda i mostra el resultat al llenç.
    Retorna la funció (PIL -> PIL) per aplicar a la foto sencera, o None si es cancel·la."""
    from PIL import Image as _I
    base = base_pil.copy()
    costat = int(max(llenc.width(), llenc.height()) * llenc.devicePixelRatioF())
    base.thumbnail((costat, costat), _I.Resampling.BILINEAR)
    vista = llenc.img
    conserva = (llenc.ajusta, llenc.z, llenc.cx, llenc.cy)

    def mostra(funcio):
        try:
            llenc.posa_imatge(IM.pil_a_qimage(funcio(base)))
        except Exception:
            pass

    d = classe(parent, mostra) if classe is DialegText else classe(parent, base, mostra)
    finestra = parent.window()
    d.move(finestra.mapToGlobal(finestra.rect().topLeft()) + QPointF(40, 80).toPoint())
    ok = d.exec()
    llenc.posa_imatge(vista)
    if not conserva[0]:
        llenc.ajusta, llenc.z, llenc.cx, llenc.cy = conserva
        llenc._esc = None
        llenc._limita()
        llenc._suau.start(0)
        llenc.update()
    return d.funcio() if ok else None
