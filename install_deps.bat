@echo off
chcp 65001 >nul
echo.
echo ============================================================
echo    PTitu - Instalación de dependencias Python
echo    Universidad Autónoma de Ciudad Juárez
echo ============================================================
echo.

:: Verificar que Python esté disponible
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado en PATH.
    echo.
    echo Descarga Python 3.10 desde:
    echo   https://www.python.org/downloads/release/python-31011/
    echo.
    echo Asegúrate de marcar "Add Python to PATH" durante la instalación.
    pause
    exit /b 1
)

:: Mostrar versión de Python detectada
echo Versión de Python detectada:
python --version
echo.

:: Verificar que sea Python 3.10+
python -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>nul
if errorlevel 1 (
    echo [AVISO] Se recomienda Python 3.10. Continuando de todas formas...
    echo.
)

:: Actualizar pip
echo [1/4] Actualizando pip...
python -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo [AVISO] No se pudo actualizar pip. Continuando con la versión actual.
)
echo       OK
echo.

:: Instalar PyTorch primero (versión CPU, sin CUDA para compatibilidad máxima)
echo [2/4] Instalando PyTorch (versión CPU)...
echo       Esto puede tardar varios minutos según tu conexión...
python -m pip install torch==2.0.1 torchvision==0.15.2 --index-url https://download.pytorch.org/whl/cpu --quiet
if errorlevel 1 (
    echo [ERROR] No se pudo instalar PyTorch.
    echo         Verifica tu conexión a internet e intenta de nuevo.
    pause
    exit /b 1
)
echo       OK
echo.

:: Instalar resto de dependencias
echo [3/4] Instalando dependencias restantes...
echo       Procesamiento de imágenes, reconocimiento facial y UI...

:: Procesar requirements.txt línea por línea para mejor control de errores
python -m pip install ^
    opencv-python==4.8.1.78 ^
    Pillow==10.1.0 ^
    scikit-image==0.21.0 ^
    facenet-pytorch==2.5.3 ^
    scikit-learn==1.3.2 ^
    numpy==1.24.3 ^
    scipy==1.11.4 ^
    exifread==3.0.0 ^
    PyQt5==5.15.10 ^
    tqdm==4.66.1 ^
    python-dateutil==2.8.2 ^
    --quiet

if errorlevel 1 (
    echo [AVISO] Algunas dependencias fallaron. Revisando individualmente...
    echo.
    
    for %%p in (
        "opencv-python==4.8.1.78"
        "Pillow==10.1.0"
        "scikit-image==0.21.0"
        "facenet-pytorch==2.5.3"
        "scikit-learn==1.3.2"
        "numpy==1.24.3"
        "scipy==1.11.4"
        "exifread==3.0.0"
        "PyQt5==5.15.10"
        "tqdm==4.66.1"
        "python-dateutil==2.8.2"
    ) do (
        echo   Instalando %%p...
        python -m pip install %%p --quiet
        if errorlevel 1 (
            echo   [FALLO] %%p
        ) else (
            echo   [OK]    %%p
        )
    )
) else (
    echo       OK
)
echo.

:: Verificar instalación
echo [4/4] Verificando instalación...
python -c "
import sys
ok = []
fail = []
libs = [
    ('cv2',           'OpenCV'),
    ('PIL',           'Pillow'),
    ('torch',         'PyTorch'),
    ('torchvision',   'torchvision'),
    ('facenet_pytorch','FaceNet-PyTorch'),
    ('sklearn',       'scikit-learn'),
    ('numpy',         'NumPy'),
    ('scipy',         'SciPy'),
    ('exifread',      'ExifRead'),
    ('PyQt5',         'PyQt5'),
    ('tqdm',          'tqdm'),
]
for mod, name in libs:
    try:
        __import__(mod)
        v = getattr(sys.modules[mod], '__version__', 'OK')
        ok.append(f'  OK  {name:<22} v{v}')
    except ImportError:
        fail.append(f'  FALLO  {name}')
for l in ok:
    print(l)
for l in fail:
    print(l)
if fail:
    print()
    print('ADVERTENCIA: Algunas librerías no se instalaron.')
    sys.exit(1)
else:
    print()
    print('Todas las dependencias instaladas correctamente.')
"

if errorlevel 1 (
    echo.
    echo [AVISO] Revisa los errores anteriores.
    echo         Puedes intentar instalar manualmente las que fallaron con:
    echo         python -m pip install NOMBRE_PAQUETE
) else (
    echo.
    echo ============================================================
    echo    Instalacion completada exitosamente.
    echo    Ejecuta PTitu.exe para iniciar la aplicacion.
    echo ============================================================
)

echo.
pause