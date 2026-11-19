# Xoriguer Fotos

Visualitzador i editor de fotos ràpid per a Windows, gratis i sense anuncis. En català, castellà, francès i anglès.

**Baixa'l:** https://xoriguer.dev/

## Què fa

- **Navegador**: arbre de carpetes, miniatures que es carreguen en paral·lel, vista prèvia, EXIF, **estrelles i etiquetes**
  i **filtres** per nom, etiqueta, estrelles, càmera i mes.
- **Visor a pantalla completa**: precarrega les fotos veïnes (passar a la següent és instantani), zoom, **lupa** (G o botó de
  la roda), **GIF/WebP animats**, presentació amb **transicions i música de fons**.
  - Botó dret: menú amb totes les opcions. Vora esquerra: panell d'edició. Vora dreta: informació, EXIF, GPS i histograma.
- **Edició** dins del visor o a l'editor complet: girar i mirall (**en JPEG, sense perdre qualitat**), retallar, mida,
  llum i colors, **nivells**, **corbes**, **ulls vermells**, **text i marca d'aigua** (amb logotip), efectes, desfés i refés.
- **Compara** 2–4 fotos una al costat de l'altra amb el zoom sincronitzat.
- **Cerca duplicats**: idèntics o semblants (retocats, reduïts o recomprimits).
- **Envia per correu**: redueix les fotos i obre un correu nou amb els adjunts.
- **Fitxers**: copiar, moure, canviar el nom, paperera, fons d'escriptori, imprimir, conversió per lots.

Formats: JPG, PNG, WebP, GIF, BMP, TIFF, ICO, **HEIC/HEIF (iPhone)**, **AVIF**, **RAW** de càmera (CR2, CR3, NEF, ARW, DNG,
ORF, RW2, RAF...), TGA, PSD, PCX, PPM, JPEG 2000.

## Dreceres

| Tecla | Acció |
|---|---|
| Enter / doble clic | Obre el visor |
| ← → / roda | Foto anterior / següent |
| Ctrl + roda, + / − | Zoom |
| F / 1 / Z | Ajusta / 100% / alterna |
| R / L | Gira a la dreta / esquerra (Ctrl+S el desa) |
| E | Edita |
| S | Presentació |
| I | Informació EXIF |
| Supr | A la paperera |
| F2 | Canvia el nom |
| F11 | Pantalla completa |
| Ctrl+0…5 | Estrelles |
| T | Etiquetes |
| P | Compara les seleccionades |
| G | Lupa |
| U | Ulls vermells |
| Ctrl+L / Ctrl+M | Nivells / corbes |
| Ctrl+Shift+T | Text i marca d'aigua |
| F6 | Envia per correu |
| Ctrl+D | Cerca duplicats |

## Compilar

Cal Python 3.12, i Inno Setup 6 per a l'instal·lador.

```
compilar.bat
```

Fa `dist\XoriguerFotos\XoriguerFotos.exe` (PyInstaller, mode carpeta perquè arrenqui més ràpid) i
`XoriguerFotos_Setup_v<versió>.exe`.

Fet amb Python, PyQt6, Pillow, pillow-heif i rawpy (LibRaw). Creat per Xavier Musté.
