"""Opcions de la presentació (durada, transició, ordre, música) i reproductor de la música de fons."""

import os
import random

from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QSpinBox, QVBoxLayout)

import config
from i18n import t

AUDIO_EXT = {"mp3", "m4a", "aac", "wav", "flac", "ogg", "wma", "opus"}
TRANSICIONS = ["cap", "fosa", "llisca", "aleatoria"]


def tria_transicio():
    tr = config.get("transicio") or "fosa"
    return random.choice(["fosa", "llisca"]) if tr == "aleatoria" else tr


class Musica:
    """Música de fons en bucle (un fitxer o totes les cançons d'una carpeta)."""

    def __init__(self):
        self.jugador = None
        self.llista = []
        self.i = 0

    def comenca(self):
        font = config.get("musica") or ""
        if not font or not os.path.exists(font):
            return
        if os.path.isdir(font):
            self.llista = [os.path.join(font, f) for f in sorted(os.listdir(font))
                           if os.path.splitext(f)[1][1:].lower() in AUDIO_EXT]
            if config.get("musica_aleatoria"):
                random.shuffle(self.llista)
        else:
            self.llista = [font]
        if not self.llista:
            return
        try:
            from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
        except ImportError:
            return
        if self.jugador is None:
            self.jugador = QMediaPlayer()
            self.sortida = QAudioOutput()
            self.jugador.setAudioOutput(self.sortida)
            self.jugador.mediaStatusChanged.connect(self._estat)
        self.sortida.setVolume((config.get("musica_volum") or 70) / 100)
        self.i = 0
        self._toca()

    def _toca(self):
        self.jugador.setSource(QUrl.fromLocalFile(self.llista[self.i]))
        self.jugador.play()

    def _estat(self, estat):
        from PyQt6.QtMultimedia import QMediaPlayer
        if estat == QMediaPlayer.MediaStatus.EndOfMedia and self.llista:
            self.i = (self.i + 1) % len(self.llista)
            self._toca()

    def atura(self):
        if self.jugador is not None:
            self.jugador.stop()


class DialegPresentacio(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("pr_titol"))
        lay = QVBoxLayout(self)
        f = QFormLayout()
        self.s_seg = QSpinBox(minimum=1, maximum=120, value=int(config.get("segons_presentacio")), suffix=" s")
        f.addRow(t("a_segons"), self.s_seg)
        self.c_tr = QComboBox()
        for k in TRANSICIONS:
            self.c_tr.addItem(t("tr_" + k), k)
        self.c_tr.setCurrentIndex(max(0, self.c_tr.findData(config.get("transicio") or "fosa")))
        f.addRow(t("pr_transicio"), self.c_tr)
        self.ch_bucle = QCheckBox(t("pr_bucle"), checked=config.get("presentacio_bucle") is not False)
        f.addRow("", self.ch_bucle)
        self.ch_aleat = QCheckBox(t("pr_aleatori"), checked=bool(config.get("presentacio_aleatoria")))
        f.addRow("", self.ch_aleat)
        fila = QHBoxLayout()
        self.e_mus = QLineEdit(config.get("musica") or "")
        self.e_mus.setPlaceholderText(t("pr_sense_musica"))
        b1 = QPushButton(t("pr_canco"))
        b1.clicked.connect(self._tria_fitxer)
        b2 = QPushButton(t("i_carpeta"))
        b2.clicked.connect(self._tria_carpeta)
        fila.addWidget(self.e_mus, 1)
        fila.addWidget(b1)
        fila.addWidget(b2)
        f.addRow(t("pr_musica"), fila)
        self.s_vol = QSpinBox(minimum=0, maximum=100, value=config.get("musica_volum") or 70, suffix=" %")
        f.addRow(t("pr_volum"), self.s_vol)
        self.ch_mus_aleat = QCheckBox(t("pr_musica_aleatoria"), checked=bool(config.get("musica_aleatoria")))
        f.addRow("", self.ch_mus_aleat)
        lay.addLayout(f)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Cancel).setText(t("cancel·la"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.resize(560, 280)

    def _tria_fitxer(self):
        ext = " ".join("*." + e for e in sorted(AUDIO_EXT))
        f, _ = QFileDialog.getOpenFileName(self, t("pr_musica"), "", f"{t('pr_musica')} ({ext})")
        if f:
            self.e_mus.setText(os.path.normpath(f))

    def _tria_carpeta(self):
        d = QFileDialog.getExistingDirectory(self, t("pr_musica"))
        if d:
            self.e_mus.setText(os.path.normpath(d))

    def accept(self):
        config.set("segons_presentacio", self.s_seg.value())
        config.set("transicio", self.c_tr.currentData())
        config.set("presentacio_bucle", self.ch_bucle.isChecked())
        config.set("presentacio_aleatoria", self.ch_aleat.isChecked())
        config.set("musica", self.e_mus.text().strip())
        config.set("musica_volum", self.s_vol.value())
        config.set("musica_aleatoria", self.ch_mus_aleat.isChecked())
        config.desa()
        super().accept()
