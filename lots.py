"""Conversió i canvi de mida per lots."""

import os
import threading

from PIL import Image

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                             QMessageBox, QProgressBar, QPushButton, QSpinBox, QVBoxLayout)

import config
import editor
import imatges as IM
from i18n import t

FORMATS = [("", None), ("JPEG", "jpg"), ("PNG", "png"), ("WebP", "webp"), ("BMP", "bmp"), ("TIFF", "tif")]


class _Senyals(QObject):
    progres = pyqtSignal(int, str)
    fi = pyqtSignal(int, list)


class DialegLots(QDialog):
    def __init__(self, camins, carpeta, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("l_titol"))
        self.camins = list(camins)
        self._atura = False
        cfg = config.get("lots") or {}
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(t("l_n_fitxers", n=len(self.camins)), objectName="titol"))

        f = QFormLayout()
        self.c_format = QComboBox()
        for nom, ext in FORMATS:
            self.c_format.addItem(nom or t("l_mateix_format"), ext)
        self.c_format.setCurrentIndex(cfg.get("format", 1))
        f.addRow(t("l_format"), self.c_format)

        self.s_qualitat = QSpinBox(minimum=30, maximum=100, value=cfg.get("qualitat", config.get("qualitat_jpeg")))
        f.addRow(t("l_qualitat"), self.s_qualitat)

        fila = QHBoxLayout()
        self.ch_mida = QCheckBox(t("l_redimensiona"), checked=cfg.get("redimensiona", False))
        self.s_costat = QSpinBox(minimum=16, maximum=20000, value=cfg.get("costat", 1920), suffix=" px")
        self.ch_amplia = QCheckBox(t("l_no_amplia"), checked=True)
        fila.addWidget(self.ch_mida)
        fila.addWidget(self.s_costat)
        fila.addWidget(self.ch_amplia)
        f.addRow(t("l_mida"), fila)

        self.e_nom = QLineEdit(cfg.get("patro", "{nom}"))
        self.e_nom.setToolTip(t("l_patro_ajuda"))
        f.addRow(t("l_patro"), self.e_nom)
        f.addRow("", QLabel(t("l_patro_ajuda"), objectName="suau", wordWrap=True))

        fila = QHBoxLayout()
        self.e_desti = QLineEdit(cfg.get("desti") or os.path.join(carpeta, "convertides"))
        b = QPushButton("…")
        b.setFixedWidth(36)
        b.clicked.connect(self._tria_desti)
        fila.addWidget(self.e_desti)
        fila.addWidget(b)
        f.addRow(t("l_desti"), fila)
        self.ch_exif = QCheckBox(t("l_conserva_exif"), checked=cfg.get("exif", True))
        f.addRow("", self.ch_exif)
        lay.addLayout(f)

        self.barra = QProgressBar(maximum=max(1, len(self.camins)), value=0)
        self.lbl = QLabel(objectName="suau")
        lay.addWidget(self.barra)
        lay.addWidget(self.lbl)

        botons = QHBoxLayout()
        botons.addStretch()
        self.b_tanca = QPushButton(t("v_tanca"))
        self.b_tanca.clicked.connect(self._tanca)
        self.b_inicia = QPushButton(t("l_inicia"), objectName="primari")
        self.b_inicia.clicked.connect(self.inicia)
        botons.addWidget(self.b_tanca)
        botons.addWidget(self.b_inicia)
        lay.addLayout(botons)
        self.resize(620, 380)

        self.s = _Senyals()
        self.s.progres.connect(self._progres)
        self.s.fi.connect(self._fi)
        self._fil = None

    def _tria_desti(self):
        d = QFileDialog.getExistingDirectory(self, t("l_desti"), self.e_desti.text())
        if d:
            self.e_desti.setText(d)

    def inicia(self):
        desti = self.e_desti.text().strip()
        if not desti:
            return
        opcions = dict(format=self.c_format.currentData(), qualitat=self.s_qualitat.value(),
                       redimensiona=self.ch_mida.isChecked(), costat=self.s_costat.value(),
                       no_amplia=self.ch_amplia.isChecked(), patro=self.e_nom.text() or "{nom}",
                       desti=desti, exif=self.ch_exif.isChecked())
        config.set("lots", dict(format=self.c_format.currentIndex(), qualitat=opcions["qualitat"],
                                redimensiona=opcions["redimensiona"], costat=opcions["costat"],
                                patro=opcions["patro"], desti=desti, exif=opcions["exif"]))
        try:
            os.makedirs(desti, exist_ok=True)
        except OSError as e:
            QMessageBox.warning(self, "Xoriguer Fotos", str(e))
            return
        self.b_inicia.setEnabled(False)
        self.b_tanca.setText(t("l_atura"))
        self._atura = False
        self._fil = threading.Thread(target=self._treballa, args=(opcions,), daemon=True)
        self._fil.start()

    def _treballa(self, o):
        errors, fets = [], 0
        for i, cami in enumerate(self.camins, 1):
            if self._atura:
                break
            nom, ext = os.path.splitext(os.path.basename(cami))
            ext_nova = o["format"] or ext[1:].lower()
            try:
                nou_nom = o["patro"].format(nom=nom, n=i)
            except (KeyError, ValueError, IndexError):
                nou_nom = nom
            sortida = os.path.join(o["desti"], f"{nou_nom}.{ext_nova}")
            if os.path.abspath(sortida) == os.path.abspath(cami):
                sortida = os.path.join(o["desti"], f"{nou_nom}_1.{ext_nova}")
            try:
                im = IM.obre_pil(cami)
                if o["redimensiona"]:
                    c = o["costat"]
                    if max(im.size) > c or not o["no_amplia"]:
                        r = c / max(im.size)
                        im = im.resize((max(1, round(im.width * r)), max(1, round(im.height * r))),
                                       Image.Resampling.LANCZOS)
                editor.desa(im, sortida, o["qualitat"], original=cami if o["exif"] else None)
                fets += 1
            except Exception as e:
                errors.append(f"{os.path.basename(cami)}: {e}")
            self.s.progres.emit(i, os.path.basename(cami))
        self.s.fi.emit(fets, errors)

    def _progres(self, i, nom):
        self.barra.setValue(i)
        self.lbl.setText(f"{i} / {len(self.camins)}   {nom}")

    def _fi(self, fets, errors):
        self._fil = None
        self.b_inicia.setEnabled(True)
        self.b_tanca.setText(t("v_tanca"))
        msg = t("l_fet", n=fets)
        if errors:
            msg += "\n\n" + t("l_errors") + "\n" + "\n".join(errors[:15])
        QMessageBox.information(self, "Xoriguer Fotos", msg)

    def _tanca(self):
        if self._fil is not None:
            self._atura = True
        else:
            self.accept()

    def closeEvent(self, ev):
        self._atura = True
        super().closeEvent(ev)
