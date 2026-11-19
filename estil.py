"""Colors de la marca (paleta «Blau pissarra»), full d'estil Qt i icones."""

import os
import sys

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPalette, QPixmap, QTransform

BG = "#1E2A3B"
BG_A = "#24344A"
BG_B = "#1A2533"
CARD = "#27354A"
BG3 = "#31405A"
LINE = "#41506A"
SOFT = "#B9B2A5"
CREAM = "#F6EFE2"
OR1 = "#FFA82E"
OR2 = "#F2650F"


def recurs(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


QSS = f"""
* {{ font-family: 'Segoe UI'; font-size: 10pt; }}
QWidget {{ color: {CREAM}; }}
QMainWindow, QDialog, QWidget#fons {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {BG_A}, stop:1 {BG_B});
}}
QMenuBar {{ background: {BG}; border-bottom: 1px solid {LINE}; }}
QMenuBar::item {{ padding: 4px 10px; background: transparent; }}
QMenuBar::item:selected {{ background: {BG3}; color: {OR1}; border-radius: 4px; }}
QMenu {{ background: {CARD}; border: 1px solid {LINE}; padding: 4px; }}
QMenu::item {{ padding: 5px 24px 5px 24px; border-radius: 4px; }}
QMenu::item:selected {{ background: {BG3}; color: {OR1}; }}
QMenu::item:disabled {{ color: #7b8596; }}
QMenu::separator {{ height: 1px; background: {LINE}; margin: 4px 8px; }}
QToolBar {{ background: {BG}; border: none; border-bottom: 1px solid {LINE}; spacing: 2px; padding: 3px; }}
QToolBar::separator {{ background: {LINE}; width: 1px; margin: 6px 4px; }}
QToolButton {{ background: transparent; border: 1px solid transparent; border-radius: 6px; padding: 3px 6px; color: {CREAM}; }}
QToolButton:hover {{ background: {BG3}; border-color: {LINE}; }}
QToolButton:checked {{ background: {BG3}; border-color: {OR1}; color: {OR1}; }}
QToolButton:disabled {{ color: #6f7a8a; }}
QToolButton::menu-indicator {{ image: none; }}
QPushButton {{ background: {BG3}; border: 1px solid {LINE}; border-radius: 6px; padding: 6px 14px; }}
QPushButton:hover {{ border-color: {OR1}; }}
QPushButton:pressed {{ background: {LINE}; }}
QPushButton:checked {{ border-color: {OR1}; color: {OR1}; }}
QPushButton:disabled {{ color: #6f7a8a; border-color: {BG3}; }}
QPushButton#primari {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {OR1}, stop:1 {OR2});
    color: {BG_B}; font-weight: 600; border: none;
}}
QPushButton#primari:hover {{ background: {OR1}; }}
QTreeView, QListView, QTextEdit, QPlainTextEdit, QTableWidget {{
    background: {CARD}; border: 1px solid {LINE}; border-radius: 8px; outline: 0;
    selection-background-color: {BG3}; selection-color: {OR1};
}}
QTreeView::item {{ padding: 2px; }}
QTreeView::item:hover {{ background: {BG3}; }}
QTreeView::item:selected {{ background: {BG3}; color: {OR1}; }}
QHeaderView::section {{ background: {BG3}; border: none; padding: 4px; }}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {BG3}; border: 1px solid {LINE}; border-radius: 6px; padding: 3px 6px;
    selection-background-color: {OR2};
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border-color: {OR1}; }}
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{ width: 18px; border: none; background: transparent; }}
QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover {{ background: {LINE}; }}
QAbstractSpinBox::up-arrow {{ image: url(@A@/fletxa_amunt.png); width: 9px; height: 6px; }}
QAbstractSpinBox::down-arrow {{ image: url(@A@/fletxa_avall.png); width: 9px; height: 6px; }}
QComboBox::drop-down {{ width: 22px; border: none; }}
QComboBox::down-arrow {{ image: url(@A@/fletxa_combo.png); width: 10px; height: 6px; }}
QComboBox QAbstractItemView {{ background: {CARD}; border: 1px solid {LINE}; selection-background-color: {BG3}; }}
QSlider::groove:horizontal {{ height: 4px; background: {LINE}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {OR1}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {CREAM}; width: 14px; height: 14px; margin: -6px 0; border-radius: 7px; }}
QSlider::handle:horizontal:hover {{ background: {OR1}; }}
QGroupBox {{ border: 1px solid {LINE}; border-radius: 8px; margin-top: 16px; padding: 8px 6px 6px 6px; background: {CARD}; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {OR1}; font-weight: 600; }}
QStatusBar {{ background: {BG}; color: {SOFT}; border-top: 1px solid {LINE}; }}
QStatusBar QLabel {{ color: {SOFT}; }}
QSplitter::handle {{ background: {BG}; }}
QSplitter::handle:hover {{ background: {OR2}; }}
QScrollBar:vertical {{ background: transparent; width: 12px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {LINE}; border-radius: 4px; min-height: 30px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: {LINE}; border-radius: 4px; min-width: 30px; margin: 2px; }}
QScrollBar::handle:hover {{ background: {SOFT}; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ width: 0; height: 0; background: none; }}
QProgressBar {{ background: {BG3}; border: 1px solid {LINE}; border-radius: 6px; text-align: center; color: {CREAM}; }}
QProgressBar::chunk {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {OR1}, stop:1 {OR2}); border-radius: 5px; }}
QToolTip {{ background: {CARD}; color: {CREAM}; border: 1px solid {OR1}; padding: 4px; }}
QLabel#suau {{ color: {SOFT}; }}
QLabel#titol {{ color: {OR1}; font-weight: 600; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QCheckBox, QRadioButton {{ spacing: 6px; }}
"""


def aplica(app):
    app.setStyle("Fusion")
    p = QPalette()
    for rol, color in [
        (QPalette.ColorRole.Window, BG), (QPalette.ColorRole.WindowText, CREAM),
        (QPalette.ColorRole.Base, CARD), (QPalette.ColorRole.AlternateBase, BG3),
        (QPalette.ColorRole.Text, CREAM), (QPalette.ColorRole.Button, BG3),
        (QPalette.ColorRole.ButtonText, CREAM), (QPalette.ColorRole.Highlight, OR2),
        (QPalette.ColorRole.HighlightedText, CREAM), (QPalette.ColorRole.ToolTipBase, CARD),
        (QPalette.ColorRole.ToolTipText, CREAM), (QPalette.ColorRole.PlaceholderText, SOFT),
        (QPalette.ColorRole.Link, OR1),
    ]:
        p.setColor(rol, QColor(color))
    app.setPalette(p)
    app.setStyleSheet(QSS.replace("@A@", recurs("assets").replace("\\", "/")))
    QFontDatabase.addApplicationFont(recurs("fonts", "Montserrat-ExtraBold.ttf"))


# -------------------------------------------------------------- icones (glifs)
_FONT_ICONES = None


def _font_icones():
    global _FONT_ICONES
    if _FONT_ICONES is None:
        families = set(QFontDatabase.families())
        _FONT_ICONES = next((f for f in ("Segoe Fluent Icons", "Segoe MDL2 Assets") if f in families), "Segoe UI Symbol")
    return _FONT_ICONES


G = {
    "enrere": "", "endavant": "", "amunt": "", "refresca": "",
    "carpeta": "", "foto": "", "edita": "", "elimina": "",
    "gira": "", "retalla": "", "presentacio": "", "pantalla": "",
    "info": "", "meszoom": "", "menyszoom": "", "ajusta": "",
    "desa": "", "desacom": "", "desfes": "", "refes": "",
    "tanca": "", "copia": "", "mou": "", "reanomena": "",
    "ordena": "", "idioma": "", "play": "", "pausa": "",
    "lots": "", "fons": "", "anterior": "", "seguent": "",
    "volteja": "", "ajustos": "", "mida": "", "inici": "",
}


def icona(nom, color=CREAM, mida=22, mirall=False):
    pm = QPixmap(mida * 2, mida * 2)
    pm.fill(Qt.GlobalColor.transparent)
    pt = QPainter(pm)
    pt.setRenderHint(QPainter.RenderHint.Antialiasing)
    pt.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    f = QFont(_font_icones())
    f.setPixelSize(int(mida * 1.45))
    pt.setFont(f)
    if mirall:
        pt.setTransform(QTransform(-1, 0, 0, 1, pm.width(), 0))
    pt.setPen(QColor(color))
    pt.drawText(QRectF(0, 0, pm.width(), pm.height()), Qt.AlignmentFlag.AlignCenter, G.get(nom, nom))
    pt.end()
    ic = QIcon()
    ic.addPixmap(pm, QIcon.Mode.Normal)
    # versió taronja per a l'estat actiu / desactivada grisa
    for mode, col in ((QIcon.Mode.Active, OR1), (QIcon.Mode.Disabled, "#6f7a8a")):
        pm2 = QPixmap(pm.size())
        pm2.fill(Qt.GlobalColor.transparent)
        q = QPainter(pm2)
        q.drawPixmap(QPointF(0, 0), pm)
        q.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        q.fillRect(pm2.rect(), QColor(col))
        q.end()
        ic.addPixmap(pm2, mode)
    return ic


def icona_app():
    return QIcon(recurs("assets", "XoriguerFotos.ico"))
