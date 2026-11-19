"""Llenç amb zoom/desplaçament/retall i finestra de visualització a pantalla completa."""

import os

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QCursor, QGuiApplication, QImage, QKeySequence, QPainter, QPen, QPixmap, QShortcut, QTransform
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMessageBox, QToolButton, QVBoxLayout, QWidget

import config
import estil as E
import imatges as IM
from i18n import t

FONS_A = QColor(E.BG_A)
FONS_B = QColor(E.BG_B)


class Llenc(QWidget):
    """Mostra una QImage amb ajust a la finestra, zoom centrat al ratolí, arrossegament i selecció de retall."""
    zoom_canviat = pyqtSignal(float)
    roda = pyqtSignal(int)
    doble_clic = pyqtSignal()
    retall_canviat = pyqtSignal(QRectF)
    ratoli_mogut = pyqtSignal(QPointF)

    ZOOMS = [0.02, 0.05, 0.08, 0.1, 0.15, 0.2, 0.25, 0.33, 0.5, 0.67, 0.75, 1, 1.25, 1.5, 2, 3, 4, 6, 8, 12, 16, 24, 32]

    def __init__(self, parent=None, roda_navega=True):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(200, 150)
        self.roda_navega = roda_navega
        self.img = QImage()
        self._pix = None            # QPixmap sencer (es fa quan cal)
        self._esc = None            # QPixmap ja reduït a la mida actual
        self._esc_z = None
        self.z = 1.0
        self.ajusta = True
        self.amplia_petites = False
        self.cx = self.cy = 0.0
        self._arrossega = None
        self.mode_retall = False
        self.proporcio = None       # amplada/alçada o None (lliure)
        self.retall = QRectF()
        self._retall_ini = None
        self._suau = QTimer(self, singleShot=True, timeout=self._fes_suau)
        self.text_buit = ""

    # ------------------------------------------------------------ imatge
    def posa_imatge(self, img, conserva_vista=False):
        self.img = img if img is not None else QImage()
        self._pix = None
        self._esc = None
        if not conserva_vista or self.img.isNull():
            self.ajusta = True
            self.retall = QRectF()
        self._recalcula()
        if self.ajusta and self.z < 1 and not self.img.isNull():
            self._fes_suau()          # primera vista ja nítida
        self.update()

    def _pixmap(self):
        if self._pix is None and not self.img.isNull():
            self._pix = QPixmap.fromImage(self.img)
        return self._pix

    def _z_ajust(self):
        if self.img.isNull():
            return 1.0
        w, h = self.width(), self.height()
        z = min(w / self.img.width(), h / self.img.height())
        return z if (self.amplia_petites or z < 1) else 1.0

    def _recalcula(self):
        if self.img.isNull():
            return
        if self.ajusta:
            self.z = self._z_ajust()
            self.cx, self.cy = self.img.width() / 2, self.img.height() / 2
        self._limita()
        self.zoom_canviat.emit(self.z)

    def _limita(self):
        iw, ih = self.img.width() * self.z, self.img.height() * self.z
        for eix, mida_vista, mida_img, total in (("x", self.width(), iw, self.img.width()),
                                                  ("y", self.height(), ih, self.img.height())):
            if mida_img <= mida_vista:
                v = total / 2
            else:
                mig = mida_vista / 2 / self.z
                v = min(max(self.cx if eix == "x" else self.cy, mig), total - mig)
            if eix == "x":
                self.cx = v
            else:
                self.cy = v

    def origen(self):
        return QPointF(self.width() / 2 - self.cx * self.z, self.height() / 2 - self.cy * self.z)

    def a_imatge(self, p):
        o = self.origen()
        return QPointF((p.x() - o.x()) / self.z, (p.y() - o.y()) / self.z)

    # ------------------------------------------------------------- zoom
    def posa_zoom(self, z, punt=None):
        if self.img.isNull():
            return
        z = max(0.01, min(z, 40.0))
        if punt is None:
            punt = QPointF(self.width() / 2, self.height() / 2)
        pi = self.a_imatge(punt)
        self.z = z
        self.ajusta = False
        o = QPointF(punt.x() - pi.x() * z, punt.y() - pi.y() * z)
        self.cx = (self.width() / 2 - o.x()) / z
        self.cy = (self.height() / 2 - o.y()) / z
        self._limita()
        self._esc = None
        self._suau.start(140)
        self.zoom_canviat.emit(self.z)
        self.update()

    def zoom_pas(self, sentit, punt=None):
        if sentit > 0:
            z = next((v for v in self.ZOOMS if v > self.z * 1.01), self.ZOOMS[-1])
        else:
            z = next((v for v in reversed(self.ZOOMS) if v < self.z * 0.99), self.ZOOMS[0])
        self.posa_zoom(z, punt)

    def posa_ajusta(self):
        self.ajusta = True
        self._esc = None
        self._recalcula()
        self._suau.start(0)
        self.update()

    def alterna_100(self):
        if abs(self.z - 1) < 1e-3:
            self.posa_ajusta()
        else:
            self.posa_zoom(1.0, self.mapFromGlobal(QCursor.pos()) if self.underMouse() else None)

    def _fes_suau(self):
        if self.img.isNull() or self.z >= 1:
            self._esc = None
            return
        dpr = self.devicePixelRatioF()
        if self.z * dpr >= 1:
            self._esc = None
            return
        w = max(1, round(self.img.width() * self.z * dpr))
        h = max(1, round(self.img.height() * self.z * dpr))
        self._esc = QPixmap.fromImage(self.img.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio,
                                                      Qt.TransformationMode.SmoothTransformation))
        self._esc.setDevicePixelRatio(dpr)
        self._esc_z = self.z
        self.update()

    # ----------------------------------------------------------- pintar
    def paintEvent(self, ev):
        p = QPainter(self)
        p.fillRect(self.rect(), FONS_B)
        if self.img.isNull():
            if self.text_buit:
                p.setPen(QColor(E.SOFT))
                p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text_buit)
            return
        o = self.origen()
        desti = QRectF(o.x(), o.y(), self.img.width() * self.z, self.img.height() * self.z)
        if self.img.hasAlphaChannel():
            self._pinta_escacs(p, desti.intersected(QRectF(self.rect())))
        if self._esc is not None and self._esc_z == self.z:
            p.drawPixmap(QPointF(round(o.x()), round(o.y())), self._esc)
        else:
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, self.z < 2)
            vista = QRectF(self.rect()).intersected(desti)
            font = QRectF((vista.x() - o.x()) / self.z, (vista.y() - o.y()) / self.z,
                          vista.width() / self.z, vista.height() / self.z)
            p.drawPixmap(vista, self._pixmap(), font)
        if self.mode_retall and not self.retall.isNull():
            r = QRectF(o.x() + self.retall.x() * self.z, o.y() + self.retall.y() * self.z,
                       self.retall.width() * self.z, self.retall.height() * self.z)
            fosc = QColor(26, 37, 51, 170)
            p.fillRect(QRectF(desti.left(), desti.top(), desti.width(), r.top() - desti.top()), fosc)
            p.fillRect(QRectF(desti.left(), r.bottom(), desti.width(), desti.bottom() - r.bottom()), fosc)
            p.fillRect(QRectF(desti.left(), r.top(), r.left() - desti.left(), r.height()), fosc)
            p.fillRect(QRectF(r.right(), r.top(), desti.right() - r.right(), r.height()), fosc)
            p.setPen(QPen(QColor(E.OR1), 2))
            p.drawRect(r)
            p.setPen(QPen(QColor(246, 239, 226, 90), 1, Qt.PenStyle.DashLine))
            for i in (1, 2):
                x = r.left() + r.width() * i / 3
                y = r.top() + r.height() * i / 3
                p.drawLine(QPointF(x, r.top()), QPointF(x, r.bottom()))
                p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
            txt = f"{int(self.retall.width())} × {int(self.retall.height())}"
            caixa = QRectF(r.left() + 6, r.top() + 6, p.fontMetrics().horizontalAdvance(txt) + 14, 22)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(30, 42, 59, 220))
            p.drawRoundedRect(caixa, 5, 5)
            p.setPen(QColor(E.CREAM))
            p.drawText(caixa, Qt.AlignmentFlag.AlignCenter, txt)

    def _pinta_escacs(self, p, r):
        c1, c2, m = QColor(E.CARD), QColor(E.BG3), 12
        p.save()
        p.setClipRect(r)
        y = int(r.top()) - int(r.top()) % m
        while y < r.bottom():
            x = int(r.left()) - int(r.left()) % m
            while x < r.right():
                p.fillRect(x, y, m, m, c1 if (x // m + y // m) % 2 == 0 else c2)
                x += m
            y += m
        p.restore()

    def resizeEvent(self, ev):
        if self.ajusta:
            self._esc = None
            self._recalcula()
            self._suau.start(80)
        else:
            self._limita()
        super().resizeEvent(ev)

    # ----------------------------------------------------------- ratolí
    def wheelEvent(self, ev):
        d = ev.angleDelta().y()
        if not d:
            return
        if self.roda_navega and not (ev.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.roda.emit(1 if d < 0 else -1)
        else:
            self.zoom_pas(1 if d > 0 else -1, ev.position())

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton and not self.img.isNull():
            if self.mode_retall:
                self._retall_ini = self._dins(self.a_imatge(ev.position()))
                self.retall = QRectF(self._retall_ini, self._retall_ini)
            else:
                self._arrossega = (ev.position(), self.cx, self.cy)
                self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def _dins(self, pi):
        return QPointF(min(max(pi.x(), 0), self.img.width()), min(max(pi.y(), 0), self.img.height()))

    def mouseMoveEvent(self, ev):
        self.ratoli_mogut.emit(ev.position())
        if self._retall_ini is not None:
            fi = self._dins(self.a_imatge(ev.position()))
            a = self._retall_ini
            if self.proporcio:
                w = abs(fi.x() - a.x())
                h = w / self.proporcio
                sy = 1 if fi.y() >= a.y() else -1
                fi = QPointF(fi.x(), a.y() + sy * h)
                fi = self._dins(fi)
                h = abs(fi.y() - a.y())
                w = h * self.proporcio
                sx = 1 if ev.position().x() >= self.origen().x() + a.x() * self.z else -1
                fi = QPointF(a.x() + sx * w, fi.y())
            self.retall = QRectF(a, fi).normalized()
            self.retall_canviat.emit(self.retall)
            self.update()
        elif self._arrossega is not None:
            p0, cx, cy = self._arrossega
            d = ev.position() - p0
            self.cx = cx - d.x() / self.z
            self.cy = cy - d.y() / self.z
            self._limita()
            self.update()

    def mouseReleaseEvent(self, ev):
        if self._retall_ini is not None:
            self._retall_ini = None
            if self.retall.width() < 3 or self.retall.height() < 3:
                self.retall = QRectF()
            self.retall_canviat.emit(self.retall)
            self.update()
        self._arrossega = None
        self.setCursor(Qt.CursorShape.CrossCursor if self.mode_retall else Qt.CursorShape.ArrowCursor)

    def mouseDoubleClickEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton and not self.mode_retall:
            self.doble_clic.emit()

    def posa_mode_retall(self, actiu):
        self.mode_retall = actiu
        self.retall = QRectF()
        self.setCursor(Qt.CursorShape.CrossCursor if actiu else Qt.CursorShape.ArrowCursor)
        self.retall_canviat.emit(self.retall)
        self.update()


def boto_barra(nom_icona, tooltip, accio, text=None, mirall=False):
    b = QToolButton()
    if nom_icona:
        b.setIcon(E.icona(nom_icona, mirall=mirall))
        b.setIconSize(QSize(22, 22))
    if text:
        b.setText(text)
        if nom_icona:
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    b.setToolTip(tooltip)
    b.setAutoRaise(True)
    b.clicked.connect(accio)
    b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return b


class Visor(QWidget):
    """Finestra de visualització: navega per la carpeta amb precàrrega de les fotos veïnes."""
    tancat = pyqtSignal(str)          # camí de l'última foto vista
    eliminada = pyqtSignal(str)
    editar = pyqtSignal(str)

    def __init__(self, camins, index, memoria, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setObjectName("fons")
        self.setWindowTitle("Xoriguer Fotos")
        self.setWindowIcon(E.icona_app())
        self.camins = list(camins)
        self.index = max(0, min(index, len(self.camins) - 1))
        self.memoria = memoria
        self.memoria.llesta.connect(self._precarregada)
        self.gir = {}  # cami -> graus (només vista, fins que es desa)

        self.llenc = Llenc(self)
        self.llenc.amplia_petites = config.get("amplia_petites")
        self.llenc.roda.connect(self.mou)
        self.llenc.doble_clic.connect(self.close)
        self.llenc.zoom_canviat.connect(lambda z: self._actualitza_peu())
        self.llenc.ratoli_mogut.connect(self._ratoli)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.llenc)

        # barra superior (apareix en acostar el ratolí a dalt)
        self.barra = QFrame(self)
        self.barra.setStyleSheet(f"QFrame {{ background: rgba(30,42,59,230); border-bottom: 1px solid {E.LINE}; }}")
        bl = QHBoxLayout(self.barra)
        bl.setContentsMargins(8, 4, 8, 4)
        for b in [
            boto_barra("anterior", t("v_anterior") + "  (←)", lambda: self.mou(-1)),
            boto_barra("seguent", t("v_seguent") + "  (→)", lambda: self.mou(1)),
            None,
            boto_barra("ajusta", t("v_ajusta") + "  (F)", self.llenc.posa_ajusta),
            boto_barra(None, t("v_100") + "  (1 / Z)", lambda: self.llenc.posa_zoom(1.0), "1:1"),
            boto_barra("meszoom", t("v_mes_zoom") + "  (+)", lambda: self.llenc.zoom_pas(1)),
            boto_barra("menyszoom", t("v_menys_zoom") + "  (−)", lambda: self.llenc.zoom_pas(-1)),
            None,
            boto_barra("gira", t("v_gira_e") + "  (L)", lambda: self.gira(-90), mirall=True),
            boto_barra("gira", t("v_gira_d") + "  (R)", lambda: self.gira(90)),
            boto_barra("desa", t("v_desa_gir") + "  (Ctrl+S)", self.desa_gir),
            None,
            boto_barra("edita", t("v_edita") + "  (E)", self._edita),
            boto_barra("presentacio", t("v_presentacio") + "  (S)", self.alterna_presentacio),
            boto_barra("info", t("v_info") + "  (I)", self.alterna_info),
            boto_barra("copia", t("v_copia") + "  (Ctrl+C)", self.copia),
            boto_barra("elimina", t("v_elimina") + "  (Supr)", self.elimina),
            None,
            boto_barra("pantalla", t("v_pantalla") + "  (F11)", self.alterna_pantalla),
            boto_barra("tanca", t("v_tanca") + "  (Esc)", self.close),
        ]:
            if b is None:
                s = QFrame()
                s.setFixedSize(1, 24)
                s.setStyleSheet(f"background:{E.LINE}; border:none;")
                bl.addWidget(s)
            else:
                b.setStyleSheet("QToolButton { border: none; padding: 4px; }")
                bl.addWidget(b)
        bl.addStretch()
        self.lbl_titol = QLabel()
        self.lbl_titol.setStyleSheet(f"color:{E.CREAM}; background: transparent; border: none; font-weight:600;")
        bl.addWidget(self.lbl_titol)
        self.barra.hide()

        self.peu = QLabel(self)
        self.peu.setStyleSheet(f"background: rgba(30,42,59,200); color:{E.CREAM}; padding: 4px 10px; border-radius: 6px;")
        self.info = QLabel(self)
        self.info.setStyleSheet(f"background: rgba(39,53,74,235); color:{E.CREAM}; padding: 12px; "
                                f"border: 1px solid {E.LINE}; border-radius: 8px;")
        self.info.setTextFormat(Qt.TextFormat.RichText)
        self.info.setWordWrap(True)
        self.info.setMaximumWidth(460)
        self.info.hide()

        self.temporitzador = QTimer(self, timeout=lambda: self.mou(1, en_bucle=True))
        self._amaga_cursor = QTimer(self, singleShot=True, timeout=self._amaga_ratoli)

        dreceres = {
            "Right": lambda: self.mou(1), "Left": lambda: self.mou(-1),
            "Space": lambda: self.mou(1), "Backspace": lambda: self.mou(-1),
            "PgDown": lambda: self.mou(1), "PgUp": lambda: self.mou(-1),
            "Home": lambda: self.ves(0), "End": lambda: self.ves(len(self.camins) - 1),
            "Esc": self.close, "Return": self.close, "Enter": self.close,
            "+": lambda: self.llenc.zoom_pas(1), "=": lambda: self.llenc.zoom_pas(1),
            "-": lambda: self.llenc.zoom_pas(-1), "F": self.llenc.posa_ajusta,
            "1": lambda: self.llenc.posa_zoom(1.0), "Z": self.llenc.alterna_100, "*": self.llenc.alterna_100,
            "R": lambda: self.gira(90), "L": lambda: self.gira(-90), "Ctrl+S": self.desa_gir,
            "E": self._edita, "S": self.alterna_presentacio, "I": self.alterna_info,
            "Del": self.elimina, "F11": self.alterna_pantalla, "Ctrl+C": self.copia,
        }
        for tecla, f in dreceres.items():
            QShortcut(QKeySequence(tecla), self, activated=f)

        self.resize(1200, 800)
        self.mostra()

    # --------------------------------------------------------- navegació
    def actual(self):
        return self.camins[self.index] if self.camins else None

    def mostra(self):
        cami = self.actual()
        if cami is None:
            self.close()
            return
        img = self.memoria.carrega(cami)
        g = self.gir.get(cami, 0)
        if g and not img.isNull():
            img = img.transformed(QTransform().rotate(g))
        self.llenc.text_buit = t("v_no_es_pot_obrir")
        self.llenc.posa_imatge(img)
        self.lbl_titol.setText(os.path.basename(cami))
        self.setWindowTitle(f"{os.path.basename(cami)} — Xoriguer Fotos")
        self._actualitza_peu()
        if self.info.isVisible():
            self._omple_info()
        # precarrega les veïnes (primer la següent)
        n = len(self.camins)
        veines = [self.camins[(self.index + d) % n] for d in (1, -1, 2, 3, -2) if n > 1]
        self.memoria.precarrega(list(dict.fromkeys(veines)))

    def _precarregada(self, cami):
        pass

    def mou(self, d, en_bucle=False):
        if not self.camins:
            return
        n = len(self.camins)
        nou = self.index + d
        if en_bucle:
            nou %= n
        nou = max(0, min(nou, n - 1))
        if nou != self.index:
            self.index = nou
            self.mostra()

    def ves(self, i):
        if self.camins:
            self.index = max(0, min(i, len(self.camins) - 1))
            self.mostra()

    def _actualitza_peu(self):
        cami = self.actual()
        if not cami:
            return
        img = self.llenc.img
        mida = f"{img.width()} × {img.height()}" if not img.isNull() else "—"
        try:
            kb = os.path.getsize(cami) / 1024
            pes = f"{kb / 1024:.1f} MB" if kb > 1024 else f"{kb:.0f} KB"
        except OSError:
            pes = ""
        extra = "   ▶ " + t("v_presentacio") if self.temporitzador.isActive() else ""
        self.peu.setText(f"{self.index + 1} / {len(self.camins)}    {os.path.basename(cami)}    "
                         f"{mida}    {pes}    {round(self.llenc.z * 100)}%{extra}")
        self.peu.adjustSize()
        self._colloca()

    def _colloca(self):
        self.peu.move(12, self.height() - self.peu.height() - 12)
        self.barra.setGeometry(0, 0, self.width(), self.barra.sizeHint().height())
        self.info.adjustSize()
        self.info.move(self.width() - self.info.width() - 16, 60)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._colloca()

    def _ratoli(self, pos):
        if self.llenc._arrossega is None:
            self.llenc.unsetCursor()
        self.barra.setVisible(pos.y() < 70)
        if self.barra.isVisible():
            self.barra.raise_()
        if self.isFullScreen():
            self._amaga_cursor.start(2500)

    def _amaga_ratoli(self):
        if self.isFullScreen() and not self.barra.isVisible():
            self.llenc.setCursor(Qt.CursorShape.BlankCursor)

    # ------------------------------------------------------------ accions
    def gira(self, graus):
        cami = self.actual()
        if not cami or self.llenc.img.isNull():
            return
        self.gir[cami] = (self.gir.get(cami, 0) + graus) % 360
        self.llenc.posa_imatge(self.llenc.img.transformed(QTransform().rotate(graus)))
        self._actualitza_peu()

    def desa_gir(self):
        cami = self.actual()
        g = self.gir.get(cami, 0) if cami else 0
        if not g:
            return
        import editor
        try:
            editor.desa_girada(cami, g, config.get("qualitat_jpeg"))
        except Exception as e:
            QMessageBox.warning(self, "Xoriguer Fotos", t("e_no_desat") + f"\n{e}")
            return
        self.gir.pop(cami, None)
        self.memoria.oblida(cami)
        self.mostra()
        self.peu.setText(self.peu.text() + "    ✔ " + t("v_desat"))
        self.peu.adjustSize()

    def _edita(self):
        cami = self.actual()
        if cami:
            if self.temporitzador.isActive():
                self.alterna_presentacio()
            self.editar.emit(cami)

    def recarrega(self, cami=None):
        if cami:
            self.memoria.oblida(cami)
            self.gir.pop(cami, None)
        self.mostra()

    def alterna_presentacio(self):
        if self.temporitzador.isActive():
            self.temporitzador.stop()
        else:
            self.temporitzador.start(int(config.get("segons_presentacio") * 1000))
            if not self.isFullScreen():
                self.showFullScreen()
        self._actualitza_peu()

    def alterna_info(self):
        if self.info.isVisible():
            self.info.hide()
        else:
            self._omple_info()
            self.info.show()
            self.info.raise_()

    def _omple_info(self):
        cami = self.actual()
        if not cami:
            return
        ex = IM.info_exif(cami)
        files = [(t("i_nom"), os.path.basename(cami)),
                 (t("i_mida"), f"{self.llenc.img.width()} × {self.llenc.img.height()} px")]
        for k in ("camera", "objectiu", "data", "exposicio", "diafragma", "iso", "focal"):
            if k in ex:
                files.append((t("i_" + k), ex[k]))
        html = "<table cellspacing='3'>" + "".join(
            f"<tr><td style='color:{E.OR1}; padding-right:10px'>{a}</td><td>{b}</td></tr>" for a, b in files) + "</table>"
        self.info.setText(html)
        self._colloca()

    def copia(self):
        if not self.llenc.img.isNull():
            QGuiApplication.clipboard().setImage(self.llenc.img)

    def elimina(self):
        cami = self.actual()
        if not cami:
            return
        if config.get("confirma_eliminar"):
            r = QMessageBox.question(self, "Xoriguer Fotos", t("p_elimina_1", nom=os.path.basename(cami)))
            if r != QMessageBox.StandardButton.Yes:
                return
        from PyQt6.QtCore import QFile
        if not QFile.moveToTrash(cami):
            QMessageBox.warning(self, "Xoriguer Fotos", t("e_no_eliminat"))
            return
        self.memoria.oblida(cami)
        self.eliminada.emit(cami)
        del self.camins[self.index]
        if not self.camins:
            self.close()
            return
        self.index = min(self.index, len(self.camins) - 1)
        self.mostra()

    def alterna_pantalla(self):
        if self.isFullScreen():
            self.showMaximized()
        else:
            self.showFullScreen()

    def closeEvent(self, ev):
        self.temporitzador.stop()
        try:
            self.memoria.llesta.disconnect(self._precarregada)
        except TypeError:
            pass
        self.tancat.emit(self.actual() or "")
        super().closeEvent(ev)
