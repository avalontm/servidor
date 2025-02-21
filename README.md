# Mochi Mochi Ensenada - Backend

## Descripción
Este es el backend del sitio web de Mochi Mochi Ensenada, desarrollado con Python y Flask. Proporciona una API RESTful para gestionar datos y comunicarse con una base de datos MySQL.

## Características
- **API RESTful**: Endpoints para CRUD de productos y otros datos relevantes.
- **Conexión a MySQL**: Uso de `mysql-connector-python` para interactuar con la base de datos.
- **Autenticación con JWT**: Implementación de autenticación segura con JSON Web Tokens.
- **CORS habilitado**: Uso de `flask-cors` para permitir el acceso desde diferentes orígenes.
- **Gestión de Errores**: Manejo estructurado de excepciones y respuestas HTTP.

## Requisitos del Sistema
- Python >= 3.9
- MySQL Server
- Dependencias listadas en `requirements.txt`

## Instalación y Configuración

### Clonar el repositorio
```sh
git clone https://github.com/avalontm/servidor.git
cd servidor
```

### Crear un entorno virtual y activar
```sh
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### Instalar dependencias
```sh
pip install -r requirements.txt
```

### Configurar variables de entorno
Crea un archivo `.env` basado en el ejemplo `.env.example` y configura:
```
DB_HOST=localhost
DB_USER=tu_usuario
DB_PASSWORD=tu_contraseña
DB_NAME=mochi_db
SECRET_KEY=clave_secreta_para_jwt
```

### Ejecutar la aplicación
```sh
python app.py
```

## Endpoints Principales
- `GET /productos` - Obtener todos los productos
- `POST /productos` - Agregar un nuevo producto
- `PUT /productos/<id>` - Actualizar un producto
- `DELETE /productos/<id>` - Eliminar un producto
- `POST /login` - Autenticación de usuario

## Despliegue en Servidor VPS
1. Configurar un servidor con Ubuntu/Debian.
2. Instalar MySQL y configurar la base de datos.
3. Usar `gunicorn` y `nginx` para servir la aplicación en producción.
4. Configurar `systemd` para gestionar el servicio de Flask.

## Licencia
Este proyecto está bajo la Licencia MIT. Puedes ver más detalles en el archivo `LICENSE`.

## Contribuciones
Si deseas contribuir, por favor crea un fork del repositorio y envía un pull request con tus cambios.

## Contacto
Para más información, visita [avalontm.info](http://avalontm.info) o contacta al equipo de desarrollo.


## Configurar el Linux

```
sudo nano /etc/systemd/system/start_api.service
```

```
[Unit]
Description=Servicio para ejecutar start_app al iniciar
After=network.target

[Service]
WorkingDirectory=/home/avalontm/ftp/server
ExecStart=/bin/bash /home/avalontm/ftp/server/start_app.sh
Restart=always
User=root
Group=root

[Install]
WantedBy=multi-user.target
```

```
sudo systemctl daemon-reload
```

```
sudo systemctl enable start_api.service
```

```
sudo systemctl start start_api.service
```

```
sudo systemctl restart start_api.service
```
