from datetime import datetime
import uuid as uuid_module
import base64
import os
from flask import Blueprint, json, request, jsonify
from werkzeug.utils import secure_filename
from exeptions.DatabaseErrorException import DatabaseErrorException
from utils.img_utils import procesar_imagen_destino
from utils.jwt_utils import token_required
from utils.db_utils import get_user_access, query
from utils.app_config import APP_PUBLIC, APP_SITE
from mysql.connector import Error

imagen_bp = Blueprint('imagen', __name__)

# Ruta pública para el carrusel
@imagen_bp.route('/carousel', methods=['GET'])
def get_carousel_images():
    try:
        query_sql = """
            SELECT uuid, imagen
            FROM carousel
            WHERE eliminado = 0
        """
        carousel = query(query_sql, fetchall=True)

        if not carousel:
            return jsonify([])

        return jsonify(carousel), 200

    except Error as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ================================
# PANEL ADMIN / DASHBOARD
# ================================

@imagen_bp.route('/panel/carousel/listar', methods=['GET'])
@token_required
def listar_carousel_dashboard(user_id):
    access = get_user_access(user_id)

    if access != "admin":
        return jsonify({'status': False, "error": "No tiene permisos para realizar esta acción"}), 403
    
    try:
        query_sql = """
            SELECT uuid, imagen
            FROM carousel
            WHERE eliminado = 0
        """
        carousel = query(query_sql, fetchall=True)
        
        if not carousel:
            return jsonify({'status': True, 'data': []}), 200
        
        return jsonify({'status': True, 'data': carousel}), 200
    
    except Error as e:
        return jsonify({'status': False, 'message': str(e)}), 500

@imagen_bp.route('/panel/carousel/agregar', methods=['POST'])
@token_required
def agregar_carousel_dashboard(user_id):
    try:
        access = get_user_access(user_id)

        if access != "admin":
            return jsonify({'status': False, "error": "No tiene permisos para realizar esta acción"}), 403

        # Obtener la imagen desde form-data
        imagen = request.files.get("imagen")

        if not imagen:
            return jsonify({'status': False, 'message': 'se requiere que subar una imagen.'}), 400

        # Procesar imagen si se subió
        imagen_url = None
        if imagen:
            # Generar nombre único
            uuid_str = str(uuid_module.uuid4())
            imagen_filename = f"{uuid_str}"

            imagen_url = procesar_imagen_destino(imagen, os.path.join(APP_PUBLIC, "/assets/banners"), imagen_filename)
            if imagen_url == None:
                return jsonify({"status": False, "message": "No se pudo guardar el banner"}), 500

        # Insertar en la BD
        insert_sql = """
            INSERT INTO carousel (uuid, imagen, eliminado)
            VALUES (%s, %s, 0)
        """
        query(insert_sql, (uuid_str, imagen_url), commit=True)

        return jsonify({'status': True, 'message': 'Imagen agregada correctamente'}), 201

    except Exception as e:
        return jsonify({'status': False, 'message': f'Error inesperado: {str(e)}'}), 500

     
@imagen_bp.route('/panel/carousel/eliminar/<uuid_str>', methods=['DELETE'])
@token_required
def eliminar_carousel_dashboard(user_id, uuid_str):
    access = get_user_access(user_id)

    if access != "admin":
        return jsonify({'status': False, "error": "No tiene permisos para realizar esta acción"}), 403
    
    try:
        update_sql = """
            UPDATE carousel
            SET eliminado = 1
            WHERE uuid = %s
        """
        
        affected = query(update_sql, (uuid_str,), commit=True, return_cursor=False)
        
        if affected is None:
            return jsonify({'status': False, 'message': 'Error al eliminar la imagen'}), 500
        if affected == 0:
            return jsonify({'status': False, 'message': 'Imagen no encontrada'}), 404

        return jsonify({'status': True, 'message': 'Imagen eliminada correctamente'}), 200

    except Error as e:
        return jsonify({'status': False, 'message': str(e)}), 500
    