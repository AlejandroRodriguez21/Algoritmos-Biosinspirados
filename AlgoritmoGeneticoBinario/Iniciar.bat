@echo off
setlocal
cd /d "%~dp0"
title Laberinto evolutivo
where py >nul 2>nul
if errorlevel 1 goto python_fallback
py -3 main.py
if errorlevel 1 goto failed
exit /b 0
:python_fallback
python main.py
if errorlevel 1 goto failed
exit /b 0
:failed
echo.
echo No se pudo iniciar. Revisa el error mostrado arriba.
echo Necesitas Python 3.10 o posterior con Tcl/Tk instalado.
pause
exit /b 1
