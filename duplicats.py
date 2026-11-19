"""Cerca fotos duplicades: idèntiques (mateix contingut) o semblants (retocades, reduïdes o recomprimides)."""

import hashlib
import os
import threading
from datetime import datetime

from PIL import Image, ImageOps

from PyQt6.QtCore import QObject, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (QCheckBox, QDialog, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
                             QProgressBar, QPushButton, QRadioButton, QSlider, QTreeWidget, QTreeWidgetItem, QVBoxLayout)

import imatges as IM
from i18n import t


def _sha1(cami):
    h = hashlib.sha1()
    with open(cami, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def dhash(cami, mida=8):
    """Empremta perceptiva de 64 bits (diferència de brillantor entre píxels veïns)."""
    if IM.es_raw(cami):
        img = IM.carrega_qimage(cami, 64)
        im = IM.qimage_a_pil(img).convert("L")
    else:
        im = Image.open(cami)
        im.draft("L", (64, 64))
        im = ImageOps.exif_transpose(im).convert("L")
    im = im.resize((mida + 1, mida), Image.Resampling.BILINEAR)
    px = list(im.getdata()) if not hasattr(im, "get_flattened_data") else list(im.get_flattened_data())
    v = 0
    for y in range(mida):
        for x in range(mida):
            v = (v << 1) | (px[y * (mida + 1) + x] > px[y * (mida + 1) + x + 1])
    return v


class _Senyals(QObject):
    progres = pyqtSignal(int, int, str)
    fi = pyqtSignal(list)


class DialegDuplicats(QDialog):
    obre = pyqtSignal(list, int)      # llista de camins, índex
    eliminades = pyqtSignal(list)

    def __init__(self, carpeta, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("du_titol"))
        self._atura = False
        self._fil = None
        lay = QVBoxLayout(self)

        fila = QHBoxLayout()
        fila.addWidget(QLabel(t("du_carpeta")))
        self.e_carpeta = QLineEdit(carpeta or "")
        b = QPushButton("…")
        b.setFixedWidth(34)
        b.clicked.connect(self._tria)
        fila.addWidget(self.e_carpeta, 1)
        fila.addWidget(b)
        self.ch_sub = QCheckBox(t("du_subcarpetes"), checked=True)
        fila.addWidget(self.ch_sub)
        lay.addLayout(fila)

        fila = QHBoxLayout()
        self.r_exactes = QRadioButton(t("du_exactes"), checked=True)
        self.r_semblants = QRadioButton(t("du_semblants"))
        self.s_sens = QSlider(Qt.Orientation.Horizontal, minimum=0, maximum=16, value=6)
        self.s_sens.setFixedWidth(140)
        self.s_sens.setEnabled(False)
        self.s_sens.setToolTip(t("du_sensibilitat"))
        self.r_semblants.toggled.connect(self.s_sens.setEnabled)
        fila.addWidget(self.r_exactes)
        fila.addWidget(self.r_semblants)
        fila.addWidget(QLabel(t("du_sensibilitat"), objectName="suau"))
        fila.addWidget(self.s_sens)
        fila.addStretch()
        self.b_cerca = QPushButton(t("du_cerca"), objectName="primari")
        self.b_cerca.clicked.connect(self.cerca)
        fila.addWidget(self.b_cerca)
        lay.addLayout(fila)

        self.barra = QProgressBar()
        self.lbl = QLabel(objectName="suau")
        lay.addWidget(self.barra)
        lay.addWidget(self.lbl)

        self.arbre = QTreeWidget()
        self.arbre.setHeaderLabels([t("i_nom"), t("i_carpeta"), t("i_mida"), t("pi_pes"), t("pi_data")])
        self.arbre.setIconSize(QSize(72, 72))
        self.arbre.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.arbre.itemDoubleClicked.connect(self._doble_clic)
        lay.addWidget(self.arbre, 1)

        fila = QHBoxLayout()
        b1 = QPushButton(t("du_marca_auto"))
        b1.setToolTip(t("du_marca_auto_ajuda"))
        b1.clicked.connect(self.marca_auto)
        b2 = QPushButton(t("du_desmarca"))
        b2.clicked.connect(lambda: self._marca_totes(False))
        self.b_elimina = QPushButton(t("du_elimina"))
        self.b_elimina.clicked.connect(self.elimina)
        b3 = QPushButton(t("v_tanca"))
        b3.clicked.connect(self.close)
        for w in (b1, b2):
            fila.addWidget(w)
        fila.addStretch()
        fila.addWidget(self.b_elimina)
        fila.addWidget(b3)
        lay.addLayout(fila)

        self.s = _Senyals()
        self.s.progres.connect(self._progres)
        self.s.fi.connect(self._resultat)
        self.resize(1000, 700)

    def _tria(self):
        d = QFileDialog.getExistingDirectory(self, t("du_carpeta"), self.e_carpeta.text())
        if d:
            self.e_carpeta.setText(os.path.normpath(d))

    # ------------------------------------------------------------ cerca
    def cerca(self):
        if self._fil is not None:
            self._atura = True
            return
        carpeta = self.e_carpeta.text().strip()
        if not os.path.isdir(carpeta):
            return
        self.arbre.clear()
        self._atura = False
        self.b_cerca.setText(t("l_atura"))
        args = (carpeta, self.ch_sub.isChecked(), self.r_semblants.isChecked(), self.s_sens.value())
        self._fil = threading.Thread(target=self._treballa, args=args, daemon=True)
        self._fil.start()

    def _llista(self, carpeta, sub):
        res = []
        if sub:
            for arrel, dirs, fitxers in os.walk(carpeta):
                dirs[:] = [d for d in dirs if not d.startswith(("$", "."))]
                res += [os.path.join(arrel, f) for f in fitxers if IM.es_imatge(f)]
                if self._atura:
                    break
        else:
            res = [os.path.join(carpeta, f) for f in os.listdir(carpeta) if IM.es_imatge(f)]
        return res

    def _treballa(self, carpeta, sub, semblants, llindar):
        camins = self._llista(carpeta, sub)
        grups = []
        if not semblants:
            per_mida = {}
            for c in camins:
                try:
                    per_mida.setdefault(os.path.getsize(c), []).append(c)
                except OSError:
                    pass
            candidats = [c for g in per_mida.values() if len(g) > 1 for c in g]
            per_hash = {}
            for i, c in enumerate(candidats, 1):
                if self._atura:
                    break
                try:
                    per_hash.setdefault(_sha1(c), []).append(c)
                except OSError:
                    pass
                if i % 10 == 0 or i == len(candidats):
                    self.s.progres.emit(i, len(candidats), os.path.basename(c))
            grups = [g for g in per_hash.values() if len(g) > 1]
        else:
            empremtes = []
            for i, c in enumerate(camins, 1):
                if self._atura:
                    break
                try:
                    empremtes.append((c, dhash(c)))
                except Exception:
                    pass
                if i % 10 == 0 or i == len(camins):
                    self.s.progres.emit(i, len(camins), os.path.basename(c))
            pare = list(range(len(empremtes)))

            def arrel(i):
                while pare[i] != i:
                    pare[i] = pare[pare[i]]
                    i = pare[i]
                return i
            for i in range(len(empremtes)):
                if self._atura:
                    break
                hi = empremtes[i][1]
                for j in range(i + 1, len(empremtes)):
                    if (hi ^ empremtes[j][1]).bit_count() <= llindar:
                        pare[arrel(j)] = arrel(i)
            per_arrel = {}
            for i, (c, _) in enumerate(empremtes):
                per_arrel.setdefault(arrel(i), []).append(c)
            grups = [g for g in per_arrel.values() if len(g) > 1]
        self.s.fi.emit(grups)

    def _progres(self, i, n, nom):
        self.barra.setMaximum(max(1, n))
        self.barra.setValue(i)
        self.lbl.setText(f"{i} / {n}   {nom}")

    def _resultat(self, grups):
        self._fil = None
        self.b_cerca.setText(t("du_cerca"))
        self.arbre.clear()
        total = 0
        for n, g in enumerate(sorted(grups, key=len, reverse=True), 1):
            arrel = QTreeWidgetItem(self.arbre, [t("du_grup", n=n, m=len(g))])
            arrel.setFirstColumnSpanned(True)
            arrel.setExpanded(True)
            for c in g:
                w, h = IM.mida_imatge(c)
                try:
                    st = os.stat(c)
                    pes, mt = st.st_size, st.st_mtime
                    data = datetime.fromtimestamp(mt).strftime("%d/%m/%Y %H:%M")
                except OSError:
                    pes, mt, data = 0, 0, ""
                it = QTreeWidgetItem(arrel, [os.path.basename(c), os.path.dirname(c), f"{w} × {h}",
                                             f"{pes / 1024:.0f} KB", data])
                it.setData(0, Qt.ItemDataRole.UserRole, (c, w * h, pes, mt))
                it.setCheckState(0, Qt.CheckState.Unchecked)
                img = IM.carrega_qimage(c, 144)
                if not img.isNull():
                    it.setIcon(0, QIcon(QPixmap.fromImage(img)))
                total += 1
        self.lbl.setText(t("du_resultat", g=len(grups), n=total) if grups else t("du_cap"))
        self.arbre.resizeColumnToContents(0)

    # ---------------------------------------------------------- accions
    def _fills(self):
        for i in range(self.arbre.topLevelItemCount()):
            g = self.arbre.topLevelItem(i)
            yield g, [g.child(k) for k in range(g.childCount())]

    def marca_auto(self):
        """Marca totes menys la millor de cada grup (més resolució, després més pes, després la més antiga)."""
        for _, fills in self._fills():
            millor = max(fills, key=lambda it: (it.data(0, Qt.ItemDataRole.UserRole)[1],
                                                it.data(0, Qt.ItemDataRole.UserRole)[2],
                                                -it.data(0, Qt.ItemDataRole.UserRole)[3]))
            for it in fills:
                it.setCheckState(0, Qt.CheckState.Unchecked if it is millor else Qt.CheckState.Checked)

    def _marca_totes(self, v):
        for _, fills in self._fills():
            for it in fills:
                it.setCheckState(0, Qt.CheckState.Checked if v else Qt.CheckState.Unchecked)

    def elimina(self):
        marcats = [it for _, fills in self._fills() for it in fills if it.checkState(0) == Qt.CheckState.Checked]
        if not marcats:
            return
        for _, fills in self._fills():
            if fills and all(it.checkState(0) == Qt.CheckState.Checked for it in fills):
                if QMessageBox.question(self, "Xoriguer Fotos", t("du_tot_grup")) != QMessageBox.StandardButton.Yes:
                    return
                break
        if QMessageBox.question(self, "Xoriguer Fotos", t("p_elimina_n", n=len(marcats))) != QMessageBox.StandardButton.Yes:
            return
        from PyQt6.QtCore import QFile
        fets = []
        for it in marcats:
            c = it.data(0, Qt.ItemDataRole.UserRole)[0]
            if QFile.moveToTrash(c):
                fets.append(c)
                it.parent().removeChild(it)
        for i in reversed(range(self.arbre.topLevelItemCount())):
            if self.arbre.topLevelItem(i).childCount() < 2:
                self.arbre.takeTopLevelItem(i)
        self.eliminades.emit(fets)
        self.lbl.setText(t("s_fet_n", n=len(fets)))

    def _doble_clic(self, it, col):
        dades = it.data(0, Qt.ItemDataRole.UserRole)
        if not dades:
            return
        g = it.parent()
        camins = [g.child(k).data(0, Qt.ItemDataRole.UserRole)[0] for k in range(g.childCount())]
        self.obre.emit(camins, g.indexOfChild(it))

    def closeEvent(self, ev):
        self._atura = True
        super().closeEvent(ev)
