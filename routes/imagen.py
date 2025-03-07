from datetime import datetime
import uuid
from flask import Blueprint, json, request, jsonify
from exeptions.DatabaseErrorException import DatabaseErrorException
from utils.jwt_utils import token_required
from utils.db_utils import get_user_access, query
from utils.app_config import APP_PUBLIC, APP_SITE
from mysql.connector import Error

imagen_bp = Blueprint('imagen', __name__)

#Ruta para obtener todas las ordenes
@imagen_bp.route('/carousel', methods=['GET'])
def get_carousel_images():
    try:
        # Consulta SQL para obtener las imágenes que no están eliminadas
        query_sql = """
            SELECT uuid, imagen
            FROM carousel
            WHERE eliminado = 0
        """
        # Ejecutar la consulta
        carousel = query(query_sql, fetchall=True)

        if not carousel:
            return jsonify([])  # Si no hay categorías, devolver una lista vacía
        
        return jsonify(carousel), 200

    except Error as e:
        # Manejo de errores de base de datos
        return jsonify({'status': 'error', 'message': str(e)}), 500