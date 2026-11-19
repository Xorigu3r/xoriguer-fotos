"""Gir i mirall de JPEG SENSE PÈRDUA: només es canvia l'etiqueta d'orientació EXIF; els píxels no es toquen."""

import os
import struct
import tempfile

# nova orientació = TAULA[operació][orientació actual]  (verificat amb ImageOps.exif_transpose)
TAULA = {
    "cw":  {1: 6, 2: 7, 3: 8, 4: 5, 5: 2, 6: 3, 7: 4, 8: 1},
    "ccw": {1: 8, 2: 5, 3: 6, 4: 7, 5: 4, 6: 1, 7: 2, 8: 3},
    "180": {1: 3, 2: 4, 3: 1, 4: 2, 5: 7, 6: 8, 7: 5, 8: 6},
    "h":   {1: 2, 2: 1, 3: 4, 4: 3, 5: 6, 6: 5, 7: 8, 8: 7},
    "v":   {1: 4, 2: 3, 3: 2, 4: 1, 5: 8, 6: 7, 7: 6, 8: 5},
}
JPEG_EXT = {"jpg", "jpeg", "jpe", "jfif"}


def es_jpeg(cami):
    return os.path.splitext(cami)[1][1:].lower() in JPEG_EXT


def compon(orientacio, operacions):
    for op in operacions:
        orientacio = TAULA[op][orientacio]
    return orientacio


def _segments(dades):
    """Retorna [(posició, marcador, mida)] dels segments abans de la imatge (SOS)."""
    if dades[:2] != b"\xff\xd8":
        raise ValueError("no és un JPEG")
    i, seg = 2, []
    while i + 4 <= len(dades):
        if dades[i] != 0xFF:
            raise ValueError("JPEG malmès")
        marc = dades[i + 1]
        if marc == 0xDA:   # SOS: comencen les dades de la imatge
            break
        mida = struct.unpack(">H", dades[i + 2:i + 4])[0]
        seg.append((i, marc, mida))
        i += 2 + mida
    return seg


def llegeix_orientacio(cami):
    with open(cami, "rb") as f:
        dades = f.read(256 * 1024)
    try:
        for pos, marc, mida in _segments(dades):
            if marc == 0xE1 and dades[pos + 4:pos + 10] == b"Exif\x00\x00":
                r = _troba_etiqueta(dades, pos + 10)
                if r:
                    return r[1]
    except (ValueError, struct.error):
        pass
    return 1


def _troba_etiqueta(dades, tiff):
    """Busca l'etiqueta 0x0112 a l'IFD0. Retorna (posició del valor, valor) o None."""
    ordre = dades[tiff:tiff + 2]
    e = "<" if ordre == b"II" else ">" if ordre == b"MM" else None
    if not e:
        return None
    ifd = tiff + struct.unpack(e + "I", dades[tiff + 4:tiff + 8])[0]
    n = struct.unpack(e + "H", dades[ifd:ifd + 2])[0]
    for k in range(n):
        p = ifd + 2 + 12 * k
        etiqueta, tipus, compte = struct.unpack(e + "HHI", dades[p:p + 8])
        if etiqueta == 0x0112 and tipus == 3 and compte == 1:
            return p + 8, struct.unpack(e + "H", dades[p + 8:p + 10])[0], e
    return None


def posa_orientacio(cami, valor):
    """Escriu l'orientació al fitxer conservant-ne la data de modificació."""
    st = os.stat(cami)
    with open(cami, "rb") as f:
        dades = bytearray(f.read())
    seg = _segments(dades)
    exif = next(((p, m) for p, m, _ in seg if m == 0xE1 and dades[p + 4:p + 10] == b"Exif\x00\x00"), None)
    if exif:
        r = _troba_etiqueta(dades, exif[0] + 10)
        if r:   # cas habitual: es canvien 2 bytes
            pos, _, e = r
            with open(cami, "r+b") as f:
                f.seek(pos)
                f.write(struct.pack(e + "H", valor))
            os.utime(cami, (st.st_atime, st.st_mtime))
            return
    # no hi ha etiqueta: es refà el bloc EXIF amb Pillow (els píxels continuen intactes)
    from PIL import Image
    ex = Image.Exif()
    if exif:
        p, _ = exif
        mida = struct.unpack(">H", dades[p + 2:p + 4])[0]
        ex.load(bytes(dades[p + 4:p + 2 + mida]))
    ex[274] = valor
    nou = ex.tobytes()
    if not nou.startswith(b"Exif\x00\x00"):
        nou = b"Exif\x00\x00" + nou
    if len(nou) + 2 > 0xFFFF:
        raise ValueError("EXIF massa gran")
    bloc = b"\xff\xe1" + struct.pack(">H", len(nou) + 2) + nou
    if exif:
        p, _ = exif
        mida = struct.unpack(">H", dades[p + 2:p + 4])[0]
        dades[p:p + 2 + mida] = bloc
    else:
        pos = 2
        if seg and seg[0][1] == 0xE0:   # després del JFIF
            pos = seg[0][0] + 2 + seg[0][2]
        dades[pos:pos] = bloc
    fd, tmp = tempfile.mkstemp(suffix=".jpg", dir=os.path.dirname(os.path.abspath(cami)))
    with os.fdopen(fd, "wb") as f:
        f.write(dades)
    os.replace(tmp, cami)
    os.utime(cami, (st.st_atime, st.st_mtime))


def aplica(cami, operacions):
    """Gira/voltetja un JPEG sense pèrdua. operacions: llista de 'cw', 'ccw', '180', 'h', 'v'."""
    posa_orientacio(cami, compon(llegeix_orientacio(cami), operacions))
