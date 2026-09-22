@echo off
setlocal
cd /d "%~dp0"
set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"
"%PYTHON_EXE%" -m qaf.cli dashboard --port 0 --open
if errorlevel 1 (
  echo.
  echo No se pudo iniciar el Centro de Control. Copia este mensaje para revisarlo.
  pause
)