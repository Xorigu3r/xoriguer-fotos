@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   Compilant Xoriguer Fotos
echo ============================================
py -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto error

py -m PyInstaller --noconfirm --clean XoriguerFotos.spec
if errorlevel 1 goto error
echo.
echo [OK] Programa creat a: dist\XoriguerFotos\XoriguerFotos.exe

set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist %ISCC% (
    echo Creant l'instal.lador amb Inno Setup...
    %ISCC% XoriguerFotos_Setup.iss
    if errorlevel 1 goto error
    echo [OK] Instal.lador creat: XoriguerFotos_Setup_v1.1.exe
) else (
    echo Inno Setup 6 no trobat: nomes s'ha creat la carpeta dist\XoriguerFotos.
)
if not "%1"=="/q" pause
exit /b 0

:error
echo.
echo [ERROR] La compilacio ha fallat. Revisa els missatges de dalt.
if not "%1"=="/q" pause
exit /b 1
