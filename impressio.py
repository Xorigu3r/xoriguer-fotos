"""Impressió amb previsualització: impressora, paper, marges, mida, posició, orientació, còpies i gamma."""

import os

from PIL import Image

from PyQt6.QtCore import QMarginsF, QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QIcon, QImage, QPageLayout, QPainter, QPen, QPixmap, QTransform
from PyQt6.QtPrintSupport import QPageSetupDialog, QPrinter, QPrinterInfo
from PyQt6.QtWidgets import (QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog,
                             QGridLayout, QGroupBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox,
                             QPushButton, QRadioButton, QSpinBox, QToolButton, QVBoxLayout, QWidget)

import config
import estil as E
import imatges as IM
from i18n import t

PER_DEFECTE = {"marges": [5.0, 5.0, 5.0, 5.0], "mida": "redueix", "esp_w": 100.0, "esp_h": 150.0, "proporcio": True,
               "posicio": "mc", "orientacio": "vertical", "rotacio_auto": True, "unitats": "cm", "copies": 1,
               "gamma": 1.0, "nom": False, "impressora": ""}
POSICIONS = ["tl", "tc", "tr", "ml", "mc", "mr", "bl", "bc", "br"]
FACTOR = {"cm": 10.0, "in": 25.4}          # mm per unitat


def dpi_de(cami, img=None):
    """Resolució de la foto (per a «mida original»). Si no en té o és absurda, 96."""
    try:
        with Image.open(cami) as im:
            d = im.info.get("dpi")
            if d and float(d[0]) >= 30:
                return float(d[0])
    except Exception:
        pass
    if img is not None and not img.isNull() and img.dotsPerMeterX() > 1200:
        return img.dotsPerMeterX() * 0.0254
    return 96.0


def aplica_gamma(img, g):
    if abs(g - 1.0) < 0.01 or img.isNull():
        return img
    lut = [min(255, round(255 * (i / 255) ** (1 / g))) for i in range(256)]
    im = IM.qimage_a_pil(img)
    alfa = im.getchannel("A")
    out = im.convert("RGB").point(lut * 3)
    out.putalpha(alfa)
    return IM.pil_a_qimage(out)


def disposa(pagina, w_px, h_px, dpi, o):
    """Calcula on va la foto dins del paper.
    pagina: (amplada, alçada) en mm. Retorna (QRectF en mm, gira 90°?, àrea útil QRectF)."""
    pw, ph = pagina
    m_dalt, m_baix, m_esq, m_dre = o["marges"]
    util = QRectF(m_esq, m_dalt, max(1.0, pw - m_esq - m_dre), max(1.0, ph - m_dalt - m_baix))
    gira = bool(o["rotacio_auto"]) and w_px and h_px and ((w_px > h_px) != (util.width() > util.height())) \
        and abs(w_px - h_px) > 2
    iw, ih = (h_px, w_px) if gira else (w_px, h_px)
    if not iw or not ih:
        return QRectF(), False, util
    mode = o["mida"]
    if mode == "original":
        w, h = iw / dpi * 25.4, ih / dpi * 25.4
    elif mode == "especificada":
        w, h = o["esp_w"], o["esp_h"]
        if o["proporcio"]:
            s = min(w / iw, h / ih)
            w, h = iw * s, ih * s
    else:
        s = min(util.width() / iw, util.height() / ih)
        if mode == "redueix":
            s = min(s, 25.4 / dpi)       # no l'amplia més enllà de la mida original
        w, h = iw * s, ih * s
    pos = o["posicio"]
    x = {"l": util.left(), "c": util.left() + (util.width() - w) / 2, "r": util.right() - w}[pos[1]]
    y = {"t": util.top(), "m": util.top() + (util.height() - h) / 2, "b": util.bottom() - h}[pos[0]]
    return QRectF(x, y, w, h), gira, util


class _Element:
    def __init__(self, cami, img=None):
        self.cami = cami
        self._img = img                  # imatge ja retocada (des del visor) o None
        self.mini = (img.scaled(160, 160, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                     if img is not None and not img.isNull() else IM.carrega_qimage(cami, 160))
        if img is not None and not img.isNull():
            self.w, self.h = img.width(), img.height()
        else:
            self.w, self.h = IM.mida_imatge(cami)
        self.dpi = dpi_de(cami, img)
        self._prev = None

    def previsualitzacio(self):
        if self._prev is None:
            self._prev = (self._img.scaled(900, 900, Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation)
                          if self._img is not None else IM.carrega_qimage(self.cami, 900))
        return self._prev

    def sencera(self):
        return self._img if self._img is not None else IM.carrega_qimage(self.cami)


class Previsualitzacio(QWidget):
    def __init__(self, dialeg):
        super().__init__()
        self.d = dialeg
        self.setMinimumSize(360, 420)

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.fillRect(self.rect(), QColor(E.BG_B))
        el = self.d.actual()
        pw, ph = self.d.mida_pagina()
        marge = 24
        s = min((self.width() - 2 * marge) / pw, (self.height() - 2 * marge) / ph)
        full = QRectF((self.width() - pw * s) / 2, (self.height() - ph * s) / 2, pw * s, ph * s)
        p.fillRect(full.translated(5, 5), QColor(0, 0, 0, 90))
        p.fillRect(full, QColor("#FFFFFF"))
        if el is None:
            return
        o = self.d.opcions()
        r, gira, util = disposa((pw, ph), el.w, el.h, el.dpi, o)
        p.setPen(QPen(QColor(180, 190, 205), 1, Qt.PenStyle.DashLine))
        p.drawRect(QRectF(full.x() + util.x() * s, full.y() + util.y() * s, util.width() * s, util.height() * s))
        if r.isEmpty():
            return
        img = el.previsualitzacio()
        if gira:
            img = img.transformed(QTransform().rotate(90))
        img = aplica_gamma(img, o["gamma"])
        desti = QRectF(full.x() + r.x() * s, full.y() + r.y() * s, r.width() * s, r.height() * s)
        p.save()
        p.setClipRect(full)
        p.drawImage(desti, img)
        p.restore()
        if o["nom"]:
            p.setPen(QColor(60, 60, 60))
            f = p.font()
            f.setPixelSize(max(7, int(3.2 * s)))
            p.setFont(f)
            p.drawText(QRectF(desti.x(), desti.bottom() + 1.5 * s, desti.width(), 5 * s),
                       Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, os.path.basename(el.cami))


class DialegImpressio(QDialog):
    def __init__(self, elements, parent=None):
        """elements: llista de camins o de tuples (camí, QImage ja retocada)."""
        super().__init__(parent)
        self.setWindowTitle(t("im_titol"))
        self.setWindowIcon(E.icona_app())
        self.elements = [(_Element(*e) if isinstance(e, tuple) else _Element(e)) for e in elements]
        self.o = dict(PER_DEFECTE)
        self.o.update(config.get("impressio") or {})
        self.printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        self._bloc = False

        arrel = QVBoxLayout(self)
        # ---- llista de fotos
        g = QGroupBox(t("im_fotos"))
        gl = QHBoxLayout(g)
        self.llista = QListWidget()
        self.llista.setViewMode(QListWidget.ViewMode.IconMode)
        self.llista.setFlow(QListWidget.Flow.LeftToRight)
        self.llista.setWrapping(False)
        self.llista.setIconSize(QSize(96, 96))
        self.llista.setFixedHeight(140)
        self.llista.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.llista.currentRowChanged.connect(lambda _: self._refresca())
        gl.addWidget(self.llista, 1)
        col = QVBoxLayout()
        b = QPushButton(t("im_afegeix") + "…")
        b.clicked.connect(self._afegeix)
        col.addWidget(b)
        b = QPushButton(t("im_treu"))
        b.clicked.connect(self._treu)
        col.addWidget(b)
        col.addStretch()
        gl.addLayout(col)
        arrel.addWidget(g)

        cos = QHBoxLayout()
        esq = QGridLayout()
        arrel.addLayout(cos, 1)
        cos.addLayout(esq, 0)

        # ---- impressora i paper
        g = QGroupBox(t("im_impressora"))
        gl = QVBoxLayout(g)
        fila = QHBoxLayout()
        self.c_imp = QComboBox()
        self._omple_impressores()
        self.c_imp.currentIndexChanged.connect(lambda _: self._canvia_impressora(self.c_imp.currentData()))
        b = QPushButton(t("im_paper") + "…")
        b.clicked.connect(self._configura_pagina)
        fila.addWidget(self.c_imp, 1)
        fila.addWidget(b)
        gl.addLayout(fila)
        self.lbl_paper = QLabel(objectName="suau")
        gl.addWidget(self.lbl_paper)
        esq.addWidget(g, 0, 0, 1, 2)

        # ---- marges
        g = QGroupBox(t("im_marges"))
        gm = QGridLayout(g)
        self.s_marges = []
        for nom, (fila_, col_) in zip(("im_dalt", "im_baix", "im_esquerra", "im_dreta"), ((0, 1), (2, 1), (1, 0), (1, 2))):
            caixa = QVBoxLayout()
            sp = QDoubleSpinBox(decimals=2, maximum=999, singleStep=0.1)
            sp.valueChanged.connect(self._canvi)
            caixa.addWidget(sp)
            caixa.addWidget(QLabel(t(nom), alignment=Qt.AlignmentFlag.AlignCenter, objectName="suau"))
            gm.addLayout(caixa, fila_, col_)
            self.s_marges.append(sp)
        esq.addWidget(g, 1, 0)

        # ---- posició
        g = QGroupBox(t("tx_posicio"))
        gp = QGridLayout(g)
        self.g_pos = QButtonGroup(self)
        for i, k in enumerate(POSICIONS):
            b = QToolButton(checkable=True)
            b.setFixedSize(34, 34)
            b.setToolTip(t("pos_" + k))
            b.setText("▣" if k == "mc" else "■")
            b.setStyleSheet(f"QToolButton {{ color: {E.SOFT}; }} QToolButton:checked {{ color: {E.OR1}; }}")
            self.g_pos.addButton(b, i)
            gp.addWidget(b, i // 3, i % 3)
        self.g_pos.idClicked.connect(self._canvi)
        esq.addWidget(g, 1, 1)

        # ---- mida
        g = QGroupBox(t("im_mida"))
        gs = QGridLayout(g)
        self.g_mida = QButtonGroup(self)
        for i, k in enumerate(("original", "encaixa", "redueix", "especificada")):
            r = QRadioButton(t("im_" + k))
            self.g_mida.addButton(r, i)
            gs.addWidget(r, i, 0, 1, 4)
        self.g_mida.idClicked.connect(self._canvi)
        self.s_w = QDoubleSpinBox(decimals=2, maximum=9999, singleStep=0.5)
        self.s_h = QDoubleSpinBox(decimals=2, maximum=9999, singleStep=0.5)
        self.s_w.valueChanged.connect(lambda v: self._esp_canviat("w"))
        self.s_h.valueChanged.connect(lambda v: self._esp_canviat("h"))
        self.ch_prop = QCheckBox(t("ed_mantén_proporcio"))
        self.ch_prop.toggled.connect(self._canvi)
        gs.addWidget(self.s_w, 4, 1)
        gs.addWidget(QLabel("×"), 4, 2)
        gs.addWidget(self.s_h, 4, 3)
        gs.addWidget(self.ch_prop, 5, 1, 1, 3)
        esq.addWidget(g, 2, 0)

        # ---- orientació i unitats
        g = QGroupBox(t("im_orientacio"))
        go = QVBoxLayout(g)
        self.r_vert = QRadioButton(t("im_vertical"))
        self.r_hor = QRadioButton(t("im_horitzontal"))
        self.ch_rot = QCheckBox(t("im_rotacio_auto"))
        for w in (self.r_vert, self.r_hor):
            w.toggled.connect(self._canvia_orientacio)
            go.addWidget(w)
        self.ch_rot.toggled.connect(self._canvi)
        go.addWidget(self.ch_rot)
        fila = QHBoxLayout()
        fila.addWidget(QLabel(t("im_unitats")))
        self.c_unit = QComboBox()
        self.c_unit.addItem("cm", "cm")
        self.c_unit.addItem(t("im_polzades"), "in")
        self.c_unit.currentIndexChanged.connect(self._canvia_unitats)
        fila.addWidget(self.c_unit)
        go.addLayout(fila)
        esq.addWidget(g, 2, 1)

        # ---- còpies, gamma, nom
        g = QGroupBox(t("im_altres"))
        ga = QGridLayout(g)
        ga.addWidget(QLabel(t("im_copies")), 0, 0)
        self.s_copies = QSpinBox(minimum=1, maximum=999)
        self.s_copies.valueChanged.connect(self._canvi)
        ga.addWidget(self.s_copies, 0, 1)
        ga.addWidget(QLabel(t("im_gamma")), 0, 2)
        self.s_gamma = QDoubleSpinBox(decimals=2, minimum=0.3, maximum=3.0, singleStep=0.05)
        self.s_gamma.valueChanged.connect(self._canvi)
        ga.addWidget(self.s_gamma, 0, 3)
        self.ch_nom = QCheckBox(t("im_nom"))
        self.ch_nom.toggled.connect(self._canvi)
        ga.addWidget(self.ch_nom, 1, 0, 1, 4)
        esq.addWidget(g, 3, 0, 1, 2)

        # ---- previsualització
        g = QGroupBox(t("im_previsualitzacio"))
        gv = QVBoxLayout(g)
        self.prev = Previsualitzacio(self)
        gv.addWidget(self.prev, 1)
        self.lbl_info = QLabel(objectName="suau", alignment=Qt.AlignmentFlag.AlignCenter, wordWrap=True)
        gv.addWidget(self.lbl_info)
        cos.addWidget(g, 1)

        # ---- botons
        fila = QHBoxLayout()
        b = QPushButton(t("ed_restableix"))
        b.clicked.connect(self._restableix)
        fila.addWidget(b)
        fila.addStretch()
        self.b_imp = QPushButton(t("im_imprimeix"), objectName="primari")
        self.b_imp.clicked.connect(self.imprimeix)
        b = QPushButton(t("cancel·la"))
        b.clicked.connect(self.reject)
        fila.addWidget(self.b_imp)
        fila.addWidget(b)
        arrel.addLayout(fila)

        self._omple_llista()
        self._canvia_impressora(self.c_imp.currentData())
        self._carrega_opcions()
        self.resize(1180, 820)

    # ------------------------------------------------------------ dades
    def _u(self):
        return FACTOR[self.c_unit.currentData() or "cm"]

    def _carrega_opcions(self):
        self._bloc = True
        o = self.o
        self.c_unit.setCurrentIndex(0 if o["unitats"] == "cm" else 1)
        u = FACTOR[o["unitats"]]
        for sp, v in zip(self.s_marges, o["marges"]):
            sp.setValue(v / u)
        self.g_pos.button(POSICIONS.index(o["posicio"]) if o["posicio"] in POSICIONS else 4).setChecked(True)
        self.g_mida.button(("original", "encaixa", "redueix", "especificada").index(o["mida"])).setChecked(True)
        self.s_w.setValue(o["esp_w"] / u)
        self.s_h.setValue(o["esp_h"] / u)
        self.ch_prop.setChecked(o["proporcio"])
        (self.r_hor if o["orientacio"] == "horitzontal" else self.r_vert).setChecked(True)
        self.ch_rot.setChecked(o["rotacio_auto"])
        self.s_copies.setValue(o["copies"])
        self.s_gamma.setValue(o["gamma"])
        self.ch_nom.setChecked(o["nom"])
        self.o["_u_vell"] = u
        self._bloc = False
        self._aplica_orientacio()
        self._refresca()

    def opcions(self):
        u = self._u()
        modes = ("original", "encaixa", "redueix", "especificada")
        return {"marges": [sp.value() * u for sp in self.s_marges],
                "mida": modes[max(0, self.g_mida.checkedId())], "esp_w": self.s_w.value() * u,
                "esp_h": self.s_h.value() * u, "proporcio": self.ch_prop.isChecked(),
                "posicio": POSICIONS[max(0, self.g_pos.checkedId())],
                "orientacio": "horitzontal" if self.r_hor.isChecked() else "vertical",
                "rotacio_auto": self.ch_rot.isChecked(), "unitats": self.c_unit.currentData(),
                "copies": self.s_copies.value(), "gamma": self.s_gamma.value(), "nom": self.ch_nom.isChecked(),
                "impressora": self.c_imp.currentData() or ""}

    def mida_pagina(self):
        r = self.printer.pageLayout().fullRect(QPageLayout.Unit.Millimeter)
        return r.width(), r.height()

    def actual(self):
        i = self.llista.currentRow()
        return self.elements[i] if 0 <= i < len(self.elements) else None

    # ----------------------------------------------------------- canvis
    def _omple_llista(self):
        self.llista.clear()
        for el in self.elements:
            it = QListWidgetItem(QIcon(QPixmap.fromImage(el.mini)), os.path.basename(el.cami))
            it.setToolTip(el.cami)
            self.llista.addItem(it)
        if self.elements:
            self.llista.setCurrentRow(0)
        self.b_imp.setEnabled(bool(self.elements)) if hasattr(self, "b_imp") else None

    def _afegeix(self):
        ext = " ".join("*." + e for e in sorted(IM.EXTENSIONS))
        carpeta = os.path.dirname(self.elements[0].cami) if self.elements else ""
        fitxers, _ = QFileDialog.getOpenFileNames(self, t("im_afegeix"), carpeta, f"{t('imatges')} ({ext})")
        for f in fitxers:
            self.elements.append(_Element(os.path.normpath(f)))
        if fitxers:
            self._omple_llista()
            self.llista.setCurrentRow(len(self.elements) - 1)

    def _treu(self):
        i = self.llista.currentRow()
        if 0 <= i < len(self.elements):
            del self.elements[i]
            self._omple_llista()
            self.llista.setCurrentRow(min(i, len(self.elements) - 1))
            self._refresca()

    def _canvi(self, *_):
        if not self._bloc:
            self._refresca()

    def _esp_canviat(self, quin):
        if self._bloc:
            return
        el = self.actual()
        if self.ch_prop.isChecked() and el and el.w and el.h:
            self._bloc = True
            gira = self.ch_rot.isChecked() and ((el.w > el.h) != (self.mida_pagina()[0] > self.mida_pagina()[1]))
            iw, ih = (el.h, el.w) if gira else (el.w, el.h)
            if quin == "w":
                self.s_h.setValue(self.s_w.value() * ih / iw)
            else:
                self.s_w.setValue(self.s_h.value() * iw / ih)
            self._bloc = False
        if self.g_mida.checkedId() != 3:
            self.g_mida.button(3).setChecked(True)
        self._refresca()

    def _canvia_unitats(self):
        if self._bloc:
            return
        vell = self.o.get("_u_vell", FACTOR[self.o["unitats"]])
        nou = self._u()
        self._bloc = True
        for sp in self.s_marges + [self.s_w, self.s_h]:
            sp.setValue(sp.value() * vell / nou)
        self._bloc = False
        self.o["_u_vell"] = nou
        self._refresca()

    def _omple_impressores(self):
        """La predeterminada de Windows primer; les que estan en error (p. ex. una còpia vella WSD) al final i marcades.
        S'usa la preferida guardada només si continua existint i funciona; si no, la predeterminada."""
        defecte = QPrinterInfo.defaultPrinterName()
        infos = QPrinterInfo.availablePrinters()
        self._estat_imp = {}
        for info in infos:
            self._estat_imp[info.printerName()] = info.state() == QPrinter.PrinterState.Error if False else \
                info.state().name == "Error"
        ordre = sorted(infos, key=lambda i: (i.printerName() != defecte, self._estat_imp[i.printerName()],
                                              i.printerName().lower()))
        for info in ordre:
            nom = info.printerName()
            text = nom
            if nom == defecte:
                text += "  (" + t("im_predeterminada") + ")"
            if self._estat_imp[nom]:
                text += "  — " + t("im_no_disponible")
            self.c_imp.addItem(text, nom)
        preferida = self.o.get("impressora") or ""
        if preferida not in self._estat_imp or self._estat_imp[preferida]:
            preferida = defecte
        i = self.c_imp.findData(preferida)
        self.c_imp.setCurrentIndex(max(0, i))

    def _canvia_impressora(self, nom):
        if nom:
            self.printer.setPrinterName(nom)
        self._aplica_orientacio()
        self._refresca()

    def _aplica_orientacio(self):
        self.printer.setPageOrientation(QPageLayout.Orientation.Landscape if self.r_hor.isChecked()
                                        else QPageLayout.Orientation.Portrait)

    def _canvia_orientacio(self, actiu):
        if actiu and not self._bloc:
            self._aplica_orientacio()
            self._refresca()

    def _configura_pagina(self):
        if QPageSetupDialog(self.printer, self).exec():
            self._bloc = True
            hor = self.printer.pageLayout().orientation() == QPageLayout.Orientation.Landscape
            (self.r_hor if hor else self.r_vert).setChecked(True)
            self._bloc = False
            self._refresca()

    def _restableix(self):
        imp = self.c_imp.currentData() or ""
        self.o = dict(PER_DEFECTE)
        self.o["impressora"] = imp
        self._carrega_opcions()

    def _refresca(self):
        pw, ph = self.mida_pagina()
        u = self.c_unit.currentData() or "cm"
        f = FACTOR[u]
        nom_paper = self.printer.pageLayout().pageSize().name()
        self.lbl_paper.setText(f"{t('im_paper_txt')}: {nom_paper}  ({pw / f:.2f} × {ph / f:.2f} {u})")
        el = self.actual()
        if el:
            r, gira, _ = disposa((pw, ph), el.w, el.h, el.dpi, self.opcions())
            if not r.isEmpty():
                iw = el.h if gira else el.w
                ppp = iw / (r.width() / 25.4)
                avis = f"  ·  ⚠ {t('im_qualitat_baixa')}" if ppp < 150 else ""
                self.lbl_info.setText(t("im_pagina", i=self.llista.currentRow() + 1, n=len(self.elements)) +
                                      f"  ·  {r.width() / f:.2f} × {r.height() / f:.2f} {u}  ·  {ppp:.0f} ppp{avis}")
        else:
            self.lbl_info.setText("")
        self.prev.update()

    # --------------------------------------------------------- imprimir
    def imprimeix(self):
        if not self.elements:
            return
        o = self.opcions()
        pr = self.printer
        pr.setFullPage(True)
        pr.setCopyCount(o["copies"])
        pr.setDocName("Xoriguer Fotos")
        nom = self.c_imp.currentData() or ""
        if self._estat_imp.get(nom):
            defecte = QPrinterInfo.defaultPrinterName()
            if defecte and defecte != nom and not self._estat_imp.get(defecte):
                r = QMessageBox.question(self, t("im_titol"), t("im_en_error", nom=nom, bona=defecte))
                if r != QMessageBox.StandardButton.Yes:
                    return
                self.c_imp.setCurrentIndex(self.c_imp.findData(defecte))
                o = self.opcions()
            else:
                QMessageBox.warning(self, t("im_titol"), t("im_cap_impressora") + f"\n{nom}")
                return
        if not pr.isValid():
            QMessageBox.warning(self, t("im_titol"), t("im_cap_impressora"))
            return
        self._desa_opcions()
        try:
            self.imprimeix_a(pr, o)
        except Exception as e:
            QMessageBox.warning(self, t("im_titol"), t("im_cap_impressora") + f"\n{e}")
            return
        self.accept()

    def imprimeix_a(self, pr, o):
        from PyQt6.QtWidgets import QApplication
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        p = QPainter()
        try:
            if not p.begin(pr):
                raise RuntimeError(t("im_cap_impressora"))
            pagina = pr.pageLayout().fullRect(QPageLayout.Unit.Millimeter)
            k = pr.resolution() / 25.4      # mm -> punts de la impressora
            for n, el in enumerate(self.elements):
                if n:
                    pr.newPage()
                r, gira, _ = disposa((pagina.width(), pagina.height()), el.w, el.h, el.dpi, o)
                if r.isEmpty():
                    continue
                img = el.sencera()
                if img.isNull():
                    continue
                if gira:
                    img = img.transformed(QTransform().rotate(90))
                desti = QRectF(r.x() * k, r.y() * k, r.width() * k, r.height() * k)
                if img.width() > desti.width() * 1.5:     # redueix abans: més ràpid i més nítid
                    img = img.scaled(int(desti.width()), int(desti.height()), Qt.AspectRatioMode.IgnoreAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
                img = aplica_gamma(img, o["gamma"])
                p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                p.drawImage(desti, img)
                if o["nom"]:
                    f = p.font()
                    f.setPointSizeF(8)
                    p.setFont(f)
                    p.setPen(QColor(60, 60, 60))
                    p.drawText(QRectF(desti.x(), desti.bottom() + 1.5 * k, desti.width(), 6 * k),
                               Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, os.path.basename(el.cami))
        finally:
            if p.isActive():
                p.end()
            QApplication.restoreOverrideCursor()

    def _desa_opcions(self):
        o = self.opcions()
        o.pop("_u_vell", None)
        config.set("impressio", o)
        config.desa()

    def reject(self):
        self._desa_opcions()
        super().reject()
