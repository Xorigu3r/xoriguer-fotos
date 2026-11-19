"""Preferències de l'usuari a %APPDATA%\\XoriguerFotos\\config.json."""

import json
import os

CARPETA = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "XoriguerFotos")
FITXER = os.path.join(CARPETA, "config.json")

PER_DEFECTE = {
    "idioma": None,
    "carpeta": None,
    "mida_miniatura": 160,
    "ordre": "nom",
    "ordre_invers": False,
    "qualitat_jpeg": 92,
    "segons_presentacio": 4,
    "confirma_eliminar": True,
    "amplia_petites": False,
    "geometria": None,
    "splitter": None,
    "splitter_esq": None,
    "lots": {},
}

_dades = dict(PER_DEFECTE)


def carrega():
    try:
        with open(FITXER, encoding="utf-8") as f:
            _dades.update(json.load(f))
    except (OSError, ValueError):
        pass


def desa():
    try:
        os.makedirs(CARPETA, exist_ok=True)
        tmp = FITXER + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_dades, f, ensure_ascii=False, indent=1)
        os.replace(tmp, FITXER)
    except OSError:
        pass


def get(clau):
    return _dades.get(clau, PER_DEFECTE.get(clau))


def set(clau, valor):
    _dades[clau] = valor
