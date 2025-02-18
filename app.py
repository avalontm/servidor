# app.py
from flask import Flask
from flask_cors import CORS
from utils.db_utils import verify_db_connection
import sys

# Importar los blueprints
from routes.users import users_bp
from routes.products import products_bp
from routes.category import category_bp

app = Flask(__name__)

# Verificar la conexión a la base de datos al iniciar la aplicación
conexion = verify_db_connection()

if conexion:
    print("Conexión a la base de datos exitosa.")
else:
    sys.exit()

# Registrar los blueprints
app.register_blueprint(users_bp, url_prefix='/api/user')
app.register_blueprint(products_bp, url_prefix='/api/product')
app.register_blueprint(category_bp, url_prefix='/api/category')

# Aplica CORS a todas las rutas
CORS(app)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8081)
