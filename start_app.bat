@echo off
SETLOCAL

REM Ruta al entorno virtual
SET VENV_DIR=%~dp0.venv

REM Verificar si el entorno virtual existe
IF NOT EXIST "%VENV_DIR%\Scripts\activate.bat" (
    echo Creando entorno virtual...
    python -m venv "%VENV_DIR%"
)

REM Activar el entorno virtual
CALL "%VENV_DIR%\Scripts\activate.bat"

REM Instalar dependencias
python -m pip install --upgrade pip
pip install -r "%~dp0requirements.txt"

REM Ejecutar la aplicación
python "%~dp0app.py"

REM Desactivar el entorno virtual (opcional en .bat, pero puedes cerrar terminal o dejarlo así)
ENDLOCAL
pause
