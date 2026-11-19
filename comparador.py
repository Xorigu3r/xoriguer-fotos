"""Compara 2-4 fotos una al costat de l'altra amb el zoom i el desplaçament sincronitzats."""

import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QCheckBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

import config
import estil as E
import imatges as IM
import valoracions as VAL
from i18n import t
from visor import Llenc


class _Cel(QFrame):
    def __init__(self, cami, img, comparador):
        super().__init__()
        self.cami = cami
        self.setObjectName("cel")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(2)
        self.llenc = Llenc(self, roda_navega=False)
        self.llenc.posa_imatge(img)
        self.llenc.vista_canviada.connect(lambda: comparador.sincronitza(self))
        self.llenc.doble_clic.connect(lambda: comparador.tria(self))
        self.lbl = QLabel(wordWrap=True)
        self.lbl.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(self.llenc, 1)
        lay.addWidget(self.lbl)
        self.actualitza_text()

    def actualitza_text(self):
        ex = IM.info_exif(self.cami)
        try:
            pes = os.path.getsize(self.cami) / 1024
            pes = f"{pes / 1024:.1f} MB" if pes > 1024 else f"{pes:.0f} KB"
        except OSError:
            pes = ""
        img = self.llenc.img
        tec = "  ·  ".join(ex[k] for k in ("exposicio", "diafragma", "iso", "focal") if k in ex)
        estr = VAL.text_estrelles(VAL.estrelles(self.cami))
        self.lbl.setText(f"<b>{os.path.basename(self.cami)}</b>  <span style='color:{E.OR1}'>{estr}</span><br>"
                         f"<span style='color:{E.SOFT}'>{img.width()} × {img.height()} px  ·  {pes}"
                         f"{'  ·  ' + tec if tec else ''}</span>")

    def marca(self, actiu):
        self.setStyleSheet(f"QFrame#cel {{ border: 2px solid {E.OR1 if actiu else E.LINE}; border-radius: 6px; }}")


class Comparador(QWidget):
    eliminada = pyqtSignal(str)
    obre = pyqtSignal(str)

    def __init__(self, camins, memoria, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setObjectName("fons")
        self.setWindowTitle(t("cm_titol") + " — Xoriguer Fotos")
        self.setWindowIcon(E.icona_app())
        self.memoria = memoria
        self._sincronitzant = False
        self.cels = []
        self.actiu = None

        dalt = QHBoxLayout()
        self.ch_sinc = QCheckBox(t("cm_sincronitza"), checked=True)
        dalt.addWidget(self.ch_sinc)
        dalt.addStretch()
        dalt.addWidget(QLabel(t("cm_ajuda"), objectName="suau"))
        for txt, f in ((t("v_ajusta") + "  (F)", self.ajusta), (t("v_100") + "  (1)", lambda: self.zoom(1.0))):
            b = QPushButton(txt)
            b.clicked.connect(f)
            dalt.addWidget(b)
        b = QPushButton(t("v_tanca"))
        b.clicked.connect(self.close)
        dalt.addWidget(b)

        self.graella = QGridLayout()
        self.graella.setSpacing(6)
        lay = QVBoxLayout(self)
        lay.addLayout(dalt)
        lay.addLayout(self.graella, 1)

        for c in camins[:4]:
            self.cels.append(_Cel(c, memoria.carrega(c), self))
        self._col_loca()
        if self.cels:
            self._activa(self.cels[0])

        tecles = {"Esc": self.close, "F": self.ajusta, "1": lambda: self.zoom(1.0),
                  "+": lambda: self._zoom_pas(1), "-": lambda: self._zoom_pas(-1),
                  "Tab": self._seguent, "Del": self.elimina, "Return": self._obre_actiu}
        for k in range(6):
            tecles[f"Ctrl+{k}"] = lambda k=k: self._estrelles(k)
        for tecla, f in tecles.items():
            QShortcut(QKeySequence(tecla), self, activated=f)
        self.resize(1400, 860)

    def _col_loca(self):
        for i in reversed(range(self.graella.count())):
            self.graella.itemAt(i).widget().setParent(None)
        n = len(self.cels)
        cols = 2 if n in (2, 4) else n
        if n == 3:
            cols = 3
        for i, c in enumerate(self.cels):
            self.graella.addWidget(c, i // cols, i % cols)
            c.show()

    def _activa(self, cel):
        self.actiu = cel
        for c in self.cels:
            c.marca(c is cel)

    def tria(self, cel):
        self._activa(cel)

    def mousePressEvent(self, ev):
        super().mousePressEvent(ev)

    def sincronitza(self, origen):
        self._activa(origen)
        if self._sincronitzant or not self.ch_sinc.isChecked():
            return
        self._sincronitzant = True
        estat = origen.llenc.estat_vista()
        for c in self.cels:
            if c is not origen:
                c.llenc.posa_vista(estat)
        self._sincronitzant = False

    def ajusta(self):
        for c in self.cels:
            c.llenc.posa_ajusta()

    def zoom(self, z):
        for c in self.cels:
            self._sincronitzant = True
            c.llenc.posa_zoom(z)
            self._sincronitzant = False

    def _zoom_pas(self, s):
        if self.actiu:
            self.actiu.llenc.zoom_pas(s)

    def _seguent(self):
        if self.cels:
            i = self.cels.index(self.actiu) if self.actiu in self.cels else -1
            self._activa(self.cels[(i + 1) % len(self.cels)])

    def _estrelles(self, n):
        if self.actiu:
            VAL.posa_estrelles([self.actiu.cami], n)
            self.actiu.actualitza_text()

    def _obre_actiu(self):
        if self.actiu:
            self.obre.emit(self.actiu.cami)
            self.close()

    def elimina(self):
        if not self.actiu:
            return
        cami = self.actiu.cami
        if config.get("confirma_eliminar") and QMessageBox.question(
                self, "Xoriguer Fotos", t("p_elimina_1", nom=os.path.basename(cami))) != QMessageBox.StandardButton.Yes:
            return
        from PyQt6.QtCore import QFile
        if not QFile.moveToTrash(cami):
            QMessageBox.warning(self, "Xoriguer Fotos", t("e_no_eliminat"))
            return
        self.memoria.oblida(cami)
        self.eliminada.emit(cami)
        self.cels.remove(self.actiu)
        self.actiu.deleteLater()
        if len(self.cels) < 1:
            self.close()
            return
        self._col_loca()
        self._activa(self.cels[0])
