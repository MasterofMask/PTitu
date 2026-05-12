@echo off
chcp 65001 >nul
title PTitu — Compilador de Instalador
echo.
echo ============================================================
echo    PTitu — Compilador de Instalador
echo    Universidad Autónoma de Ciudad Juárez
echo ============================================================
echo.
echo    Herramienta: Inno Setup 6 (open source)
echo  
echo.
echo ─────────────────────────────────────────────────────────────
echo    [1]  Verificar prerrequisitos
echo    [2]  Proceso completo  (PyInstaller + Inno Setup)
echo    [3]  Solo ejecutable   (solo PyInstaller)
echo    [4]  Solo instalador   (solo Inno Setup)
echo    [5]  Salir
echo ─────────────────────────────────────────────────────────────
echo.
set /p opcion="Elige una opción [1-5]: "

if "%opcion%"=="1" goto check
if "%opcion%"=="2" goto full
if "%opcion%"=="3" goto exe_only
if "%opcion%"=="4" goto installer_only
if "%opcion%"=="5" goto end
echo Opción no válida.
goto end

:check
echo.
python build.py --check
goto end

:full
echo.
python build.py
goto end

:exe_only
echo.
python build.py --only-exe
goto end

:installer_only
echo.
python build.py --only-installer
goto end

:end
echo.
pause