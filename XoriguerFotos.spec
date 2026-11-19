# -*- mode: python ; coding: utf-8 -*-
# Compilar amb:  py -m PyInstaller --noconfirm --clean XoriguerFotos.spec   (o executa compilar.bat)
# Mode carpeta (onedir): arrenca molt més ràpid que un sol .exe que s'ha de descomprimir cada vegada.

QT_FORA = ['QtNetwork', 'QtQml', 'QtQuick', 'QtWebEngineCore', 'QtWebEngineWidgets', 'QtMultimedia', 'QtPdf',
           'QtSql', 'QtTest', 'QtDesigner', 'QtHelp', 'QtOpenGL', 'QtOpenGLWidgets', 'QtPositioning', 'QtBluetooth',
           'QtNfc', 'QtSensors', 'QtSerialPort', 'QtXml', 'QtSvgWidgets', 'QtCharts']

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('fonts', 'fonts')],
    hiddenimports=['visor', 'editor', 'lots', 'i18n', 'config', 'estil', 'imatges'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas', 'scipy', 'customtkinter'] + ['PyQt6.' + m for m in QT_FORA],
    noarchive=False,
)

# treu biblioteques Qt grosses que no fem servir
FORA_DLL = ('qt6webengine', 'qt6quick', 'qt6qml', 'qt6pdf', 'qt6network', 'qt6multimedia', 'opengl32sw',
            'qt6virtualkeyboard', 'qt6opengl', 'qt6designer')
a.binaries = [b for b in a.binaries if not any(x in b[0].lower() for x in FORA_DLL)]
a.datas = [d for d in a.datas if 'translations' not in d[0].lower() or 'qtbase_' in d[0].lower()]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='XoriguerFotos',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    version='version_info.txt',
    icon='assets/XoriguerFotos.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='XoriguerFotos',
)
