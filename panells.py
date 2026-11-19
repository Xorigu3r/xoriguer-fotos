"""Panells laterals del visor: edició ràpida (esquerra), informació i histograma (dreta), diàleg de llum i colors."""

import os
from datetime import datetime

from PIL import Image

from PyQt6.QtCore import QPointF, Qt, QTimer
from PyQt6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
                             QScrollArea, QSlider, QVBoxLayout, QWidget)

import estil as E
import imatges as IM
from i18n import t

ESTIL_PANELL = f"""
QFrame#panell {{ background: rgba(39,53,74,246); border: 1px solid {E.LINE}; }}
QLabel#seccio {{ background: {E.BG3}; color: {E.OR1}; font-weight: 600; padding: 4px 8px; }}
QPushButton#enllac {{ background: transparent; border: none; text-align: left; padding: 3px 6px; color: {E.CREAM}; }}
QPushButton#enllac:hover {{ background: {E.BG3}; color: {E.OR1}; border-radius: 4px; }}
QPushButton#enllac:disabled {{ color: #6f7a8a; }}
QLabel#drecera {{ color: {E.SOFT}; padding-right: 6px; }}
QLabel#clau {{ color: {E.OR1}; }}
"""


class _Panell(QFrame):
    """Base: un marc semitransparent amb contingut que es pot desplaçar."""

    def __init__(self, parent, amplada):
        super().__init__(parent)
        self.setObjectName("panell")
        self.setStyleSheet(ESTIL_PANELL)
        self.fixat = False
        self.amplada = amplada
        sc = QScrollArea(self)
        sc.setWidgetResizable(True)
        sc.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sc.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; }")
        self.cos = QWidget()
        self.lay = QVBoxLayout(self.cos)
        self.lay.setContentsMargins(6, 6, 6, 6)
        self.lay.setSpacing(2)
        sc.setWidget(self.cos)
        l = QVBoxLayout(self)
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(sc)
        self.hide()

    def alcada_ideal(self):
        return self.cos.sizeHint().height() + 4

    def seccio(self, text):
        lbl = QLabel(text, objectName="seccio")
        self.lay.addSpacing(4)
        self.lay.addWidget(lbl)
        return lbl

    def leaveEvent(self, ev):
        if not self.fixat:
            QTimer.singleShot(250, self._potser_amaga)
        super().leaveEvent(ev)

    def _potser_amaga(self):
        if not self.fixat and not self.underMouse():
            self.hide()


class PanellEdicio(_Panell):
    """Com el panell esquerre de FastStone: totes les accions d'edició a l'abast."""

    def __init__(self, visor):
        super().__init__(visor, 300)
        v = visor
        self.botons = {}
        self.seccio(t("pe_fitxer"))
        self._files([(t("pe_obre"), "Ctrl+O", v.obre), (t("ed_desa"), "Ctrl+S", v.desa, "desa"),
                     (t("ed_desa_com") + "…", "Ctrl+Shift+S", v.desa_com), (t("v_copia"), "Ctrl+C", v.copia),
                     (t("pe_imprimeix") + "…", "Ctrl+P", v.imprimeix), (t("v_presentacio"), "S", v.alterna_presentacio),
                     (t("pe_editor"), "E", v._edita)])
        self.seccio(t("pe_gira_mida"))
        self._fila(t("pe_gira") + ":", [(t("pe_esquerra"), lambda: v.gira(-90)), (t("pe_dreta"), lambda: v.gira(90))], "L, R")
        self._fila(t("pe_mirall") + ":", [(t("pe_horitzontal"), v.mirall_h), (t("pe_vertical"), v.mirall_v)], "H, V")
        self._files([(t("ed_mida") + "…", "Ctrl+R", v.canvia_mida), (t("ed_retalla"), "X", v.retalla)])
        self.seccio(t("pe_colors"))
        self._files([(t("ef_auto"), "Ctrl+Shift+B", lambda: v.efecte("auto")),
                     (t("pe_llum") + "…", "Ctrl+T", v.ajusta_llum),
                     (t("ef_equalitza"), "", lambda: v.efecte("equalitza"))])
        self._fila("", [(t("ef_bn"), lambda: v.efecte("bn")), (t("ef_sepia"), lambda: v.efecte("sepia")),
                        (t("ef_negatiu"), lambda: v.efecte("negatiu"))], "")
        self.seccio(t("ed_efectes"))
        self._fila("", [(t("ef_enfoca"), lambda: v.efecte("enfoca")), (t("ef_difumina"), lambda: v.efecte("difumina")),
                        (t("ef_vinyeta"), lambda: v.efecte("vinyeta"))], "")
        self.lay.addSpacing(6)
        self._files([(t("ed_desfes"), "Ctrl+Z", v.desfes, "desfes"), (t("ed_refes"), "Ctrl+Y", v.refes, "refes")])
        self.lay.addStretch()
        self.actualitza(False, False, False)

    def _files(self, items):
        g = QGridLayout()
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(4)
        g.setVerticalSpacing(0)
        for i, it in enumerate(items):
            text, tecla, f = it[:3]
            b = QPushButton(text, objectName="enllac", cursor=Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.clicked.connect(lambda _, f=f: f())
            g.addWidget(b, i, 0)
            g.addWidget(QLabel(tecla, objectName="drecera", alignment=Qt.AlignmentFlag.AlignRight), i, 1)
            if len(it) > 3:
                self.botons[it[3]] = b
        g.setColumnStretch(0, 1)
        self.lay.addLayout(g)

    def _fila(self, etiqueta, items, tecla):
        h = QHBoxLayout()
        h.setContentsMargins(6 if etiqueta else 0, 0, 0, 0)
        h.setSpacing(0)
        if etiqueta:
            h.addWidget(QLabel(etiqueta, objectName="drecera"))
        for text, f in items:
            b = QPushButton(text, objectName="enllac", cursor=Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.clicked.connect(lambda _, f=f: f())
            h.addWidget(b)
        h.addStretch()
        if tecla:
            h.addWidget(QLabel(tecla, objectName="drecera"))
        self.lay.addLayout(h)

    def actualitza(self, modificat, pot_desfer, pot_refer):
        self.botons["desa"].setEnabled(modificat)
        self.botons["desfes"].setEnabled(pot_desfer)
        self.botons["refes"].setEnabled(pot_refer)


class Histograma(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(120)
        self.canals = None

    def posa_imatge(self, img):
        self.canals = None
        if img is not None and not img.isNull():
            petita = img.scaled(320, 320, Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.FastTransformation).convertToFormat(QImage.Format.Format_RGB888)
            dades = petita.constBits().asstring(petita.sizeInBytes())
            im = Image.frombytes("RGB", (petita.width(), petita.height()), dades, "raw", "RGB", petita.bytesPerLine())
            h = im.histogram()
            lum = im.convert("L").histogram()
            self.canals = [lum, h[0:256], h[256:512], h[512:768]]
        self.update()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)
        p.fillRect(r, QColor(E.BG_B))
        p.setPen(QPen(QColor(E.LINE), 1))
        p.drawRect(r)
        if not self.canals:
            return
        maxim = max(max(c[2:254]) for c in self.canals) or 1
        colors = [QColor(246, 239, 226, 90), QColor(240, 80, 70, 200), QColor(90, 200, 110, 200), QColor(80, 150, 240, 220)]
        for i, (c, col) in enumerate(zip(self.canals, colors)):
            cami = QPainterPath()
            cami.moveTo(r.left(), r.bottom())
            for x in range(256):
                cami.lineTo(QPointF(r.left() + x / 255 * r.width(), r.bottom() - min(1.0, c[x] / maxim) * (r.height() - 4)))
            if i == 0:
                cami.lineTo(r.right(), r.bottom())
                p.fillPath(cami, col)
            else:
                p.setPen(QPen(col, 1.2))
                p.drawPath(cami)


class PanellInfo(_Panell):
    """Panell dret: fitxer, atributs, EXIF i histograma."""

    def __init__(self, visor):
        super().__init__(visor, 380)
        self.seccio(t("pi_fitxer"))
        self.lbl_fitxer = QLabel(wordWrap=True, textFormat=Qt.TextFormat.RichText)
        self.lay.addWidget(self.lbl_fitxer)
        self.seccio("EXIF")
        self.lbl_exif = QLabel(wordWrap=True, textFormat=Qt.TextFormat.RichText, openExternalLinks=True)
        self.lay.addWidget(self.lbl_exif)
        self.seccio(t("pi_histograma"))
        self.hist = Histograma()
        self.lay.addWidget(self.hist)
        self.lay.addStretch()

    @staticmethod
    def _taula(files):
        return "<table cellspacing='2'>" + "".join(
            f"<tr><td width='118' style='color:{E.OR1}; padding-right:8px' nowrap>{a}</td><td>{b}</td></tr>" for a, b in files) + "</table>"

    def omple(self, cami, img, index, total):
        try:
            st = os.stat(cami)
            pes = f"{st.st_size / 1024 / 1024:.2f} MB" if st.st_size > 1024 * 1024 else f"{st.st_size / 1024:.0f} KB"
            data = datetime.fromtimestamp(st.st_mtime).strftime("%d/%m/%Y %H:%M:%S")
        except OSError:
            pes = data = "—"
        ex = IM.info_exif(cami)
        w, h = (img.width(), img.height()) if img is not None and not img.isNull() else (0, 0)
        dpi = ex.get("dpi")
        files = [(t("i_nom"), f"{os.path.basename(cami)}  [{index} / {total}]"),
                 (t("pi_ubicacio"), os.path.dirname(cami).replace(os.sep, os.sep + "​")),
                 (t("pi_tipus"), ex.get("format") or os.path.splitext(cami)[1][1:].upper()),
                 (t("pi_pes"), pes), (t("pi_data"), data),
                 (t("i_mida"), f"{w} × {h} px  ({w * h / 1e6:.2f} MP)")]
        if dpi:
            try:
                files.append(("DPI", f"{round(float(dpi[0]))} × {round(float(dpi[1]))}"))
            except (TypeError, ValueError, IndexError):
                pass
        self.lbl_fitxer.setText(self._taula(files))

        prog = ex.get("programa")
        gps = ex.get("gps")
        enllac = ""
        if gps:
            lat, lon = gps
            url = f"https://www.openstreetmap.org/?mlat={lat:.6f}&mlon={lon:.6f}#map=16/{lat:.6f}/{lon:.6f}"
            enllac = f"{lat:.5f}, {lon:.5f}<br><a style='color:{E.OR1}' href='{url}'>{t('pi_mapa')}</a>"
        exif = [(t("pi_marca"), ex.get("marca", "")), (t("pi_model"), ex.get("model", "")),
                (t("pi_software"), ex.get("software", "")), (t("i_data"), ex.get("data", "")),
                (t("i_exposicio"), ex.get("exposicio", "")), (t("i_diafragma"), ex.get("diafragma", "")),
                ("ISO", ex.get("iso", "").replace("ISO ", "")),
                (t("pi_programa"), t(f"prog_{prog}") if prog and 1 <= prog <= 8 else ""),
                (t("pi_compensacio"), ex.get("compensacio", "")),
                (t("pi_flash"), (t("pi_si") if ex["flash"] else t("pi_no")) if "flash" in ex else ""),
                (t("i_focal"), ex.get("focal", "")), (t("pi_focal35"), ex.get("focal35", "")),
                (t("i_objectiu"), ex.get("objectiu", "")), ("GPS", enllac)]
        if not any(b for _, b in exif):
            self.lbl_exif.setText(f"<span style='color:{E.SOFT}'>{t('pi_sense_exif')}</span>")
        else:
            self.lbl_exif.setText(self._taula([(a, b or f"<span style='color:{E.LINE}'>—</span>") for a, b in exif]))
        self.hist.posa_imatge(img)


class DialegAjustos(QDialog):
    """Llum i colors amb previsualització en directe sobre el visor."""
    AJUSTOS = [("brillantor", -100, 100), ("contrast", -100, 100), ("saturacio", -100, 100),
               ("gamma", -100, 100), ("temperatura", -100, 100), ("nitidesa", 0, 100)]

    def __init__(self, parent, en_canvi):
        super().__init__(parent)
        self.setWindowTitle(t("pe_llum"))
        self.en_canvi = en_canvi
        g = QGridLayout(self)
        self.sliders = {}
        for i, (clau, mn, mx) in enumerate(self.AJUSTOS):
            s = QSlider(Qt.Orientation.Horizontal, minimum=mn, maximum=mx, value=0)
            s.setMinimumWidth(240)
            val = QLabel("0", minimumWidth=34, alignment=Qt.AlignmentFlag.AlignRight)
            s.valueChanged.connect(lambda v, l=val: (l.setText(str(v)), self._temps.start(30)))
            g.addWidget(QLabel(t("aj_" + clau)), i, 0)
            g.addWidget(s, i, 1)
            g.addWidget(val, i, 2)
            self.sliders[clau] = s
        b_reset = QPushButton(t("ed_restableix"))
        b_reset.clicked.connect(lambda: [s.setValue(0) for s in self.sliders.values()])
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText(t("ed_aplica"))
        bb.button(QDialogButtonBox.StandardButton.Ok).setObjectName("primari")
        bb.button(QDialogButtonBox.StandardButton.Cancel).setText(t("cancel·la"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        fila = QHBoxLayout()
        fila.addWidget(b_reset)
        fila.addStretch()
        fila.addWidget(bb)
        g.addLayout(fila, len(self.AJUSTOS), 0, 1, 3)
        self._temps = QTimer(self, singleShot=True, timeout=lambda: self.en_canvi(self.valors()))

    def valors(self):
        return {k: s.value() for k, s in self.sliders.items()}
