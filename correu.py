"""Envia fotos per correu: les redueix (opcional) i obre un missatge nou al programa de correu amb els adjunts.

Fa servir Simple MAPI (Outlook, Thunderbird, eM Client...). Si no n'hi ha cap, prepara les fotos en una carpeta,
la mostra a l'Explorador i obre un correu nou (mailto:) perquè s'hi puguin arrossegar."""

import ctypes
import os
import shutil
import tempfile
import threading
from ctypes import wintypes

from PIL import Image

from PyQt6.QtCore import QObject, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QMessageBox, QPushButton, QSpinBox, QVBoxLayout

import config
import editor
import imatges as IM
from i18n import t


class MapiRecipDescW(ctypes.Structure):
    _fields_ = [("ulReserved", wintypes.ULONG), ("ulRecipClass", wintypes.ULONG), ("lpszName", wintypes.LPWSTR),
                ("lpszAddress", wintypes.LPWSTR), ("ulEIDSize", wintypes.ULONG), ("lpEntryID", ctypes.c_void_p)]


class MapiFileDescW(ctypes.Structure):
    _fields_ = [("ulReserved", wintypes.ULONG), ("flFlags", wintypes.ULONG), ("nPosition", wintypes.ULONG),
                ("lpszPathName", wintypes.LPWSTR), ("lpszFileName", wintypes.LPWSTR), ("lpFileType", ctypes.c_void_p)]


class MapiMessageW(ctypes.Structure):
    _fields_ = [("ulReserved", wintypes.ULONG), ("lpszSubject", wintypes.LPWSTR), ("lpszNoteText", wintypes.LPWSTR),
                ("lpszMessageType", wintypes.LPWSTR), ("lpszDateReceived", wintypes.LPWSTR),
                ("lpszConversationID", wintypes.LPWSTR), ("flFlags", wintypes.ULONG),
                ("lpOriginator", ctypes.POINTER(MapiRecipDescW)), ("nRecipCount", wintypes.ULONG),
                ("lpRecips", ctypes.POINTER(MapiRecipDescW)), ("nFileCount", wintypes.ULONG),
                ("lpFiles", ctypes.POINTER(MapiFileDescW))]


MAPI_LOGON_UI, MAPI_DIALOG = 0x1, 0x8
SUCCESS, USER_ABORT = 0, 1


def mapi_envia(fitxers, assumpte, text):
    """Obre el redactor del programa de correu amb els adjunts. Retorna el codi de MAPI (0 = bé, 1 = cancel·lat)."""
    try:
        mapi = ctypes.WinDLL("mapi32.dll")
        envia = mapi.MAPISendMailW
    except (OSError, AttributeError):
        return -1
    envia.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(MapiMessageW), wintypes.ULONG, wintypes.ULONG]
    envia.restype = wintypes.ULONG
    descs = (MapiFileDescW * len(fitxers))()
    for i, f in enumerate(fitxers):
        descs[i].nPosition = 0xFFFFFFFF
        descs[i].lpszPathName = f
        descs[i].lpszFileName = os.path.basename(f)
    msg = MapiMessageW()
    msg.lpszSubject = assumpte
    msg.lpszNoteText = text
    msg.nFileCount = len(fitxers)
    msg.lpFiles = descs
    try:
        return envia(None, None, ctypes.byref(msg), MAPI_LOGON_UI | MAPI_DIALOG, 0)
    except OSError:
        return -1


class _Senyal(QObject):
    fi = pyqtSignal(int, list, str)


class DialegCorreu(QDialog):
    MIDES = [(0, "cr_original"), (800, None), (1024, None), (1600, None), (2048, None)]

    def __init__(self, camins, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("cr_titol"))
        self.camins = list(camins)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(t("cr_n", n=len(self.camins)), objectName="titol"))
        f = QFormLayout()
        self.c_mida = QComboBox()
        for px, clau in self.MIDES:
            self.c_mida.addItem(t(clau) if clau else t("cr_costat", px=px), px)
        self.c_mida.setCurrentIndex(max(0, self.c_mida.findData(config.get("correu_mida") if config.get("correu_mida") is not None else 1600)))
        self.c_mida.currentIndexChanged.connect(self._estima)
        f.addRow(t("cr_mida"), self.c_mida)
        self.s_q = QSpinBox(minimum=40, maximum=100, value=config.get("correu_qualitat") or 85)
        f.addRow(t("l_qualitat"), self.s_q)
        lay.addLayout(f)
        self.lbl = QLabel(objectName="suau", wordWrap=True)
        lay.addWidget(self.lbl)
        lay.addWidget(QLabel(t("cr_ajuda"), objectName="suau", wordWrap=True))
        fila = QHBoxLayout()
        fila.addStretch()
        b = QPushButton(t("cancel·la"))
        b.clicked.connect(self.reject)
        self.b_ok = QPushButton(t("cr_obre"), objectName="primari")
        self.b_ok.clicked.connect(self.prepara)
        fila.addWidget(b)
        fila.addWidget(self.b_ok)
        lay.addLayout(fila)
        self.s = _Senyal()
        self.s.fi.connect(self._fi)
        self._estima()
        self.resize(460, 260)

    def _estima(self):
        total = sum(os.path.getsize(c) for c in self.camins if os.path.exists(c))
        self.lbl.setText(t("cr_pes_original", mb=f"{total / 1024 / 1024:.1f}"))

    def prepara(self):
        px, q = self.c_mida.currentData(), self.s_q.value()
        config.set("correu_mida", px)
        config.set("correu_qualitat", q)
        carpeta = tempfile.mkdtemp(prefix="XoriguerFotos_correu_")
        fitxers = []
        for c in self.camins:
            nom = os.path.splitext(os.path.basename(c))[0]
            if px == 0 and IM.extensio(c) in ("jpg", "jpeg", "png", "gif", "webp"):
                desti = os.path.join(carpeta, os.path.basename(c))
                shutil.copy2(c, desti)
            else:
                im = IM.obre_pil(c)
                if px and max(im.size) > px:
                    im.thumbnail((px, px), Image.Resampling.LANCZOS)
                desti = os.path.join(carpeta, nom + ".jpg")
                editor.desa(im, desti, q, original=c)
            fitxers.append(desti)
        total = sum(os.path.getsize(f) for f in fitxers)
        self.b_ok.setEnabled(False)
        self.lbl.setText(t("cr_preparades", n=len(fitxers), mb=f"{total / 1024 / 1024:.1f}"))
        assumpte = t("cr_assumpte", n=len(fitxers))
        threading.Thread(target=lambda: self.s.fi.emit(mapi_envia(fitxers, assumpte, ""), fitxers, carpeta),
                         daemon=True).start()

    def _fi(self, codi, fitxers, carpeta):
        if codi in (SUCCESS, USER_ABORT):
            self.accept()
            return
        # sense client MAPI: carpeta a l'Explorador + correu nou buit
        import subprocess
        subprocess.Popen(["explorer", "/select,", fitxers[0]])
        QDesktopServices.openUrl(QUrl("mailto:?subject=" + QUrl.toPercentEncoding(t("cr_assumpte", n=len(fitxers))).data().decode()))
        QMessageBox.information(self, t("cr_titol"), t("cr_sense_mapi"))
        self.accept()
