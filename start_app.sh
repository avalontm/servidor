#!/bin/bash

# Ruta al entorno virtual
VENV_DIR="/home/avalontm/ftp/server/myenv"

# Verificar si el entorno virtual existe, si no, crearlo
if [ ! -d "$VENV_DIR" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv "$VENV_DIR"
fi

# Activar el entorno virtual
source "$VENV_DIR/bin/activate"

# Instalar dependencias si es necesario
pip install --upgrade pip  # Asegurar que pip esté actualizado
pip install -r /home/avalontm/ftp/server/requirements.txt  # Instalar dependencias

# Ejecutar la aplicación
python3 /home/avalontm/ftp/server/app.py

# Desactivar el entorno virtual
deactivate
