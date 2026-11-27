"""Xoriguer Fotos — visualitzador i editor de fotos ràpid per a Windows."""

import collections
import ctypes
import os
import shutil
import subprocess
import sys

from PyQt6.QtCore import (QAbstractListModel, QDir, QFileSystemWatcher, QModelIndex, QRect, QRectF, QSize, Qt, QTimer,
                          pyqtSignal)
from PyQt6.QtGui import (QAction, QActionGroup, QColor, QFileSystemModel, QFont, QGuiApplication, QKeySequence, QPainter,
                         QPen, QPixmap)
from PyQt6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QFileDialog, QHBoxLayout, QInputDialog, QLabel,
                             QLineEdit, QListView, QMainWindow, QMessageBox, QPushButton, QSlider, QSplitter, QStyle,
                             QStyledItemDelegate, QToolBar, QToolButton, QTreeView, QVBoxLayout, QWidget)

import config
import estil as E
import i18n
import imatges as IM
import valoracions as VAL
from i18n import t

VERSIO = "1.3.2"
ROL_CAMI = Qt.ItemDataRole.UserRole


# ================================================================ miniatures
class ModelMiniatures(QAbstractListModel):
    def __init__(self, carregador, parent=None):
        super().__init__(parent)
        self.carregador = carregador
        self.fitxers = []
        self.fila = {}
        self.cau = collections.OrderedDict()
        self.costat_px = 160
        self.carregador.feta.connect(self._feta)

    def posa_fitxers(self, fitxers):
        self.beginResetModel()
        self.carregador.buida()
        self.fitxers = fitxers
        self.fila = {f["cami"]: i for i, f in enumerate(fitxers)}
        self.endResetModel()

    def posa_costat(self, px):
        if px != self.costat_px:
            self.costat_px = px
            self.cau.clear()
            self.carregador.buida()
            if self.fitxers:
                self.dataChanged.emit(self.index(0), self.index(len(self.fitxers) - 1))

    def repinta(self, cami):
        r = self.fila.get(cami)
        if r is not None:
            self.dataChanged.emit(self.index(r), self.index(r), [Qt.ItemDataRole.DisplayRole])

    def oblida(self, cami):
        self.cau.pop(cami, None)
        r = self.fila.get(cami)
        if r is not None:
            self.dataChanged.emit(self.index(r), self.index(r))

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.fitxers)

    def data(self, idx, rol=Qt.ItemDataRole.DisplayRole):
        if not idx.isValid() or idx.row() >= len(self.fitxers):
            return None
        f = self.fitxers[idx.row()]
        if rol == Qt.ItemDataRole.DisplayRole:
            return f["nom"]
        if rol == Qt.ItemDataRole.DecorationRole:
            if f["cami"] in self.cau:
                self.cau.move_to_end(f["cami"])
                return self.cau[f["cami"]]
            self.carregador.demana(f["cami"], self.costat_px)
            return None
        if rol == ROL_CAMI:
            return f["cami"]
        if rol == Qt.ItemDataRole.ToolTipRole:
            extra = VAL.text_estrelles(VAL.estrelles(f["cami"]))
            et = VAL.etiquetes(f["cami"])
            return f"{f['nom']}\n{mida_text(f['mida'])}" + (f"\n{extra}" if extra else "") + (
                f"\n{', '.join(et)}" if et else "")
        return None

    def _feta(self, cami, costat, img):
        if costat != self.costat_px or cami not in self.fila:
            return
        pm = QPixmap.fromImage(img) if not img.isNull() else QPixmap()
        self.cau[cami] = pm
        limit = max(400, int(300e6 / (self.costat_px * self.costat_px * 4)))
        while len(self.cau) > limit:
            self.cau.popitem(last=False)
        r = self.fila[cami]
        self.dataChanged.emit(self.index(r), self.index(r), [Qt.ItemDataRole.DecorationRole])


class DelegatMiniatura(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.costat = 160
        self.dpr = 1.0

    def sizeHint(self, opt, idx):
        return QSize(self.costat + 16, self.costat + 38)

    def paint(self, p, opt, idx):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(opt.rect).adjusted(3, 3, -3, -3)
        sel = bool(opt.state & QStyle.StateFlag.State_Selected)
        sobre = bool(opt.state & QStyle.StateFlag.State_MouseOver)
        p.setPen(QPen(QColor(E.OR1), 2) if sel else QPen(QColor(E.LINE), 1) if sobre else Qt.PenStyle.NoPen)
        p.setBrush(QColor(E.BG3) if (sel or sobre) else QColor(E.CARD))
        p.drawRoundedRect(r, 8, 8)
        area = QRectF(r.x() + 5, r.y() + 5, r.width() - 10, r.height() - 32)
        pm = idx.data(Qt.ItemDataRole.DecorationRole)
        if pm is not None and not pm.isNull():
            w, h = pm.width() / self.dpr, pm.height() / self.dpr
            s = min(area.width() / w, area.height() / h, 1.0)
            w, h = w * s, h * s
            desti = QRectF(area.x() + (area.width() - w) / 2, area.y() + (area.height() - h) / 2, w, h)
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            p.drawPixmap(desti, pm, QRectF(pm.rect()))
            cami = idx.data(ROL_CAMI)
            n = VAL.estrelles(cami) if cami else 0
            et = VAL.etiquetes(cami) if cami else []
            if n or et:
                txt = ("★" * n) + ("  🏷" if et else "")
                fm = opt.fontMetrics
                caixa = QRectF(desti.right() - fm.horizontalAdvance(txt) - 14, desti.bottom() - 22,
                               fm.horizontalAdvance(txt) + 10, 19)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(26, 37, 51, 210))
                p.drawRoundedRect(caixa, 6, 6)
                p.setPen(QColor(E.OR1))
                p.drawText(caixa, Qt.AlignmentFlag.AlignCenter, txt)
        else:
            p.setPen(QColor(E.LINE))
            p.setBrush(Qt.BrushStyle.NoBrush)
            c = area.center()
            m = min(area.width(), area.height()) * 0.28
            p.drawRoundedRect(QRectF(c.x() - m, c.y() - m * 0.75, 2 * m, 1.5 * m), 4, 4)
            if pm is not None:  # no s'ha pogut llegir
                p.setPen(QColor(E.OR2))
                p.drawText(area, Qt.AlignmentFlag.AlignCenter, "?")
        p.setPen(QColor(E.OR1) if sel else QColor(E.CREAM))
        text = QRectF(r.x() + 6, r.bottom() - 25, r.width() - 12, 20)
        nom = opt.fontMetrics.elidedText(idx.data(Qt.ItemDataRole.DisplayRole) or "", Qt.TextElideMode.ElideMiddle,
                                         int(text.width()))
        p.drawText(text, Qt.AlignmentFlag.AlignCenter, nom)
        p.restore()


def mida_text(b):
    if b >= 1024 * 1024:
        return f"{b / 1024 / 1024:.1f} MB"
    return f"{b / 1024:.0f} KB"


# ================================================================== finestra
class Finestra(QMainWindow):
    canvi_idioma = pyqtSignal(str)
    meta_llesta = pyqtSignal(str)

    MIDES = [64, 96, 128, 160, 200, 256, 320]

    def __init__(self, carregador, memoria, carpeta=None):
        super().__init__()
        self.setWindowTitle("Xoriguer Fotos")
        self.setWindowIcon(E.icona_app())
        self.setAcceptDrops(True)
        self.carregador = carregador
        self.memoria = memoria
        self.carpeta = None
        self.historial, self.hist_pos = [], -1
        self.visor = None
        self.editors = []

        # ---- arbre de carpetes
        self.fsm = QFileSystemModel(self)
        self.fsm.setFilter(QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot | QDir.Filter.Drives)
        self.fsm.setRootPath("")
        self.arbre = QTreeView()
        self.arbre.setModel(self.fsm)
        for c in (1, 2, 3):
            self.arbre.hideColumn(c)
        self.arbre.setHeaderHidden(True)
        self.arbre.setAnimated(False)
        self.arbre.clicked.connect(lambda i: self.obre_carpeta(self.fsm.filePath(i)))
        self.arbre.activated.connect(lambda i: self.obre_carpeta(self.fsm.filePath(i)))
        self.fsm.directoryLoaded.connect(lambda _: self._sincronitza_arbre(False))

        # ---- previsualització
        self.prev = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.prev.setMinimumHeight(150)
        self.prev.setStyleSheet(f"background:{E.CARD}; border:1px solid {E.LINE}; border-radius:8px;")
        self.prev_info = QLabel(objectName="suau", wordWrap=True)
        self.prev_info.setTextFormat(Qt.TextFormat.RichText)
        self.prev_info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        caixa_prev = QWidget()
        pl = QVBoxLayout(caixa_prev)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.addWidget(self.prev, 1)
        pl.addWidget(self.prev_info)
        self._prev_cami = None
        self._prev_px = 520
        self.carregador.feta.connect(self._prev_feta)
        self._temps_prev = QTimer(self, singleShot=True, timeout=self._actualitza_prev)

        self.split_esq = QSplitter(Qt.Orientation.Vertical)
        self.split_esq.addWidget(self.arbre)
        self.split_esq.addWidget(caixa_prev)
        self.split_esq.setSizes([420, 330])

        # ---- miniatures
        self.model = ModelMiniatures(carregador, self)
        self.delegat = DelegatMiniatura(self)
        self.llista = QListView()
        self.llista.setModel(self.model)
        self.llista.setItemDelegate(self.delegat)
        self.llista.setViewMode(QListView.ViewMode.IconMode)
        self.llista.setResizeMode(QListView.ResizeMode.Adjust)
        self.llista.setMovement(QListView.Movement.Static)
        self.llista.setUniformItemSizes(True)
        self.llista.setLayoutMode(QListView.LayoutMode.Batched)
        self.llista.setBatchSize(300)
        self.llista.setSpacing(2)
        self.llista.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.llista.setMouseTracking(True)
        self.llista.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.llista.verticalScrollBar().setSingleStep(40)
        self.llista.doubleClicked.connect(lambda i: self.obre_visor(i.row()))
        self.llista.selectionModel().selectionChanged.connect(self._seleccio_canviada)
        self.llista.selectionModel().currentChanged.connect(lambda *_: self._temps_prev.start(60))
        self.llista.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.llista.customContextMenuRequested.connect(self._menu_context)

        self.e_cami = QLineEdit()
        self.e_cami.returnPressed.connect(lambda: self.obre_carpeta(self.e_cami.text().strip().strip('"')))
        self.c_ordre = QComboBox()
        for clau in ("nom", "data", "mida", "tipus"):
            self.c_ordre.addItem(t("o_" + clau), clau)
        self.c_ordre.setCurrentIndex(max(0, self.c_ordre.findData(config.get("ordre"))))
        self.c_ordre.currentIndexChanged.connect(self._canvia_ordre)
        self.b_invers = QToolButton(checkable=True, checked=config.get("ordre_invers"))
        self.b_invers.setText("↓↑")
        self.b_invers.setToolTip(t("o_invers"))
        self.b_invers.toggled.connect(self._canvia_ordre)
        cap = QHBoxLayout()
        cap.setContentsMargins(0, 0, 0, 0)
        cap.addWidget(self.e_cami, 1)
        cap.addWidget(QLabel(t("o_ordena")))
        cap.addWidget(self.c_ordre)
        cap.addWidget(self.b_invers)
        self.b_filtre = QToolButton(checkable=True)
        self.b_filtre.setText("⚲ " + t("fl_filtra"))
        self.b_filtre.setToolTip(t("fl_filtra") + "  (Ctrl+F)")
        self.b_filtre.toggled.connect(self._mostra_filtres)
        cap.addWidget(self.b_filtre)
        # barra de filtres
        self.barra_filtres = QWidget()
        bf = QHBoxLayout(self.barra_filtres)
        bf.setContentsMargins(0, 2, 0, 2)
        self.f_text = QLineEdit(placeholderText=t("fl_cerca"), clearButtonEnabled=True)
        self.f_estr = QComboBox()
        self.f_estr.addItem(t("fl_totes"), 0)
        for k in range(1, 6):
            self.f_estr.addItem("★" * k + ("+" if k < 5 else ""), k)
        self.f_cam = QComboBox()
        self.f_cam.addItem(t("fl_totes_cameres"), "")
        self.f_mes = QComboBox()
        self.f_mes.addItem(t("fl_totes_dates"), "")
        self.f_info = QLabel(objectName="suau")
        b_net = QPushButton(t("fl_neteja"))
        b_net.clicked.connect(self._neteja_filtres)
        for w in (self.f_text, self.f_estr, self.f_cam, self.f_mes, self.f_info, b_net):
            bf.addWidget(w, 2 if w is self.f_text else 0)
        self.f_text.textChanged.connect(lambda _: self._temps_filtre.start(200))
        for c in (self.f_estr, self.f_cam, self.f_mes):
            c.currentIndexChanged.connect(lambda _: self._aplica_filtre())
        self._temps_filtre = QTimer(self, singleShot=True, timeout=self._aplica_filtre)
        self.barra_filtres.hide()
        self.tots = []
        self._meta = {}
        self.meta_llesta.connect(lambda c: c == self.carpeta and self._omple_combos())
        dreta = QWidget()
        dl = QVBoxLayout(dreta)
        dl.setContentsMargins(0, 0, 0, 0)
        dl.addLayout(cap)
        dl.addWidget(self.barra_filtres)
        dl.addWidget(self.llista, 1)

        self.split = QSplitter(Qt.Orientation.Horizontal)
        self.split.addWidget(self.split_esq)
        self.split.addWidget(dreta)
        self.split.setStretchFactor(1, 1)
        self.split.setSizes([300, 1000])
        cont = QWidget()
        cl = QVBoxLayout(cont)
        cl.setContentsMargins(6, 6, 6, 6)
        cl.addWidget(self.split)
        self.setCentralWidget(cont)

        # ---- barra d'estat amb la mida de les miniatures
        self.lbl_estat = QLabel()
        self.statusBar().addWidget(self.lbl_estat, 1)
        self.sl_mida = QSlider(Qt.Orientation.Horizontal, minimum=0, maximum=len(self.MIDES) - 1)
        self.sl_mida.setFixedWidth(140)
        mida = config.get("mida_miniatura")
        self.sl_mida.setValue(min(range(len(self.MIDES)), key=lambda i: abs(self.MIDES[i] - mida)))
        self.sl_mida.valueChanged.connect(self._canvia_mida)
        self.sl_mida.setToolTip(t("m_mida_miniatures"))
        self.statusBar().addPermanentWidget(QLabel(t("m_mida_miniatures")))
        self.statusBar().addPermanentWidget(self.sl_mida)

        self._accions()
        self._canvia_mida(self.sl_mida.value())

        self.vigilant = QFileSystemWatcher(self)
        self.vigilant.directoryChanged.connect(lambda _: self._temps_refresca.start(400))
        self._temps_refresca = QTimer(self, singleShot=True, timeout=lambda: self.refresca(conserva=True))

        geo = config.get("geometria")
        if geo:
            try:
                self.restoreGeometry(bytes.fromhex(geo))
            except ValueError:
                pass
        else:
            self.resize(1400, 880)
        if config.get("splitter"):
            self.split.setSizes(config.get("splitter"))
        if config.get("splitter_esq"):
            self.split_esq.setSizes(config.get("splitter_esq"))

        inici = carpeta or config.get("carpeta")
        if not inici or not os.path.exists(inici):
            inici = os.path.join(os.path.expanduser("~"), "Pictures")
            if not os.path.isdir(inici):
                inici = os.path.expanduser("~")
        self.obre_carpeta(inici)

    # ------------------------------------------------------------ accions
    def _accio(self, text, f, tecla=None, icona=None, menu=None, barra=None, mirall=False, local=False):
        """local=True: la drecera només val a la llista de miniatures (no molesta quan s'escriu un camí)."""
        a = QAction(text, self)
        if icona:
            a.setIcon(E.icona(icona, mirall=mirall))
        if tecla:
            a.setShortcuts([QKeySequence(k) for k in (tecla if isinstance(tecla, (list, tuple)) else [tecla])])
            a.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut if local
                                 else Qt.ShortcutContext.WindowShortcut)
        a.triggered.connect(lambda *_: f())
        if menu is not None:
            menu.addAction(a)
        if barra is not None:
            barra.addAction(a)
        (self.llista if local else self).addAction(a)
        return a

    def _accions(self):
        tb = QToolBar()
        tb.setMovable(False)
        tb.setIconSize(QSize(22, 22))
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.addToolBar(tb)
        mb = self.menuBar()

        m = mb.addMenu(t("m_fitxer"))
        self._accio(t("a_obre_carpeta") + "…", self.tria_carpeta, "Ctrl+O", "carpeta", m)
        self._accio(t("a_obre_fitxer") + "…", self.tria_fitxer, "Ctrl+Shift+O", None, m)
        m.addSeparator()
        self._accio(t("a_lots") + "…", self.lots, "Ctrl+B", "lots", m)
        self._accio(t("cr_titol") + "…", self.correu, "F6", None, m)
        self._accio(t("pe_imprimeix") + "…", self.imprimeix, "Ctrl+P", None, m)
        m.addSeparator()
        self._accio(t("a_surt"), self.close, "Alt+F4", None, m)

        m = mb.addMenu(t("m_edita"))
        self._accio(t("a_edita"), self.edita, "E", "edita", m, local=True)
        self._accio(t("a_reanomena"), self.reanomena, "F2", "reanomena", m, local=True)
        self._accio(t("a_copia_a") + "…", lambda: self.copia_mou(False), "Ctrl+Shift+C", "copia", m)
        self._accio(t("a_mou_a") + "…", lambda: self.copia_mou(True), "Ctrl+Shift+M", "mou", m)
        self._accio(t("a_elimina"), self.elimina, "Del", "elimina", m, local=True)
        m.addSeparator()
        self._accio(t("a_copia_imatge"), self.copia_imatge, "Ctrl+C", None, m, local=True)
        self._accio(t("a_selecciona_tot"), self.llista.selectAll, "Ctrl+A", None, m, local=True)
        m.addSeparator()
        sm = m.addMenu(t("vl_valoracio"))
        for k in range(6):
            self._accio(VAL.text_estrelles(k) or t("vl_sense"), lambda k=k: self.posa_estrelles(k), f"Ctrl+{k}",
                        None, sm, local=True)
        self._accio(t("vl_etiquetes") + "…", self.etiquetes, "T", None, m, local=True)

        m = mb.addMenu(t("m_visualitza"))
        self._accio(t("a_visualitza"), lambda: self.obre_visor(), ["Return", "Enter"], "foto", m, local=True)
        self._accio(t("a_presentacio"), self.presentacio, "S", "presentacio", m, local=True)
        self._accio(t("cm_titol"), self.compara, "P", None, m, local=True)
        self._accio(t("fl_filtra"), lambda: self.b_filtre.toggle(), "Ctrl+F", None, m)
        m.addSeparator()
        self._accio(t("a_enrere"), self.enrere, ["Alt+Left"], "enrere", m)
        self._accio(t("a_endavant"), self.endavant, ["Alt+Right"], "endavant", m)
        self._accio(t("a_amunt"), self.amunt, ["Backspace", "Alt+Up"], "amunt", m, local=True)
        self._accio(t("a_refresca"), self.refresca, "F5", "refresca", m)
        m.addSeparator()
        self._accio(t("a_mes_grans"), lambda: self.sl_mida.setValue(self.sl_mida.value() + 1), "Ctrl++", None, m)
        self._accio(t("a_mes_petites"), lambda: self.sl_mida.setValue(self.sl_mida.value() - 1), "Ctrl+-", None, m)

        m = mb.addMenu(t("m_eines"))
        self._accio(t("du_titol") + "…", self.duplicats, "Ctrl+D", None, m)
        self._accio(t("pr_titol") + "…", self.opcions_presentacio, None, None, m)
        m.addSeparator()
        self._accio(t("a_fons"), self.fons_escriptori, None, "fons", m)
        self._accio(t("a_explorador"), self.explorador, "Ctrl+Shift+E", None, m)
        m.addSeparator()
        a = self._accio(t("a_sense_perdua"), lambda: None, None, None, m)
        a.setCheckable(True)
        a.setChecked(config.get("gir_sense_perdua") is not False)
        a.toggled.connect(lambda v: config.set("gir_sense_perdua", v))
        a = self._accio(t("a_confirma_elim"), lambda: None, None, None, m)
        a.setCheckable(True)
        a.setChecked(config.get("confirma_eliminar"))
        a.toggled.connect(lambda v: config.set("confirma_eliminar", v))
        a = self._accio(t("a_amplia"), lambda: None, None, None, m)
        a.setCheckable(True)
        a.setChecked(config.get("amplia_petites"))
        a.toggled.connect(lambda v: config.set("amplia_petites", v))

        m = mb.addMenu("🌐 " + t("m_idioma"))
        g = QActionGroup(self)
        for codi, nom in i18n.IDIOMES.items():
            a = m.addAction(nom)
            a.setCheckable(True)
            a.setChecked(codi == i18n.actual())
            a.triggered.connect(lambda _, c=codi: self.canvi_idioma.emit(c))
            g.addAction(a)

        m = mb.addMenu(t("m_ajuda"))
        self._accio(t("a_dreceres"), self.dreceres, "F1", None, m)
        self._accio(t("a_quant_a"), self.quant_a, None, None, m)

        # barra d'eines
        for element in [("a_enrere", "enrere", self.enrere), ("a_endavant", "endavant", self.endavant),
                           ("a_amunt", "amunt", self.amunt), ("a_refresca", "refresca", self.refresca), None,
                           ("a_obre_carpeta", "carpeta", self.tria_carpeta), None,
                           ("a_visualitza", "foto", lambda: self.obre_visor()),
                           ("a_presentacio", "presentacio", self.presentacio),
                           ("cm_titol", "ajusta", self.compara),
                           ("a_edita", "edita", self.edita), None,
                           ("a_gira_e", "gira", lambda: self.gira_seleccio(-90)),
                           ("a_gira_d", "gira", lambda: self.gira_seleccio(90)), None,
                           ("a_copia_a", "copia", lambda: self.copia_mou(False)),
                           ("a_mou_a", "mou", lambda: self.copia_mou(True)),
                           ("a_reanomena", "reanomena", self.reanomena),
                           ("a_elimina", "elimina", self.elimina), None,
                           ("a_lots", "lots", self.lots), ("cr_curt", "copia", self.correu),
                           ("pe_imprimeix", "imprimeix", self.imprimeix),
                           ("a_fons", "fons", self.fons_escriptori)]:
            if element is None:
                tb.addSeparator()
                continue
            nom, ic, f = element
            a = QAction(E.icona(ic, mirall=(nom == "a_gira_e")), t(nom + "_curt") if i18n.te(nom + "_curt") else t(nom), self)
            a.setToolTip(t("cr_titol") if nom == "cr_curt" else t(nom))
            a.triggered.connect(lambda *_, f=f: f())
            tb.addAction(a)

    # ---------------------------------------------------------- carpetes
    def obre_carpeta(self, cami, historial=True, seleccio=None):
        if not cami:
            return
        cami = os.path.normpath(cami)
        if os.path.isfile(cami):
            seleccio, cami = cami, os.path.dirname(cami)
        if not os.path.isdir(cami):
            QMessageBox.warning(self, "Xoriguer Fotos", t("e_no_carpeta", cami=cami))
            return
        if self.carpeta and self.vigilant.directories():
            self.vigilant.removePaths(self.vigilant.directories())
        self.carpeta = cami
        self.vigilant.addPath(cami)
        config.set("carpeta", cami)
        if historial:
            del self.historial[self.hist_pos + 1:]
            if not self.historial or self.historial[-1] != cami:
                self.historial.append(cami)
            self.hist_pos = len(self.historial) - 1
        self.e_cami.setText(cami)
        self.setWindowTitle(f"{os.path.basename(cami) or cami} — Xoriguer Fotos")
        self._carrega_llista(seleccio)
        self._sincronitza_arbre(True)

    def _llegeix(self):
        fitxers = []
        try:
            with os.scandir(self.carpeta) as it:
                for e in it:
                    try:
                        if e.is_file() and IM.es_imatge(e.name):
                            st = e.stat()
                            fitxers.append({"cami": os.path.normpath(e.path), "nom": e.name,
                                            "mida": st.st_size, "mtime": st.st_mtime})
                    except OSError:
                        pass
        except OSError:
            pass
        ordre = self.c_ordre.currentData()
        claus = {"nom": lambda f: IM.clau_natural(f["nom"]), "data": lambda f: f["mtime"],
                 "mida": lambda f: f["mida"],
                 "tipus": lambda f: (os.path.splitext(f["nom"])[1].lower(), IM.clau_natural(f["nom"]))}
        fitxers.sort(key=claus[ordre], reverse=self.b_invers.isChecked())
        return fitxers

    def _carrega_llista(self, seleccio=None, conserva_scroll=False):
        scroll = self.llista.verticalScrollBar().value()
        self.tots = self._llegeix()
        if self.barra_filtres.isVisible():
            self._llegeix_meta()
        self.model.posa_fitxers(self._filtra(self.tots))
        if conserva_scroll:
            QTimer.singleShot(0, lambda: self.llista.verticalScrollBar().setValue(scroll))
        if seleccio and seleccio in self.model.fila:
            self.selecciona(seleccio)
        elif self.model.fitxers:
            self.llista.setCurrentIndex(self.model.index(0))
        else:
            self._actualitza_prev()
        self._seleccio_canviada()

    # ------------------------------------------------------------ filtres
    def _mostra_filtres(self, v):
        self.barra_filtres.setVisible(v)
        if v:
            self._llegeix_meta()
            self.f_text.setFocus()
        self._aplica_filtre()

    def _neteja_filtres(self):
        for w in (self.f_estr, self.f_cam, self.f_mes):
            w.blockSignals(True)
            w.setCurrentIndex(0)
            w.blockSignals(False)
        self.f_text.clear()
        self._aplica_filtre()

    def _llegeix_meta(self):
        """Càmera i mes de cada foto (en segon pla) per omplir els filtres."""
        import threading
        falten = [f for f in self.tots if self._meta.get(f["cami"], (None, None, 0))[2] != f["mtime"]]
        if not falten:
            self._omple_combos()
            return
        self.f_info.setText(t("fl_llegint"))
        from datetime import datetime

        def feina(fitxers, carpeta):
            for f in fitxers:
                ex = IM.info_exif(f["cami"])
                d = ex.get("data", "")
                mes = d[:7] if len(d) >= 7 and d[4] == "-" else datetime.fromtimestamp(f["mtime"]).strftime("%Y-%m")
                self._meta[f["cami"]] = (ex.get("camera", ""), mes, f["mtime"])
            self.meta_llesta.emit(carpeta)
        threading.Thread(target=feina, args=(falten, self.carpeta), daemon=True).start()

    def _omple_combos(self):
        self.f_info.setText("")
        cams = sorted({self._meta[f["cami"]][0] for f in self.tots if f["cami"] in self._meta} - {""})
        mesos = sorted({self._meta[f["cami"]][1] for f in self.tots if f["cami"] in self._meta}, reverse=True)
        for combo, valors, primer in ((self.f_cam, cams, t("fl_totes_cameres")), (self.f_mes, mesos, t("fl_totes_dates"))):
            actual = combo.currentData()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(primer, "")
            for v in valors:
                combo.addItem(v, v)
            combo.setCurrentIndex(max(0, combo.findData(actual)))
            combo.blockSignals(False)
        self._aplica_filtre()

    def _filtra(self, fitxers):
        if not self.barra_filtres.isVisible():
            return list(fitxers)
        text = self.f_text.text().strip().lower()
        estr = self.f_estr.currentData() or 0
        cam = self.f_cam.currentData() or ""
        mes = self.f_mes.currentData() or ""
        res = []
        for f in fitxers:
            c = f["cami"]
            if estr and VAL.estrelles(c) < estr:
                continue
            if text and text not in f["nom"].lower() and not any(text in e.lower() for e in VAL.etiquetes(c)):
                continue
            meta = self._meta.get(c)
            if cam and (not meta or meta[0] != cam):
                continue
            if mes and (not meta or meta[1] != mes):
                continue
            res.append(f)
        return res

    def _aplica_filtre(self):
        actual = self.actual()
        filtrats = self._filtra(self.tots)
        self.model.posa_fitxers(filtrats)
        if self.barra_filtres.isVisible() and not self.f_info.text().startswith(t("fl_llegint")):
            self.f_info.setText(t("fl_resultat", n=len(filtrats), m=len(self.tots)))
        if actual and actual in self.model.fila:
            self.selecciona(actual)
        elif self.model.fitxers:
            self.llista.setCurrentIndex(self.model.index(0))
        self._seleccio_canviada()
        self._temps_prev.start(60)

    # ----------------------------------------------- estrelles i etiquetes
    def posa_estrelles(self, n):
        camins = self.seleccionats()
        if camins:
            VAL.posa_estrelles(camins, n)
            for c in camins:
                self.model.repinta(c)
            self._temps_prev.start(30)
            if self.barra_filtres.isVisible() and self.f_estr.currentData():
                self._aplica_filtre()

    def etiquetes(self):
        camins = self.seleccionats()
        if camins:
            from panells import dialeg_etiquetes
            if dialeg_etiquetes(self, camins):
                for c in camins:
                    self.model.repinta(c)
                self._temps_prev.start(30)

    def _valoracio_visor(self, cami):
        self.model.repinta(cami)
        if cami == self._prev_cami:
            self._temps_prev.start(30)

    # ---------------------------------------------------- eines noves
    def compara(self):
        camins = self.seleccionats()
        if len(camins) < 2:
            QMessageBox.information(self, t("cm_titol"), t("cm_tria"))
            return
        if len(camins) > 4:
            camins = camins[:4]
        from comparador import Comparador
        self._comp = Comparador(camins, self.memoria)
        self._comp.eliminada.connect(self._eliminada)
        self._comp.obre.connect(lambda c: (self.selecciona(c), self.obre_visor()))
        self._comp.showMaximized()

    def duplicats(self):
        from duplicats import DialegDuplicats
        d = DialegDuplicats(self.carpeta, self)
        d.eliminades.connect(lambda llista: [(self.memoria.oblida(c), self._eliminada(c)) for c in llista])
        d.obre.connect(self.obre_visor_llista)
        d.exec()

    def correu(self):
        camins = self.seleccionats()
        if camins:
            from correu import DialegCorreu
            DialegCorreu(camins, self).exec()

    def imprimeix(self):
        camins = self.seleccionats()
        if camins:
            from impressio import DialegImpressio
            DialegImpressio(camins, self).exec()

    def opcions_presentacio(self):
        from presentacio import DialegPresentacio
        DialegPresentacio(self).exec()

    def selecciona(self, cami):
        r = self.model.fila.get(os.path.normpath(cami))
        if r is not None:
            i = self.model.index(r)
            self.llista.setCurrentIndex(i)
            self.llista.scrollTo(i, QAbstractItemView.ScrollHint.PositionAtCenter)

    def _sincronitza_arbre(self, expandeix):
        if not self.carpeta:
            return
        i = self.fsm.index(self.carpeta)
        if i.isValid() and self.arbre.currentIndex() != i:
            self.arbre.setCurrentIndex(i)
            self.arbre.scrollTo(i)
            if expandeix:
                self.arbre.expand(i)

    def refresca(self, conserva=False):
        if not self.carpeta:
            return
        if not os.path.isdir(self.carpeta):
            self.amunt()
            return
        actual = self.actual()
        if not conserva:
            self.model.cau.clear()
        self._carrega_llista(actual, conserva_scroll=True)

    def tria_carpeta(self):
        d = QFileDialog.getExistingDirectory(self, t("a_obre_carpeta"), self.carpeta or "")
        if d:
            self.obre_carpeta(d)

    def tria_fitxer(self):
        ext = " ".join("*." + e for e in sorted(IM.EXTENSIONS))
        f, _ = QFileDialog.getOpenFileName(self, t("a_obre_fitxer"), self.carpeta or "", f"{t('imatges')} ({ext})")
        if f:
            self.obre_carpeta(f)
            self.obre_visor()

    def enrere(self):
        if self.hist_pos > 0:
            self.hist_pos -= 1
            self.obre_carpeta(self.historial[self.hist_pos], historial=False)

    def endavant(self):
        if self.hist_pos < len(self.historial) - 1:
            self.hist_pos += 1
            self.obre_carpeta(self.historial[self.hist_pos], historial=False)

    def amunt(self):
        if self.carpeta:
            pare = os.path.dirname(self.carpeta)
            if pare and pare != self.carpeta:
                self.obre_carpeta(pare, seleccio=None)

    def _canvia_ordre(self, *_):
        config.set("ordre", self.c_ordre.currentData())
        config.set("ordre_invers", self.b_invers.isChecked())
        self._carrega_llista(self.actual())

    def _canvia_mida(self, i):
        c = self.MIDES[max(0, min(i, len(self.MIDES) - 1))]
        config.set("mida_miniatura", c)
        dpr = self.devicePixelRatioF()
        self.delegat.costat = c
        self.delegat.dpr = dpr
        self.model.posa_costat(int(c * dpr))
        self.llista.setGridSize(QSize(c + 18, c + 40))
        self.llista.doItemsLayout()

    # -------------------------------------------------------- selecció
    def actual(self):
        i = self.llista.currentIndex()
        return i.data(ROL_CAMI) if i.isValid() else None

    def seleccionats(self):
        files = sorted(i.row() for i in self.llista.selectionModel().selectedIndexes())
        camins = [self.model.fitxers[r]["cami"] for r in files]
        if not camins and self.actual():
            camins = [self.actual()]
        return camins

    def _seleccio_canviada(self, *_):
        n = len(self.model.fitxers)
        sel = self.llista.selectionModel().selectedIndexes()
        total = sum(f["mida"] for f in self.model.fitxers)
        txt = t("s_imatges", n=n) + f"  ·  {mida_text(total)}"
        if sel:
            mida_sel = sum(self.model.fitxers[i.row()]["mida"] for i in sel)
            txt += "    |    " + t("s_seleccionades", n=len(sel)) + f"  ·  {mida_text(mida_sel)}"
        self.lbl_estat.setText(txt)

    def _actualitza_prev(self):
        cami = self.actual()
        self._prev_cami = cami
        if not cami:
            self.prev.clear()
            self.prev_info.setText("")
            return
        self._prev_px = int(max(self.prev.width(), self.prev.height()) * self.devicePixelRatioF())
        self.carregador.demana(cami, self._prev_px)
        pm = self.model.cau.get(cami)
        if pm is not None and not pm.isNull():
            self._mostra_prev(pm)
        f = self.model.fitxers[self.model.fila[cami]]
        w, h = IM.mida_imatge(cami)
        ex = IM.info_exif(cami)
        from datetime import datetime
        files = [f"<b style='color:{E.CREAM}'>{f['nom']}</b>",
                 f"{w} × {h} px  ·  {mida_text(f['mida'])}",
                 datetime.fromtimestamp(f["mtime"]).strftime("%d/%m/%Y %H:%M")]
        if "camera" in ex:
            files.append(ex["camera"])
        tec = "  ·  ".join(ex[k] for k in ("exposicio", "diafragma", "iso", "focal") if k in ex)
        if tec:
            files.append(tec)
        if "data" in ex:
            files.append(t("i_data") + ": " + ex["data"])
        n = VAL.estrelles(cami)
        if n:
            files.append(f"<span style='color:{E.OR1}'>{VAL.text_estrelles(n)}</span>")
        et = VAL.etiquetes(cami)
        if et:
            files.append("🏷 " + ", ".join(et))
        self.prev_info.setText("<br>".join(files))

    def _prev_feta(self, cami, costat, img):
        if cami == self._prev_cami and costat == self._prev_px and not img.isNull():
            self._mostra_prev(QPixmap.fromImage(img))

    def _mostra_prev(self, pm):
        dpr = self.devicePixelRatioF()
        mida = self.prev.size() * dpr - QSize(12, 12)
        pm = pm.scaled(mida, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        pm.setDevicePixelRatio(dpr)
        self.prev.setPixmap(pm)

    # ------------------------------------------------------ visor/editor
    def obre_visor(self, fila=None, presentacio=False):
        if not self.model.fitxers:
            return
        if fila is None:
            i = self.llista.currentIndex()
            fila = i.row() if i.isValid() else 0
        self.obre_visor_llista([f["cami"] for f in self.model.fitxers], fila, presentacio)

    def obre_visor_llista(self, camins, fila=0, presentacio=False):
        from visor import Visor
        if self.visor is not None:
            self.visor.close()
        self.visor = Visor(camins, fila, self.memoria)
        self.visor.tancat.connect(self._visor_tancat)
        self.visor.eliminada.connect(self._eliminada)
        self.visor.editar.connect(self.obre_editor)
        self.visor.desat.connect(self._desat)
        self.visor.canvi_fitxers.connect(lambda: self.refresca(conserva=True))
        self.visor.surt.connect(lambda: QTimer.singleShot(0, self.close))
        self.visor.valoracio.connect(self._valoracio_visor)
        self.visor.showFullScreen()
        self.visor.activateWindow()
        if presentacio:
            self.visor.alterna_presentacio()

    def presentacio(self):
        self.obre_visor(presentacio=True)

    def _visor_tancat(self, cami):
        self.visor = None
        if not self.isVisible():
            self.show()
        if cami:
            self.selecciona(cami)
        self.activateWindow()
        self.llista.setFocus()

    def edita(self):
        cami = self.actual()
        if cami:
            self.obre_editor(cami)

    def obre_editor(self, cami):
        from editor import Editor
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            ed = Editor(cami)
        except Exception as e:
            QMessageBox.warning(self, "Xoriguer Fotos", t("e_no_obert") + f"\n{e}")
            return
        finally:
            QApplication.restoreOverrideCursor()
        ed.desat.connect(self._desat)
        ed.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.editors.append(ed)
        ed.destroyed.connect(lambda *_, e=ed: self.editors.remove(e) if e in self.editors else None)
        ed.showMaximized()
        ed.activateWindow()

    def _desat(self, cami):
        cami = os.path.normpath(cami)
        self.memoria.oblida(cami)
        self.model.oblida(cami)
        if os.path.dirname(cami) == self.carpeta and cami not in self.model.fila:
            self.refresca(conserva=True)
        if self.visor is not None and self.visor.actual() == cami:
            self.visor.recarrega(cami)
        if cami == self._prev_cami:
            self._temps_prev.start(50)

    # --------------------------------------------------- operacions fitxer
    def _eliminada(self, cami):
        self.tots = [f for f in self.tots if f["cami"] != cami]
        r = self.model.fila.get(cami)
        if r is None:
            return
        self.model.beginRemoveRows(QModelIndex(), r, r)
        del self.model.fitxers[r]
        self.model.fila = {f["cami"]: i for i, f in enumerate(self.model.fitxers)}
        self.model.cau.pop(cami, None)
        self.model.endRemoveRows()
        self._seleccio_canviada()

    def elimina(self):
        camins = self.seleccionats()
        if not camins:
            return
        if config.get("confirma_eliminar"):
            msg = t("p_elimina_1", nom=os.path.basename(camins[0])) if len(camins) == 1 else t("p_elimina_n", n=len(camins))
            if QMessageBox.question(self, "Xoriguer Fotos", msg) != QMessageBox.StandardButton.Yes:
                return
        from PyQt6.QtCore import QFile
        fila = self.llista.currentIndex().row()
        errors = 0
        for c in camins:
            if QFile.moveToTrash(c):
                self.memoria.oblida(c)
                self._eliminada(c)
            else:
                errors += 1
        if errors:
            QMessageBox.warning(self, "Xoriguer Fotos", t("e_no_eliminat"))
        if self.model.fitxers:
            self.llista.setCurrentIndex(self.model.index(max(0, min(fila, len(self.model.fitxers) - 1))))

    def reanomena(self):
        cami = self.actual()
        if not cami:
            return
        nom, ext = os.path.splitext(os.path.basename(cami))
        nou, ok = QInputDialog.getText(self, t("a_reanomena"), t("p_nou_nom"), text=nom)
        nou = nou.strip()
        if not ok or not nou or nou == nom:
            return
        if not os.path.splitext(nou)[1] or os.path.splitext(nou)[1].lower() != ext.lower():
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
        VAL.mou(cami, desti)
        self.memoria.oblida(cami)
        self._carrega_llista(desti, conserva_scroll=True)

    def copia_mou(self, moure):
        camins = self.seleccionats()
        if not camins:
            return
        d = QFileDialog.getExistingDirectory(self, t("a_mou_a" if moure else "a_copia_a"), self.carpeta or "")
        if not d or os.path.normpath(d) == self.carpeta:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        errors = []
        try:
            for c in camins:
                desti = os.path.join(d, os.path.basename(c))
                base, ext = os.path.splitext(desti)
                n = 2
                while os.path.exists(desti):
                    desti = f"{base} ({n}){ext}"
                    n += 1
                try:
                    if moure:
                        shutil.move(c, desti)
                        VAL.mou(c, desti)
                        self.memoria.oblida(c)
                        self._eliminada(c)
                    else:
                        shutil.copy2(c, desti)
                        VAL.copia(c, desti)
                except OSError as e:
                    errors.append(f"{os.path.basename(c)}: {e}")
        finally:
            QApplication.restoreOverrideCursor()
        if errors:
            QMessageBox.warning(self, "Xoriguer Fotos", "\n".join(errors[:15]))
        else:
            self.statusBar().showMessage(t("s_fet_n", n=len(camins)), 4000)

    def gira_seleccio(self, graus):
        camins = self.seleccionats()
        if not camins:
            return
        if len(camins) > 1 and QMessageBox.question(self, "Xoriguer Fotos", t("p_gira_n", n=len(camins))) != \
                QMessageBox.StandardButton.Yes:
            return
        import editor
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for c in camins:
                try:
                    editor.desa_girada(c, graus, config.get("qualitat_jpeg"))
                    self._desat(c)
                except Exception as e:
                    QMessageBox.warning(self, "Xoriguer Fotos", f"{os.path.basename(c)}: {e}")
                    break
        finally:
            QApplication.restoreOverrideCursor()

    def copia_imatge(self):
        cami = self.actual()
        if cami:
            img = IM.carrega_qimage(cami)
            if not img.isNull():
                QGuiApplication.clipboard().setImage(img)
                self.statusBar().showMessage(t("s_copiada"), 3000)

    def lots(self):
        from lots import DialegLots
        camins = self.seleccionats()
        if len(camins) <= 1:
            camins = [f["cami"] for f in self.model.fitxers]
        if camins:
            DialegLots(camins, self.carpeta, self).exec()

    def fons_escriptori(self):
        cami = self.actual()
        if not cami:
            return
        ok = ctypes.windll.user32.SystemParametersInfoW(20, 0, cami, 3) if sys.platform == "win32" else False
        self.statusBar().showMessage(t("s_fons_ok") if ok else t("e_fons"), 4000)

    def explorador(self):
        cami = self.actual()
        if cami:
            subprocess.Popen(["explorer", "/select,", cami])
        elif self.carpeta:
            os.startfile(self.carpeta)

    def _menu_context(self, pos):
        from PyQt6.QtWidgets import QMenu
        if not self.llista.indexAt(pos).isValid():
            return
        m = QMenu(self)
        for element in [("a_visualitza", lambda: self.obre_visor()), ("a_edita", self.edita), None,
                       ("a_gira_e", lambda: self.gira_seleccio(-90)), ("a_gira_d", lambda: self.gira_seleccio(90)), None,
                       ("a_copia_a", lambda: self.copia_mou(False)), ("a_mou_a", lambda: self.copia_mou(True)),
                       ("a_reanomena", self.reanomena), ("a_elimina", self.elimina), None,
                       ("a_copia_imatge", self.copia_imatge), ("a_fons", self.fons_escriptori),
                       ("a_explorador", self.explorador), ("a_lots", self.lots), None,
                       ("cm_titol", self.compara), ("vl_etiquetes", self.etiquetes), ("cr_titol", self.correu),
                       ("pe_imprimeix", self.imprimeix)]:
            if element is None:
                m.addSeparator()
            else:
                nom, f = element
                m.addAction(t(nom)).triggered.connect(lambda *_, f=f: f())
        sm = m.addMenu(t("vl_valoracio"))
        for k in range(6):
            sm.addAction(VAL.text_estrelles(k) or t("vl_sense")).triggered.connect(lambda *_, k=k: self.posa_estrelles(k))
        m.exec(self.llista.viewport().mapToGlobal(pos))

    # --------------------------------------------------------------- ajuda
    def dreceres(self):
        files = [("Enter / " + t("doble_clic"), t("a_visualitza")), ("← → / " + t("roda"), t("d_navega")),
                 ("Ctrl + " + t("roda"), "Zoom"), ("+ / − / F / 1 / Z", "Zoom / " + t("v_ajusta") + " / 100%"),
                 ("R / L", t("v_gira_d") + " / " + t("v_gira_e")), ("Ctrl+S", t("v_desa_gir")),
                 ("E", t("a_edita")), ("S", t("a_presentacio")), ("I", t("v_info")),
                 ("Supr", t("a_elimina")), ("F2", t("a_reanomena")), ("F5", t("a_refresca")),
                 ("Backspace", t("a_amunt")), ("F11", t("v_pantalla")), ("Esc", t("v_tanca")),
                 ("Ctrl+Z / Ctrl+Y", t("ed_desfes") + " / " + t("ed_refes")),
                 ("Ctrl+0 … Ctrl+5", t("vl_valoracio")), ("T", t("vl_etiquetes")), ("P", t("cm_titol")),
                 ("Ctrl+F", t("fl_filtra")), ("Ctrl+D", t("du_titol")), ("F6", t("cr_titol")),
                 ("G / " + t("roda_mig"), t("v_lupa")), ("U", t("ef_ulls")), ("X", t("ed_retalla")),
                 ("Ctrl+L / Ctrl+M", t("ef_nivells") + " / " + t("ef_corbes")), ("Ctrl+Shift+T", t("ef_text"))]
        html = "<table cellspacing='4'>" + "".join(
            f"<tr><td style='color:{E.OR1}; padding-right:14px'><b>{a}</b></td><td>{b}</td></tr>" for a, b in files) + "</table>"
        QMessageBox.information(self, t("a_dreceres"), html)

    def quant_a(self):
        QMessageBox.about(self, t("a_quant_a"),
                          f"<h2 style='font-family:Montserrat ExtraBold; color:{E.OR1}'>XORIGUER <span style='color:{E.CREAM}'>FOTOS</span></h2>"
                          f"<p>{t('versio')} {VERSIO}</p><p>{t('quant_txt')}</p>"
                          f"<p style='color:{E.SOFT}'>{t('formats')}: {', '.join(sorted(IM.EXTENSIONS))}</p>")

    # ------------------------------------------------------- arrossegar
    def dragEnterEvent(self, ev):
        if ev.mimeData().hasUrls():
            ev.acceptProposedAction()

    def dropEvent(self, ev):
        urls = [u.toLocalFile() for u in ev.mimeData().urls() if u.isLocalFile()]
        if urls:
            self.obre_carpeta(urls[0])

    def closeEvent(self, ev):
        config.set("geometria", bytes(self.saveGeometry()).hex())
        config.set("splitter", self.split.sizes())
        config.set("splitter_esq", self.split_esq.sizes())
        config.desa()
        for ed in list(self.editors):
            if not ed.close():
                ev.ignore()
                return
        if self.visor is not None:
            self.visor.close()
        super().closeEvent(ev)


# ======================================================================= inici
def main():
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Xoriguer.Fotos")
        except Exception:
            pass
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    if "--autoprova" in sys.argv:   # comprovació de l'executable compilat: escriu què hi ha disponible i surt
        res = [f"heif={sorted(IM.HEIF_EXT)}", f"raw={len(IM.RAW_EXT)}", f"qt={sorted(IM._QT_EXT)}"]
        try:
            from PyQt6.QtMultimedia import QMediaPlayer
            res.append(f"multimedia=ok {QMediaPlayer.__name__}")
        except Exception as e:
            res.append(f"multimedia=ERROR {e}")
        try:
            from PyQt6.QtPrintSupport import QPrinter  # noqa: F401
            res.append("impressio=ok")
        except Exception as e:
            res.append(f"impressio=ERROR {e}")
        with open(os.path.join(os.environ.get("TEMP", "."), "xoriguerfotos_autoprova.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(res))
        return
    app.setApplicationName("Xoriguer Fotos")
    app.setWindowIcon(E.icona_app())
    config.carrega()
    i18n.posa(config.get("idioma") or i18n.del_sistema())
    E.aplica(app)

    carregador = IM.CarregadorMiniatures()
    memoria = IM.MemoriaVisor()
    estat = {"finestra": None}

    arg = next((a for a in sys.argv[1:] if os.path.exists(a)), None)

    def crea(carpeta=None, mostra=True):
        f = Finestra(carregador, memoria, carpeta)
        f.canvi_idioma.connect(canvia_idioma)
        estat["finestra"] = f
        if mostra:
            f.show()
        return f

    def canvia_idioma(codi):
        vella = estat["finestra"]
        config.set("idioma", codi)
        i18n.posa(codi)
        config.set("geometria", bytes(vella.saveGeometry()).hex())
        nova = crea(vella.carpeta)
        nova.selecciona(vella.actual() or "")
        vella.close()
        vella.deleteLater()

    if arg and os.path.isfile(arg):
        # obert des de l'explorador amb una foto: directament al visor
        f = crea(arg, mostra=False)
        f.obre_visor()
    else:
        crea(arg)

    codi = app.exec()
    carregador.atura()
    memoria.atura()
    config.desa()
    sys.exit(codi)


if __name__ == "__main__":
    main()
