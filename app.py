# app.py
import argparse
from flask import Flask
from flask_cors import CORS
from utils.db_utils import verify_db_connection
import sys
from utils.socket_manager import socketio  # Importa socketio

# Importar los blueprints
from routes.usuario import user_bp
from routes.producto import product_bp
from routes.categoria import category_bp
from routes.inversionista import inversor_bp
from routes.openai import openai_bp
from routes.venta import venta_bp
from routes.orden import orden_bp
from routes.site import site_bp
from routes.imagen import imagen_bp

app = Flask(__name__)

# Verificar la conexión a la base de datos al iniciar la aplicación
conexion = verify_db_connection()

if conexion:
    print("Conexión a la base de datos exitosa.")
else:
    sys.exit()

# Registrar los blueprints
app.register_blueprint(user_bp, url_prefix='/api/usuario')
app.register_blueprint(product_bp, url_prefix='/api/producto')
app.register_blueprint(category_bp, url_prefix='/api/categoria')
app.register_blueprint(inversor_bp, url_prefix='/api/inversionista')
app.register_blueprint(venta_bp, url_prefix='/api/venta')
app.register_blueprint(orden_bp, url_prefix='/api/orden')
app.register_blueprint(site_bp, url_prefix='/api/site')
app.register_blueprint(imagen_bp, url_prefix='/api/imagen')
app.register_blueprint(openai_bp, url_prefix='/api/openai')

# Aplica CORS a todas las rutas
CORS(app)
# Configurar WebSockets con Flask
socketio.init_app(app)

def main():
    parser = argparse.ArgumentParser(description='Configurar parámetros del servidor Flask.')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Dirección host para ejecutar el servidor')
    parser.add_argument('--port', type=int, default=8081, help='Puerto en el que se ejecutará el servidor')
    parser.add_argument('--ssl-cert', type=str, default=None, help='Ruta del certificado SSL (opcional)')
    parser.add_argument('--ssl-key', type=str, default=None, help='Ruta de la clave privada SSL (opcional)')
    
    args = parser.parse_args()
    ssl_context = (args.ssl_cert, args.ssl_key) if args.ssl_cert and args.ssl_key else None

    app.run(debug=True, host=args.host, port=args.port, ssl_context=ssl_context)

if __name__ == '__main__':
    main()
