"""Llenç amb zoom/desplaçament/retall i finestra de visualització a pantalla completa."""

import os

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QCursor, QGuiApplication, QImage, QKeySequence, QPainter, QPen, QPixmap, QShortcut
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
    """Finestra de visualització: navega per la carpeta amb precàrrega i permet retocar sense sortir-ne."""
    tancat = pyqtSignal(str)          # camí de l'última foto vista
    eliminada = pyqtSignal(str)
    editar = pyqtSignal(str)
    desat = pyqtSignal(str)
    canvi_fitxers = pyqtSignal()      # s'ha canviat el nom o copiat: cal refrescar la llista
    surt = pyqtSignal()

    def __init__(self, camins, index, memoria, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setObjectName("fons")
        self.setWindowTitle("Xoriguer Fotos")
        self.setWindowIcon(E.icona_app())
        self.camins = list(camins)
        self.index = max(0, min(index, len(self.camins) - 1))
        self.memoria = memoria
        # edició dins del visor
        self.edicio = None            # PIL.Image de treball (només quan s'ha tocat alguna cosa)
        self.desfer, self.refer = [], []
        self.modificat = False

        self.llenc = Llenc(self)
        self.llenc.amplia_petites = config.get("amplia_petites")
        self.llenc.roda.connect(lambda d: None if self.llenc.mode_retall else self.mou(d))
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
            boto_barra("retalla", t("ed_retalla") + "  (X)", self.retalla),
            boto_barra("desfes", t("ed_desfes") + "  (Ctrl+Z)", self.desfes),
            boto_barra("desa", t("ed_desa") + "  (Ctrl+S)", self.desa),
            None,
            boto_barra("edita", t("pe_editor") + "  (E)", self._edita),
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

        from panells import PanellEdicio, PanellInfo
        self.ped = PanellEdicio(self)
        self.pinf = PanellInfo(self)

        self.temporitzador = QTimer(self, timeout=self._pas_presentacio)
        self._amaga_cursor = QTimer(self, singleShot=True, timeout=self._amaga_ratoli)

        dreceres = {
            "Right": lambda: self.mou(1), "Left": lambda: self.mou(-1),
            "Space": lambda: self.mou(1), "Backspace": lambda: self.mou(-1),
            "PgDown": lambda: self.mou(1), "PgUp": lambda: self.mou(-1),
            "Home": lambda: self.ves(0), "End": lambda: self.ves(len(self.camins) - 1),
            "Esc": self._esc, "Return": self._intro, "Enter": self._intro,
            "+": lambda: self.llenc.zoom_pas(1), "=": lambda: self.llenc.zoom_pas(1),
            "-": lambda: self.llenc.zoom_pas(-1), "F": self.llenc.posa_ajusta,
            "1": lambda: self.llenc.posa_zoom(1.0), "Z": self.llenc.alterna_100, "*": self.llenc.alterna_100,
            "R": lambda: self.gira(90), "L": lambda: self.gira(-90), "H": self.mirall_h, "V": self.mirall_v,
            "X": self.retalla, "Ctrl+R": self.canvia_mida, "Ctrl+T": self.ajusta_llum,
            "Ctrl+Shift+B": lambda: self.efecte("auto"),
            "Ctrl+Z": self.desfes, "Ctrl+Y": self.refes, "Ctrl+Shift+Z": self.refes,
            "Ctrl+S": self.desa, "Ctrl+Shift+S": self.desa_com, "Ctrl+O": self.obre, "Ctrl+P": self.imprimeix,
            "Shift+R": self.recarrega, "E": self._edita, "S": self.alterna_presentacio, "I": self.alterna_info,
            "C": lambda: self.copia_mou(False), "M": lambda: self.copia_mou(True), "F2": self.reanomena,
            "W": self.explorador, "Del": self.elimina, "F11": self.alterna_pantalla, "Ctrl+C": self.copia,
            "Alt+X": self._surt,
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
        self.llenc.text_buit = t("v_no_es_pot_obrir")
        if self.llenc.mode_retall:
            self.llenc.posa_mode_retall(False)
        self.llenc.posa_imatge(img)
        self.lbl_titol.setText(os.path.basename(cami))
        self.setWindowTitle(f"{os.path.basename(cami)} — Xoriguer Fotos")
        self._despres_canvi()
        # precarrega les veïnes (primer la següent)
        n = len(self.camins)
        veines = [self.camins[(self.index + d) % n] for d in (1, -1, 2, 3, -2) if n > 1]
        self.memoria.precarrega(list(dict.fromkeys(veines)))

    def _despres_canvi(self):
        self._actualitza_peu()
        self.ped.actualitza(self.modificat, bool(self.desfer), bool(self.refer))
        if self.pinf.isVisible():
            self._omple_info()

    def mou(self, d, en_bucle=False):
        if not self.camins:
            return
        n = len(self.camins)
        nou = self.index + d
        if en_bucle:
            nou %= n
        nou = max(0, min(nou, n - 1))
        if nou != self.index and self._pot_sortir():
            self.index = nou
            self.mostra()

    def ves(self, i):
        if self.camins and self._pot_sortir():
            self.index = max(0, min(i, len(self.camins) - 1))
            self.mostra()

    def _pas_presentacio(self):
        if self.modificat:
            self.temporitzador.stop()
            self._actualitza_peu()
        else:
            self.mou(1, en_bucle=True)

    def _actualitza_peu(self, extra=""):
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
        if self.temporitzador.isActive():
            extra += "   ▶ " + t("v_presentacio")
        if self.modificat:
            extra += f"   ● {t('v_modificada')}"
        if self.llenc.mode_retall:
            extra += "   ✂ " + t("v_retall_ajuda")
        self.peu.setText(f"{self.index + 1} / {len(self.camins)}    {os.path.basename(cami)}    "
                         f"{mida}    {pes}    {round(self.llenc.z * 100)}%{extra}")
        self.peu.adjustSize()
        self._colloca()

    def _colloca(self):
        w, h = self.width(), self.height()
        self.peu.move(12, h - self.peu.height() - 12)
        self.barra.setGeometry(0, 0, w, self.barra.sizeHint().height())
        for p, x in ((self.ped, 0), (self.pinf, w - self.pinf.amplada)):
            ph = min(p.alcada_ideal(), h - 20)
            p.setGeometry(x, max(10, (h - ph) // 2), p.amplada, ph)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._colloca()

    def _ratoli(self, pos):
        if self.llenc._arrossega is None and not self.llenc.mode_retall:
            self.llenc.unsetCursor()
        x, y = pos.x(), pos.y()
        ocupat = self.llenc._arrossega is not None or self.llenc._retall_ini is not None
        if not ocupat:
            if x <= 8 and not self.ped.isVisible():
                self._mostra_panell(self.ped)
            elif x >= self.width() - 9 and not self.pinf.isVisible():
                self._omple_info()
                self._mostra_panell(self.pinf)
        if self.ped.isVisible() and not self.ped.fixat and x > self.ped.amplada + 30:
            self.ped.hide()
        if self.pinf.isVisible() and not self.pinf.fixat and x < self.width() - self.pinf.amplada - 30:
            self.pinf.hide()
        self.barra.setVisible(y < 70 and not ocupat)
        if self.barra.isVisible():
            self.barra.raise_()
        if self.isFullScreen():
            self._amaga_cursor.start(2500)

    def _mostra_panell(self, p):
        self._colloca()
        p.show()
        p.raise_()

    def _amaga_ratoli(self):
        if self.isFullScreen() and not self.barra.isVisible() and not self.ped.isVisible() \
                and not self.pinf.isVisible() and not self.llenc.mode_retall:
            self.llenc.setCursor(Qt.CursorShape.BlankCursor)

    # ------------------------------------------------------ edició ràpida
    def op(self, funcio):
        """Aplica una operació (PIL -> PIL) a la foto que es veu; es pot desfer i cal desar-la."""
        cami = self.actual()
        if not cami or self.llenc.img.isNull():
            return
        if self.temporitzador.isActive():
            self.alterna_presentacio()
        from PyQt6.QtWidgets import QApplication
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            if self.edicio is None:
                self.edicio = IM.obre_pil(cami)
            nova = funcio(self.edicio)
        except Exception as e:
            QMessageBox.warning(self, "Xoriguer Fotos", str(e))
            return
        finally:
            QApplication.restoreOverrideCursor()
        mateixa_mida = nova.size == self.edicio.size
        self.desfer.append(self.edicio)
        del self.desfer[:-12]
        self.refer.clear()
        self.edicio = nova
        self.modificat = True
        self._mostra_edicio(mateixa_mida)

    def _mostra_edicio(self, conserva=False):
        if self.llenc.mode_retall:
            self.llenc.posa_mode_retall(False)
        self.llenc.posa_imatge(IM.pil_a_qimage(self.edicio), conserva_vista=conserva)
        self._despres_canvi()

    def _reinicia_edicio(self):
        self.edicio = None
        self.desfer.clear()
        self.refer.clear()
        self.modificat = False

    def gira(self, graus):
        self.op(lambda im: im.rotate(-graus, expand=True))

    def mirall_h(self):
        from PIL import ImageOps
        self.op(ImageOps.mirror)

    def mirall_v(self):
        from PIL import ImageOps
        self.op(ImageOps.flip)

    def efecte(self, nom):
        import editor
        self.op(editor.EFECTES[nom])

    def canvia_mida(self):
        import editor
        img = self.llenc.img
        if img.isNull():
            return
        d = editor.DialegMida(img.width(), img.height(), self)
        if d.exec():
            w, h = d.valors()
            if (w, h) != (img.width(), img.height()):
                from PIL import Image
                self.op(lambda im: im.resize((w, h), Image.Resampling.LANCZOS))

    def retalla(self):
        if self.llenc.img.isNull():
            return
        self.llenc.posa_mode_retall(not self.llenc.mode_retall)
        self._actualitza_peu()

    def _aplica_retall(self):
        r = self.llenc.retall
        caixa = (int(round(r.left())), int(round(r.top())), int(round(r.right())), int(round(r.bottom())))
        self.op(lambda im: im.crop(caixa))

    def ajusta_llum(self):
        cami = self.actual()
        if not cami or self.llenc.img.isNull():
            return
        import editor
        from panells import DialegAjustos
        from PIL import Image
        base = (self.edicio if self.edicio is not None else IM.obre_pil(cami)).copy()
        costat = int(max(self.width(), self.height()) * self.devicePixelRatioF())
        base.thumbnail((costat, costat), Image.Resampling.BILINEAR)
        vista = self.llenc.img

        def previsualitza(v):
            self.llenc.posa_imatge(IM.pil_a_qimage(editor.aplica_ajustos(base, v)))

        d = DialegAjustos(self, previsualitza)
        d.move(self.mapToGlobal(self.rect().topLeft()) + QPointF(40, 80).toPoint())
        ok = d.exec()
        v = d.valors()
        self.llenc.posa_imatge(vista)
        if ok and any(v.values()):
            self.op(lambda im: editor.aplica_ajustos(im, v))

    def desfes(self):
        if self.desfer:
            self.refer.append(self.edicio)
            self.edicio = self.desfer.pop()
            self.modificat = bool(self.desfer)
            if not self.modificat:
                self.edicio = None
                self.llenc.posa_imatge(self.memoria.carrega(self.actual()))
                self._despres_canvi()
            else:
                self._mostra_edicio()

    def refes(self):
        if self.refer:
            if self.edicio is None:
                self.edicio = IM.obre_pil(self.actual())
            self.desfer.append(self.edicio)
            self.edicio = self.refer.pop()
            self.modificat = True
            self._mostra_edicio()

    def desa(self):
        cami = self.actual()
        if not cami or not self.modificat:
            return True
        import editor
        try:
            editor.desa(self.edicio, cami, config.get("qualitat_jpeg"), original=cami)
        except Exception as e:
            QMessageBox.warning(self, "Xoriguer Fotos", t("e_no_desat") + f"\n{e}")
            return False
        self._reinicia_edicio()
        self.memoria.oblida(cami)
        self.desat.emit(cami)
        self.mostra()
        self._actualitza_peu("    ✔ " + t("v_desat"))
        return True

    def desa_com(self):
        cami = self.actual()
        if not cami:
            return
        import editor
        from PyQt6.QtWidgets import QFileDialog
        base, ext = os.path.splitext(cami)
        filtre = "JPEG (*.jpg);;PNG (*.png);;WebP (*.webp);;BMP (*.bmp);;TIFF (*.tif)"
        nou, filt = QFileDialog.getSaveFileName(self, t("ed_desa_com"), base + "_2" + ext, filtre)
        if not nou:
            return
        if not os.path.splitext(nou)[1]:
            nou += "." + filt.split("*.")[1].rstrip(")")
        qualitat = config.get("qualitat_jpeg")
        if editor.FORMATS_DESA.get(os.path.splitext(nou)[1][1:].lower()) in ("JPEG", "WEBP"):
            d = editor.DialegQualitat(self)
            if not d.exec():
                return
            qualitat = d.sl.value()
            config.set("qualitat_jpeg", qualitat)
        try:
            im = self.edicio if self.edicio is not None else IM.obre_pil(cami)
            editor.desa(im, nou, qualitat, original=cami)
        except Exception as e:
            QMessageBox.warning(self, "Xoriguer Fotos", t("e_no_desat") + f"\n{e}")
            return
        self.desat.emit(os.path.normpath(nou))
        self._actualitza_peu("    ✔ " + t("v_desat") + ": " + os.path.basename(nou))

    def _pot_sortir(self):
        """Si hi ha canvis sense desar, pregunta què fer. Retorna False si cal quedar-s'hi."""
        if not self.modificat:
            return True
        r = QMessageBox.question(self, "Xoriguer Fotos", t("p_desa_canvis_foto", nom=os.path.basename(self.actual())),
                                 QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                                 QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Save)
        if r == QMessageBox.StandardButton.Save:
            return self.desa()
        if r == QMessageBox.StandardButton.Discard:
            self._reinicia_edicio()
            return True
        return False

    def recarrega(self, cami=None):
        if cami is None or cami is False:
            cami = self.actual()
        if cami:
            self.memoria.oblida(cami)
        if cami == self.actual():
            self._reinicia_edicio()
        self.mostra()

    # ------------------------------------------------------- tecles
    def _esc(self):
        if self.llenc.mode_retall:
            self.llenc.posa_mode_retall(False)
            self._actualitza_peu()
        else:
            self.close()

    def _intro(self):
        if self.llenc.mode_retall:
            if not self.llenc.retall.isNull():
                self._aplica_retall()
        else:
            self.close()

    # ------------------------------------------------------------ fitxers
    def _edita(self):
        cami = self.actual()
        if cami and self._pot_sortir():
            if self.temporitzador.isActive():
                self.alterna_presentacio()
            self.editar.emit(cami)

    def obre(self):
        from PyQt6.QtWidgets import QFileDialog
        if not self._pot_sortir():
            return
        ext = " ".join("*." + e for e in sorted(IM.EXTENSIONS))
        f, _ = QFileDialog.getOpenFileName(self, t("a_obre_fitxer"), os.path.dirname(self.actual() or ""),
                                           f"{t('imatges')} ({ext})")
        if not f:
            return
        f = os.path.normpath(f)
        carpeta = os.path.dirname(f)
        try:
            noms = sorted((n for n in os.listdir(carpeta) if IM.es_imatge(n)), key=IM.clau_natural)
        except OSError:
            noms = [os.path.basename(f)]
        self.camins = [os.path.join(carpeta, n) for n in noms]
        self.index = self.camins.index(f) if f in self.camins else 0
        self.mostra()

    def copia_mou(self, moure):
        import shutil
        from PyQt6.QtWidgets import QFileDialog
        cami = self.actual()
        if not cami or (moure and not self._pot_sortir()):
            return
        d = QFileDialog.getExistingDirectory(self, t("a_mou_a" if moure else "a_copia_a"), os.path.dirname(cami))
        if not d or os.path.normpath(d) == os.path.dirname(cami):
            return
        desti = os.path.join(d, os.path.basename(cami))
        base, ext = os.path.splitext(desti)
        n = 2
        while os.path.exists(desti):
            desti = f"{base} ({n}){ext}"
            n += 1
        try:
            if moure:
                shutil.move(cami, desti)
            else:
                shutil.copy2(cami, desti)
        except OSError as e:
            QMessageBox.warning(self, "Xoriguer Fotos", str(e))
            return
        if moure:
            self._treu_actual(cami)
        else:
            self._actualitza_peu("    ✔ " + t("s_fet_n", n=1))

    def _treu_actual(self, cami):
        self._reinicia_edicio()
        self.memoria.oblida(cami)
        self.eliminada.emit(cami)
        del self.camins[self.index]
        if not self.camins:
            self.close()
            return
        self.index = min(self.index, len(self.camins) - 1)
        self.mostra()

    def reanomena(self):
        from PyQt6.QtWidgets import QInputDialog
        cami = self.actual()
        if not cami or not self._pot_sortir():
            return
        nom, ext = os.path.splitext(os.path.basename(cami))
        nou, ok = QInputDialog.getText(self, t("a_reanomena"), t("p_nou_nom"), text=nom)
        nou = nou.strip()
        if not ok or not nou or nou == nom:
            return
        if os.path.splitext(nou)[1].lower() != ext.lower():
            nou += ext
        desti = os.path.join(os.path.dirname(cami), nou)
        if os.path.exists(desti):
            QMessageBox.warning(self, "Xoriguer Fotos", t("e_ja_existeix", nom=nou))
            return
        try:
            os.rename(cami, desti)
        except OSError as e:
            QMessageBox.warning(self, "Xoriguer Fotos", str(e))
            return
        self.memoria.oblida(cami)
        self.camins[self.index] = desti
        self.canvi_fitxers.emit()
        self.mostra()

    def fons_escriptori(self):
        import ctypes
        cami = self.actual()
        if cami:
            ok = ctypes.windll.user32.SystemParametersInfoW(20, 0, cami, 3)
            self._actualitza_peu("    ✔ " + t("s_fons_ok") if ok else "    " + t("e_fons"))

    def explorador(self):
        import subprocess
        cami = self.actual()
        if cami:
            subprocess.Popen(["explorer", "/select,", cami])

    def imprimeix(self):
        if self.llenc.img.isNull():
            return
        from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
        pr = QPrinter(QPrinter.PrinterMode.HighResolution)
        img = self.llenc.img
        if img.width() > img.height():
            from PyQt6.QtGui import QPageLayout
            pr.setPageOrientation(QPageLayout.Orientation.Landscape)
        if QPrintDialog(pr, self).exec():
            p = QPainter(pr)
            r = p.viewport()
            mida = img.size().scaled(r.size(), Qt.AspectRatioMode.KeepAspectRatio)
            p.setViewport(r.x() + (r.width() - mida.width()) // 2, r.y() + (r.height() - mida.height()) // 2,
                          mida.width(), mida.height())
            p.setWindow(img.rect())
            p.drawImage(0, 0, img)
            p.end()

    def alterna_presentacio(self):
        if self.temporitzador.isActive():
            self.temporitzador.stop()
        else:
            self.temporitzador.start(int(config.get("segons_presentacio") * 1000))
            if not self.isFullScreen():
                self.showFullScreen()
        self._actualitza_peu()

    def alterna_info(self):
        if self.pinf.isVisible() and self.pinf.fixat:
            self.pinf.fixat = False
            self.pinf.hide()
        else:
            self.pinf.fixat = True
            self._omple_info()
            self._mostra_panell(self.pinf)

    def _omple_info(self):
        cami = self.actual()
        if cami:
            self.pinf.omple(cami, self.llenc.img, self.index + 1, len(self.camins))
            self._colloca()

    def copia(self):
        if not self.llenc.img.isNull():
            QGuiApplication.clipboard().setImage(self.llenc.img)
            self._actualitza_peu("    ✔ " + t("s_copiada"))

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
        self._treu_actual(cami)

    def alterna_pantalla(self):
        if self.isFullScreen():
            self.showMaximized()
        else:
            self.showFullScreen()

    def _surt(self):
        if self._pot_sortir():
            self.surt.emit()
            self.close()

    # ------------------------------------------------- menú del botó dret
    def contextMenuEvent(self, ev):
        from PyQt6.QtWidgets import QMenu
        m = QMenu(self)

        def afegeix(menu, text, tecla, f, icona=None, actiu=True, mirall=False):
            a = menu.addAction(E.icona(icona, mida=16, mirall=mirall) if icona else E.icona(" ", mida=16),
                               text + (f"\t{tecla}" if tecla else ""))
            a.setEnabled(actiu)
            a.triggered.connect(lambda *_: f())
            return a

        hi_ha = not self.llenc.img.isNull()
        afegeix(m, t("vm_miniatures"), "Enter", self.close, "foto")
        afegeix(m, t("v_presentacio"), "S", self.alterna_presentacio, "presentacio")
        m.addSeparator()
        afegeix(m, t("pe_obre") + "…", "Ctrl+O", self.obre, "carpeta")
        afegeix(m, t("ed_desa"), "Ctrl+S", self.desa, "desa", self.modificat)
        afegeix(m, t("ed_desa_com") + "…", "Ctrl+Shift+S", self.desa_com, "desacom", hi_ha)
        afegeix(m, t("vm_recarrega"), "Shift+R", self.recarrega, "refresca")
        afegeix(m, t("a_fons"), "", self.fons_escriptori, "fons", hi_ha)
        m.addSeparator()
        afegeix(m, t("a_explorador"), "W", self.explorador)
        sm = m.addMenu(E.icona("edita", mida=16), t("vm_edita"))
        afegeix(sm, t("pe_editor"), "E", self._edita, "edita")
        sm.addSeparator()
        afegeix(sm, t("v_gira_e"), "L", lambda: self.gira(-90), "gira", hi_ha, True)
        afegeix(sm, t("v_gira_d"), "R", lambda: self.gira(90), "gira", hi_ha)
        afegeix(sm, t("ed_volteja_h"), "H", self.mirall_h, "volteja", hi_ha)
        afegeix(sm, t("ed_volteja_v"), "V", self.mirall_v, "volteja", hi_ha)
        afegeix(sm, t("ed_mida") + "…", "Ctrl+R", self.canvia_mida, "mida", hi_ha)
        afegeix(sm, t("ed_retalla"), "X", self.retalla, "retalla", hi_ha)
        sm.addSeparator()
        afegeix(sm, t("ed_desfes"), "Ctrl+Z", self.desfes, "desfes", bool(self.desfer))
        afegeix(sm, t("ed_refes"), "Ctrl+Y", self.refes, "refes", bool(self.refer))
        sm = m.addMenu(E.icona("ajustos", mida=16), t("pe_colors"))
        afegeix(sm, t("ef_auto"), "Ctrl+Shift+B", lambda: self.efecte("auto"), None, hi_ha)
        afegeix(sm, t("pe_llum") + "…", "Ctrl+T", self.ajusta_llum, "ajustos", hi_ha)
        for k in ("equalitza", "bn", "sepia", "negatiu"):
            afegeix(sm, t("ef_" + k), "", lambda k=k: self.efecte(k), None, hi_ha)
        sm = m.addMenu(E.icona(" ", mida=16), t("ed_efectes"))
        for k in ("enfoca", "difumina", "vinyeta"):
            afegeix(sm, t("ef_" + k), "", lambda k=k: self.efecte(k), None, hi_ha)
        m.addSeparator()
        sm = m.addMenu(E.icona("seguent", mida=16), t("vm_navega"))
        afegeix(sm, t("vm_primera"), "Home", lambda: self.ves(0), "inici")
        afegeix(sm, t("v_anterior"), "←", lambda: self.mou(-1), "anterior")
        afegeix(sm, t("v_seguent"), "→", lambda: self.mou(1), "seguent")
        afegeix(sm, t("vm_ultima"), "End", lambda: self.ves(len(self.camins) - 1))
        sm = m.addMenu(E.icona("meszoom", mida=16), "Zoom")
        afegeix(sm, t("v_ajusta"), "F", self.llenc.posa_ajusta, "ajusta")
        afegeix(sm, t("v_100"), "1", lambda: self.llenc.posa_zoom(1.0))
        afegeix(sm, t("v_mes_zoom"), "+", lambda: self.llenc.zoom_pas(1), "meszoom")
        afegeix(sm, t("v_menys_zoom"), "−", lambda: self.llenc.zoom_pas(-1), "menyszoom")
        afegeix(sm, t("v_pantalla"), "F11", self.alterna_pantalla, "pantalla")
        m.addSeparator()
        afegeix(m, t("a_copia_a") + "…", "C", lambda: self.copia_mou(False), "copia")
        afegeix(m, t("a_mou_a") + "…", "M", lambda: self.copia_mou(True), "mou")
        afegeix(m, t("pe_imprimeix") + "…", "Ctrl+P", self.imprimeix, None, hi_ha)
        m.addSeparator()
        afegeix(m, t("v_copia"), "Ctrl+C", self.copia, None, hi_ha)
        afegeix(m, t("v_elimina"), "Supr", self.elimina, "elimina")
        afegeix(m, t("a_reanomena"), "F2", self.reanomena, "reanomena")
        m.addSeparator()
        afegeix(m, t("v_info"), "I", self.alterna_info, "info")
        m.addSeparator()
        afegeix(m, t("vm_surt"), "Alt+X", self._surt, "tanca")
        m.exec(ev.globalPos())

    def closeEvent(self, ev):
        if not self._pot_sortir():
            ev.ignore()
            return
        self.temporitzador.stop()
        self.tancat.emit(self.actual() or "")
        super().closeEvent(ev)
