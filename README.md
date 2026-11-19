# Xoriguer Fotos

Visualitzador i editor de fotos ràpid per a Windows, gratis i sense anuncis. En català, castellà, francès i anglès.

**Baixa'l:** https://xoriguer.dev/

## Què fa

- **Navegador**: arbre de carpetes, miniatures que es carreguen en paral·lel (primer les que es veuen), vista prèvia i dades EXIF.
- **Visor a pantalla completa**: precarrega les fotos veïnes, de manera que passar a la següent és instantani. Zoom al punt del ratolí,
  arrossegar, ajustar a la pantalla o 100%, girar i desar el gir, presentació, informació EXIF.
- **Editor**: girar, mirall, retallar (lliure o amb proporció), canviar la mida, brillantor, contrast, saturació, gamma,
  temperatura i nitidesa amb previsualització en directe, efectes (auto-nivells, blanc i negre, sèpia, vinyeta...), desfés i refés.
  En desar conserva les dades EXIF i el perfil de color.
- **Fitxers**: copiar o moure a una carpeta, canviar el nom, enviar a la paperera, posar com a fons d'escriptori.
- **Conversió per lots**: canvi de format (JPEG, PNG, WebP, BMP, TIFF), redimensionat i noms amb numeració.

Formats: JPG, PNG, WebP, GIF, BMP, TIFF, ICO, TGA, PSD, PCX, PPM, JPEG 2000.

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

## Compilar

Cal Python 3.12, i Inno Setup 6 per a l'instal·lador.

```
compilar.bat
```

Fa `dist\XoriguerFotos\XoriguerFotos.exe` (PyInstaller, mode carpeta perquè arrenqui més ràpid) i
`XoriguerFotos_Setup_v<versió>.exe`.

Fet amb Python, PyQt6 i Pillow. Creat per Xavier Musté.
