"""Estrelles (0-5) i etiquetes de cada foto, guardades a %APPDATA%\\XoriguerFotos\\valoracions.json."""

import json
import os
import threading

import config

FITXER = os.path.join(config.CARPETA, "valoracions.json")
_dades = None
_bloc = threading.Lock()


def _clau(cami):
    return os.path.normcase(os.path.normpath(cami))


def _carrega():
    global _dades
    if _dades is None:
        try:
            with open(FITXER, encoding="utf-8") as f:
                _dades = json.load(f)
        except (OSError, ValueError):
            _dades = {}
    return _dades


def _desa():
    try:
        os.makedirs(config.CARPETA, exist_ok=True)
        tmp = FITXER + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_dades, f, ensure_ascii=False)
        os.replace(tmp, FITXER)
    except OSError:
        pass


def estrelles(cami):
    return _carrega().get(_clau(cami), {}).get("e", 0)


def etiquetes(cami):
    return list(_carrega().get(_clau(cami), {}).get("t", []))


def _posa(cami, camp, valor):
    d = _carrega()
    k = _clau(cami)
    e = d.get(k, {})
    if valor:
        e[camp] = valor
    else:
        e.pop(camp, None)
    if e:
        d[k] = e
    else:
        d.pop(k, None)


def posa_estrelles(camins, n):
    with _bloc:
        for c in camins:
            _posa(c, "e", int(n))
        _desa()


def posa_etiquetes(camins, llista, afegeix=False):
    with _bloc:
        for c in camins:
            noves = sorted(set(etiquetes(c)) | set(llista)) if afegeix else sorted(set(llista))
            _posa(c, "t", noves)
        _desa()


def totes_etiquetes():
    s = set()
    for e in _carrega().values():
        s.update(e.get("t", []))
    return sorted(s, key=str.lower)


def mou(vell, nou):
    """Quan una foto canvia de nom o de carpeta dins del programa."""
    with _bloc:
        d = _carrega()
        e = d.pop(_clau(vell), None)
        if e:
            d[_clau(nou)] = e
            _desa()


def copia(origen, desti):
    with _bloc:
        d = _carrega()
        e = d.get(_clau(origen))
        if e:
            d[_clau(desti)] = json.loads(json.dumps(e))
            _desa()


def text_estrelles(n):
    return "★" * n + "☆" * (5 - n) if n else ""
