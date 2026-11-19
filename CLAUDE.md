# Xoriguer Fotos

Visualitzador i editor de fotos ràpid, només per a Windows (estil FastStone). Python 3.12 + PyQt6 + Pillow.

- `main.py` finestra principal: arbre de carpetes, miniatures (QListView amb model propi), previsualització + EXIF.
- `imatges.py` càrrega ràpida: `CarregadorMiniatures` (cua LIFO amb fils; JPEG descodificat ja reduït amb
  `QImageReader.setScaledSize`) i `MemoriaVisor` (cau de fotos senceres + precàrrega de les veïnes).
- `visor.py` `Llenc` (zoom, arrossegar, retall) i `Visor` a pantalla completa.
- `editor.py` editor (girar, mirall, retallar, mida, ajustos amb previsualització en una còpia reduïda, efectes,
  desfés/refés) i `desa()` (fitxer temporal + `os.replace`, conserva EXIF amb orientació = 1 i perfil ICC).
- `lots.py` conversió/redimensionat per lots. `i18n.py` textos ca/es/fr/en. `estil.py` paleta «Blau pissarra» i icones
  (glifs de Segoe Fluent Icons). `config.py` preferències a `%APPDATA%\XoriguerFotos\config.json`.

Compilar: `compilar.bat` → `dist\XoriguerFotos\XoriguerFotos.exe` (mode carpeta, arrenca més ràpid) i
`XoriguerFotos_Setup_v<versió>.exe` (Inno Setup, sense permisos d'administrador; opció d'afegir-se a «Obre amb»).
En pujar de versió: `VERSIO` a `main.py`, `version_info.txt` i `MyAppVersion` a l'`.iss`.
