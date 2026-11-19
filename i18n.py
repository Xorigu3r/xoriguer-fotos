"""Textos en català, espanyol, francès i anglès."""

from PyQt6.QtCore import QLocale

IDIOMES = {"ca": "Català", "es": "Español", "fr": "Français", "en": "English"}
_ORDRE = ("ca", "es", "fr", "en")
_actual = "ca"

T = {
    # ---------------------------------------------------------------- menús
    "m_fitxer": ("&Fitxer", "&Archivo", "&Fichier", "&File"),
    "m_edita": ("&Edita", "&Editar", "É&dition", "&Edit"),
    "m_visualitza": ("&Visualitza", "&Ver", "&Affichage", "&View"),
    "m_eines": ("E&ines", "&Herramientas", "&Outils", "&Tools"),
    "m_idioma": ("Idioma", "Idioma", "Langue", "Language"),
    "m_ajuda": ("A&juda", "A&yuda", "A&ide", "&Help"),
    "m_mida_miniatures": ("Miniatures", "Miniaturas", "Vignettes", "Thumbnails"),

    # -------------------------------------------------------------- accions
    "a_obre_carpeta": ("Obre una carpeta", "Abrir una carpeta", "Ouvrir un dossier", "Open folder"),
    "a_obre_carpeta_curt": ("Carpeta", "Carpeta", "Dossier", "Folder"),
    "a_obre_fitxer": ("Obre una foto", "Abrir una foto", "Ouvrir une photo", "Open photo"),
    "a_lots": ("Conversió per lots", "Conversión por lotes", "Conversion par lots", "Batch convert"),
    "a_lots_curt": ("Lots", "Lotes", "Lots", "Batch"),
    "a_surt": ("Surt", "Salir", "Quitter", "Exit"),
    "a_edita": ("Edita la foto", "Editar la foto", "Modifier la photo", "Edit photo"),
    "a_edita_curt": ("Edita", "Editar", "Modifier", "Edit"),
    "a_reanomena": ("Canvia el nom", "Cambiar el nombre", "Renommer", "Rename"),
    "a_reanomena_curt": ("Nom", "Nombre", "Renommer", "Rename"),
    "a_copia_a": ("Copia a una carpeta", "Copiar a una carpeta", "Copier vers un dossier", "Copy to folder"),
    "a_copia_a_curt": ("Copia a", "Copiar a", "Copier", "Copy to"),
    "a_mou_a": ("Mou a una carpeta", "Mover a una carpeta", "Déplacer vers un dossier", "Move to folder"),
    "a_mou_a_curt": ("Mou a", "Mover a", "Déplacer", "Move to"),
    "a_elimina": ("Elimina (a la paperera)", "Eliminar (a la papelera)", "Supprimer (corbeille)", "Delete (to Recycle Bin)"),
    "a_elimina_curt": ("Elimina", "Eliminar", "Supprimer", "Delete"),
    "a_copia_imatge": ("Copia la imatge", "Copiar la imagen", "Copier l'image", "Copy image"),
    "a_selecciona_tot": ("Selecciona-ho tot", "Seleccionar todo", "Tout sélectionner", "Select all"),
    "a_visualitza": ("Mostra a pantalla completa", "Ver a pantalla completa", "Afficher en plein écran", "View full screen"),
    "a_visualitza_curt": ("Mostra", "Ver", "Afficher", "View"),
    "a_presentacio": ("Presentació", "Presentación", "Diaporama", "Slideshow"),
    "a_enrere": ("Enrere", "Atrás", "Précédent", "Back"),
    "a_endavant": ("Endavant", "Adelante", "Suivant", "Forward"),
    "a_amunt": ("Carpeta superior", "Carpeta superior", "Dossier parent", "Parent folder"),
    "a_amunt_curt": ("Amunt", "Arriba", "Haut", "Up"),
    "a_refresca": ("Actualitza", "Actualizar", "Actualiser", "Refresh"),
    "a_mes_grans": ("Miniatures més grans", "Miniaturas más grandes", "Vignettes plus grandes", "Larger thumbnails"),
    "a_mes_petites": ("Miniatures més petites", "Miniaturas más pequeñas", "Vignettes plus petites", "Smaller thumbnails"),
    "a_fons": ("Posa com a fons d'escriptori", "Poner como fondo de escritorio", "Définir comme fond d'écran", "Set as wallpaper"),
    "a_fons_curt": ("Fons", "Fondo", "Fond", "Wallpaper"),
    "a_explorador": ("Mostra a l'Explorador", "Mostrar en el Explorador", "Afficher dans l'Explorateur", "Show in Explorer"),
    "a_confirma_elim": ("Demana confirmació abans d'eliminar", "Pedir confirmación antes de eliminar",
                        "Confirmer avant de supprimer", "Confirm before deleting"),
    "a_amplia": ("Amplia les fotos petites fins a omplir la pantalla", "Ampliar las fotos pequeñas hasta llenar la pantalla",
                 "Agrandir les petites photos à la taille de l'écran", "Enlarge small photos to fill the screen"),
    "a_segons": ("Durada de cada foto a la presentació", "Duración de cada foto en la presentación",
                 "Durée de chaque photo du diaporama", "Slideshow delay per photo"),
    "a_gira_e": ("Gira a l'esquerra", "Girar a la izquierda", "Pivoter à gauche", "Rotate left"),
    "a_gira_e_curt": ("Gira ←", "Girar ←", "Pivoter ←", "Rotate ←"),
    "a_gira_d": ("Gira a la dreta", "Girar a la derecha", "Pivoter à droite", "Rotate right"),
    "a_gira_d_curt": ("Gira →", "Girar →", "Pivoter →", "Rotate →"),
    "a_dreceres": ("Dreceres de teclat", "Atajos de teclado", "Raccourcis clavier", "Keyboard shortcuts"),
    "a_quant_a": ("Quant a Xoriguer Fotos", "Acerca de Xoriguer Fotos", "À propos de Xoriguer Fotos", "About Xoriguer Fotos"),

    # ------------------------------------------------------------- ordenació
    "o_ordena": ("Ordena:", "Ordenar:", "Trier :", "Sort:"),
    "o_nom": ("Nom", "Nombre", "Nom", "Name"),
    "o_data": ("Data", "Fecha", "Date", "Date"),
    "o_mida": ("Mida", "Tamaño", "Taille", "Size"),
    "o_tipus": ("Tipus", "Tipo", "Type", "Type"),
    "o_invers": ("Ordre invers", "Orden inverso", "Ordre inverse", "Reverse order"),

    # ---------------------------------------------------------------- estat
    "s_imatges": ("{n} imatges", "{n} imágenes", "{n} images", "{n} images"),
    "s_seleccionades": ("{n} seleccionades", "{n} seleccionadas", "{n} sélectionnées", "{n} selected"),
    "s_fet_n": ("Fet: {n} fitxers", "Hecho: {n} archivos", "Terminé : {n} fichiers", "Done: {n} files"),
    "s_copiada": ("Imatge copiada al porta-retalls", "Imagen copiada al portapapeles",
                  "Image copiée dans le presse-papiers", "Image copied to clipboard"),
    "s_fons_ok": ("Fons d'escriptori canviat", "Fondo de escritorio cambiado", "Fond d'écran modifié", "Wallpaper changed"),
    "imatges": ("Imatges", "Imágenes", "Images", "Images"),

    # ---------------------------------------------------------- preguntes
    "p_elimina_1": ("Vols enviar «{nom}» a la paperera?", "¿Quieres enviar «{nom}» a la papelera?",
                    "Envoyer « {nom} » à la corbeille ?", "Send “{nom}” to the Recycle Bin?"),
    "p_elimina_n": ("Vols enviar {n} fotos a la paperera?", "¿Quieres enviar {n} fotos a la papelera?",
                    "Envoyer {n} photos à la corbeille ?", "Send {n} photos to the Recycle Bin?"),
    "p_nou_nom": ("Nom nou:", "Nombre nuevo:", "Nouveau nom :", "New name:"),
    "p_gira_n": ("Vols girar i desar {n} fotos?", "¿Quieres girar y guardar {n} fotos?",
                 "Pivoter et enregistrer {n} photos ?", "Rotate and save {n} photos?"),
    "p_desa_canvis": ("Hi ha canvis sense desar. Els vols desar?", "Hay cambios sin guardar. ¿Quieres guardarlos?",
                      "Des modifications ne sont pas enregistrées. Les enregistrer ?", "There are unsaved changes. Save them?"),

    # -------------------------------------------------------------- errors
    "e_no_carpeta": ("No es troba la carpeta:\n{cami}", "No se encuentra la carpeta:\n{cami}",
                     "Dossier introuvable :\n{cami}", "Folder not found:\n{cami}"),
    "e_no_eliminat": ("No s'ha pogut eliminar.", "No se ha podido eliminar.", "Impossible de supprimer.", "Could not delete."),
    "e_no_desat": ("No s'ha pogut desar.", "No se ha podido guardar.", "Impossible d'enregistrer.", "Could not save."),
    "e_no_obert": ("No s'ha pogut obrir la foto.", "No se ha podido abrir la foto.", "Impossible d'ouvrir la photo.",
                   "Could not open the photo."),
    "e_ja_existeix": ("Ja hi ha un fitxer que es diu «{nom}».", "Ya existe un archivo llamado «{nom}».",
                      "Un fichier « {nom} » existe déjà.", "A file named “{nom}” already exists."),
    "e_fons": ("No s'ha pogut canviar el fons.", "No se ha podido cambiar el fondo.", "Impossible de changer le fond.",
               "Could not change the wallpaper."),

    # --------------------------------------------------------------- visor
    "v_anterior": ("Anterior", "Anterior", "Précédente", "Previous"),
    "v_seguent": ("Següent", "Siguiente", "Suivante", "Next"),
    "v_ajusta": ("Ajusta a la finestra", "Ajustar a la ventana", "Ajuster à la fenêtre", "Fit to window"),
    "v_100": ("Mida real (100%)", "Tamaño real (100%)", "Taille réelle (100 %)", "Actual size (100%)"),
    "v_mes_zoom": ("Amplia", "Ampliar", "Zoom avant", "Zoom in"),
    "v_menys_zoom": ("Redueix", "Reducir", "Zoom arrière", "Zoom out"),
    "v_gira_e": ("Gira a l'esquerra", "Girar a la izquierda", "Pivoter à gauche", "Rotate left"),
    "v_gira_d": ("Gira a la dreta", "Girar a la derecha", "Pivoter à droite", "Rotate right"),
    "v_desa_gir": ("Desa el gir", "Guardar el giro", "Enregistrer la rotation", "Save rotation"),
    "v_edita": ("Edita", "Editar", "Modifier", "Edit"),
    "v_presentacio": ("Presentació", "Presentación", "Diaporama", "Slideshow"),
    "v_info": ("Informació EXIF", "Información EXIF", "Informations EXIF", "EXIF info"),
    "v_copia": ("Copia la imatge", "Copiar la imagen", "Copier l'image", "Copy image"),
    "v_elimina": ("Elimina", "Eliminar", "Supprimer", "Delete"),
    "v_pantalla": ("Pantalla completa", "Pantalla completa", "Plein écran", "Full screen"),
    "v_tanca": ("Tanca", "Cerrar", "Fermer", "Close"),
    "v_no_es_pot_obrir": ("No es pot obrir aquesta imatge", "No se puede abrir esta imagen",
                          "Impossible d'ouvrir cette image", "This image cannot be opened"),
    "v_desat": ("Desat", "Guardado", "Enregistré", "Saved"),

    "i_nom": ("Nom", "Nombre", "Nom", "Name"),
    "i_carpeta": ("Carpeta", "Carpeta", "Dossier", "Folder"),
    "i_mida": ("Mida", "Tamaño", "Dimensions", "Size"),
    "i_camera": ("Càmera", "Cámara", "Appareil", "Camera"),
    "i_objectiu": ("Objectiu", "Objetivo", "Objectif", "Lens"),
    "i_data": ("Presa", "Tomada", "Prise le", "Taken"),
    "i_exposicio": ("Exposició", "Exposición", "Exposition", "Exposure"),
    "i_diafragma": ("Diafragma", "Diafragma", "Ouverture", "Aperture"),
    "i_iso": ("ISO", "ISO", "ISO", "ISO"),
    "i_focal": ("Focal", "Focal", "Focale", "Focal length"),

    # -------------------------------------------------------------- editor
    "ed_titol": ("Editor", "Editor", "Éditeur", "Editor"),
    "ed_transforma": ("Transforma", "Transformar", "Transformer", "Transform"),
    "ed_gira_e": ("Gira ←", "Girar ←", "Pivoter ←", "Rotate ←"),
    "ed_gira_d": ("Gira →", "Girar →", "Pivoter →", "Rotate →"),
    "ed_volteja_h": ("Mirall ↔", "Espejo ↔", "Miroir ↔", "Flip ↔"),
    "ed_volteja_v": ("Mirall ↕", "Espejo ↕", "Miroir ↕", "Flip ↕"),
    "ed_mida": ("Canvia la mida", "Cambiar el tamaño", "Redimensionner", "Resize"),
    "ed_mantén_proporcio": ("Mantén la proporció", "Mantener la proporción", "Conserver les proportions",
                            "Keep aspect ratio"),
    "ed_actual": ("Mida actual: {w} × {h} px", "Tamaño actual: {w} × {h} px", "Taille actuelle : {w} × {h} px",
                  "Current size: {w} × {h} px"),
    "ed_amplada": ("Amplada", "Anchura", "Largeur", "Width"),
    "ed_alcada": ("Alçada", "Altura", "Hauteur", "Height"),
    "ed_percentatge": ("Percentatge", "Porcentaje", "Pourcentage", "Percentage"),
    "ed_retalla": ("Retalla", "Recortar", "Rogner", "Crop"),
    "ed_selecciona": ("Selecciona l'àrea", "Seleccionar el área", "Choisir la zone", "Select area"),
    "ed_lliure": ("Lliure", "Libre", "Libre", "Free"),
    "ed_aplica_retall": ("Retalla (Intro)", "Recortar (Intro)", "Rogner (Entrée)", "Crop (Enter)"),
    "ed_ajustos": ("Ajustos", "Ajustes", "Réglages", "Adjustments"),
    "aj_brillantor": ("Brillantor", "Brillo", "Luminosité", "Brightness"),
    "aj_contrast": ("Contrast", "Contraste", "Contraste", "Contrast"),
    "aj_saturacio": ("Saturació", "Saturación", "Saturation", "Saturation"),
    "aj_gamma": ("Gamma", "Gamma", "Gamma", "Gamma"),
    "aj_temperatura": ("Temperatura", "Temperatura", "Température", "Temperature"),
    "aj_nitidesa": ("Nitidesa", "Nitidez", "Netteté", "Sharpness"),
    "ed_aplica": ("Aplica", "Aplicar", "Appliquer", "Apply"),
    "ed_restableix": ("Restableix", "Restablecer", "Réinitialiser", "Reset"),
    "ed_efectes": ("Efectes", "Efectos", "Effets", "Effects"),
    "ef_auto": ("Auto-nivells", "Auto-niveles", "Niveaux auto", "Auto levels"),
    "ef_equalitza": ("Equalitza", "Ecualizar", "Égaliser", "Equalize"),
    "ef_bn": ("Blanc i negre", "Blanco y negro", "Noir et blanc", "Black & white"),
    "ef_sepia": ("Sèpia", "Sepia", "Sépia", "Sepia"),
    "ef_negatiu": ("Negatiu", "Negativo", "Négatif", "Negative"),
    "ef_enfoca": ("Enfoca", "Enfocar", "Accentuer", "Sharpen"),
    "ef_difumina": ("Difumina", "Difuminar", "Flouter", "Blur"),
    "ef_vinyeta": ("Vinyeta", "Viñeta", "Vignette", "Vignette"),
    "ed_desfes": ("Desfés", "Deshacer", "Annuler", "Undo"),
    "ed_refes": ("Refés", "Rehacer", "Rétablir", "Redo"),
    "ed_desa": ("Desa", "Guardar", "Enregistrer", "Save"),
    "ed_desa_com": ("Desa com a", "Guardar como", "Enregistrer sous", "Save as"),
    "ed_qualitat": ("Qualitat", "Calidad", "Qualité", "Quality"),
    "ed_qualitat_txt": ("Qualitat de compressió (més alta = millor i més gran):",
                        "Calidad de compresión (más alta = mejor y más grande):",
                        "Qualité de compression (plus haute = meilleure et plus lourde) :",
                        "Compression quality (higher = better and larger):"),
    "cancel·la": ("Cancel·la", "Cancelar", "Annuler", "Cancel"),

    # ---------------------------------------------------------------- lots
    "l_titol": ("Conversió per lots", "Conversión por lotes", "Conversion par lots", "Batch convert"),
    "l_n_fitxers": ("{n} fotos a convertir", "{n} fotos para convertir", "{n} photos à convertir", "{n} photos to convert"),
    "l_format": ("Format", "Formato", "Format", "Format"),
    "l_mateix_format": ("El mateix que l'original", "El mismo que el original", "Identique à l'original", "Same as original"),
    "l_qualitat": ("Qualitat JPEG/WebP", "Calidad JPEG/WebP", "Qualité JPEG/WebP", "JPEG/WebP quality"),
    "l_mida": ("Mida", "Tamaño", "Taille", "Size"),
    "l_redimensiona": ("Costat llarg màxim:", "Lado largo máximo:", "Grand côté max. :", "Max long side:"),
    "l_no_amplia": ("No ampliïs les petites", "No ampliar las pequeñas", "Ne pas agrandir les petites", "Don't enlarge small ones"),
    "l_patro": ("Nom dels fitxers", "Nombre de los archivos", "Nom des fichiers", "File names"),
    "l_patro_ajuda": ("{nom} = nom original · {n} = número (p. ex. Viatge_{n:03})",
                      "{nom} = nombre original · {n} = número (p. ej. Viaje_{n:03})",
                      "{nom} = nom d'origine · {n} = numéro (ex. Voyage_{n:03})",
                      "{nom} = original name · {n} = number (e.g. Trip_{n:03})"),
    "l_desti": ("Carpeta de destinació", "Carpeta de destino", "Dossier de destination", "Output folder"),
    "l_conserva_exif": ("Conserva les dades EXIF", "Conservar los datos EXIF", "Conserver les données EXIF", "Keep EXIF data"),
    "l_inicia": ("Converteix", "Convertir", "Convertir", "Convert"),
    "l_atura": ("Atura", "Detener", "Arrêter", "Stop"),
    "l_fet": ("S'han convertit {n} fotos.", "Se han convertido {n} fotos.", "{n} photos converties.", "{n} photos converted."),
    "l_errors": ("Errors:", "Errores:", "Erreurs :", "Errors:"),

    # --------------------------------------------------------------- ajuda
    "doble_clic": ("doble clic", "doble clic", "double-clic", "double-click"),
    "roda": ("roda", "rueda", "molette", "wheel"),
    "d_navega": ("Foto anterior / següent", "Foto anterior / siguiente", "Photo précédente / suivante", "Previous / next photo"),
    "versio": ("Versió", "Versión", "Version", "Version"),
    "quant_txt": ("Visualitzador i editor de fotos ràpid per a Windows.",
                  "Visor y editor de fotos rápido para Windows.",
                  "Visionneuse et éditeur de photos rapide pour Windows.",
                  "Fast photo viewer and editor for Windows."),
    "formats": ("Formats", "Formatos", "Formats", "Formats"),
}


def del_sistema():
    codi = QLocale.system().name()[:2].lower()
    return codi if codi in IDIOMES else "ca"


def posa(codi):
    global _actual
    _actual = codi if codi in IDIOMES else "ca"


def actual():
    return _actual


def te(clau):
    return clau in T


def t(clau, **kw):
    fila = T.get(clau)
    text = fila[_ORDRE.index(_actual)] if fila else clau
    if kw:
        try:
            text = text.format(**kw)
        except (KeyError, IndexError, ValueError):
            pass
    return text
