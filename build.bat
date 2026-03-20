@echo off
echo.
echo ============================================================
echo    CONSTRUYENDO PTitu.exe
echo ============================================================
echo.

pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PyInstaller no esta instalado.
    echo         pip install pyinstaller
    pause & exit /b 1
)

echo [1/4] Limpiando builds anteriores...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

echo [2/4] Preparando hooks...
if not exist .pyinstaller_hooks mkdir .pyinstaller_hooks

echo [3/4] Ejecutando PyInstaller (5-10 min)...
pyinstaller PTitu.spec --noconfirm --clean
if errorlevel 1 (
    echo [ERROR] PyInstaller fallo.
    pause & exit /b 1
)

echo [4/4] Copiando modelo VGG-16...
if not exist "dist\PTitu\data\models" mkdir "dist\PTitu\data\models"
if exist "data\models\vgg16_scene_classifier.pth" (
    copy "data\models\vgg16_scene_classifier.pth" "dist\PTitu\data\models\" >nul
    echo       OK
) else (
    echo [AVISO] No se encontro vgg16_scene_classifier.pth
)

echo.
echo ============================================================
echo    LISTO: dist\PTitu\PTitu.exe
echo ============================================================
pause
