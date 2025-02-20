# routes/products.py
# Proyecto: API de Productos
# Desarrollado por: Scarleth
# Versión: 1.0.0
# Fecha de última modificación: 2025-02-15
# Descripción: API para gestionar productos en la base de datos.

from mysql.connector import Error
from flask import Blueprint, jsonify, request
from utils.db_utils import query
from utils.jwt_utils import token_required
from flask import jsonify, request
from werkzeug.utils import secure_filename
from utils.app_config import APP_PUBLIC, APP_SITE

# Definimos el directorio donde guardar las imágenes
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

inversor_bp = Blueprint("inversionista", __name__)


@inversor_bp.route('/listar', methods=['GET'])
@token_required  # Asegura que el token sea validado antes de acceder a esta ruta
def obtener_categorias(user_id):
    """Obtiene los inversionistas."""
    
    try:
        # Consulta SQL para obtener todas las categorías
        sql = "SELECT uuid, nombre, eliminado FROM inversionistas WHERE eliminado = 0" 
        categorias = query(sql, fetchall=True)  # Usamos fetchall porque esperamos varios resultados
        
        if not categorias:
            return jsonify([])  # Si no hay categorías, devolver una lista vacía
        
        return jsonify(categorias)  # Devolver las categorías como respuesta JSON
    
    except Error as e:
        return jsonify({"error": str(e)}), 500  # Si ocurre un error, devolver el mensaje
