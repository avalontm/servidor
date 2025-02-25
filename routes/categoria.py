# routes/category.py

from mysql.connector import Error
from flask import Blueprint, jsonify, request
from utils.db_utils import query
from utils.jwt_utils import token_required

category_bp = Blueprint("categoria", __name__)

@category_bp.route('/listar', methods=['GET'])
@token_required  # Asegura que el token sea validado antes de acceder a esta ruta
def obtener_categorias(user_id):
    """Obtiene las categorías."""
    
    try:
        # Consulta SQL para obtener todas las categorías
        sql = "SELECT * FROM categorias WHERE eliminado = 0 ORDER BY nombre ASC"  # Asegúrate de tener un campo 'activo' si solo quieres categorías activas
        categorias = query(sql, fetchall=True)  # Usamos fetchall porque esperamos varios resultados
        
        if not categorias:
            return jsonify([])  # Si no hay categorías, devolver una lista vacía
        
        # Limpiar los resultados para quitar el campo 'id' si es necesario
        categorias = [
            {key: value for key, value in categoria.items() if key != "id"}
            for categoria in categorias
        ]
        
        return jsonify(categorias)  # Devolver las categorías como respuesta JSON
    
    except Error as e:
        return jsonify({"error": str(e)}), 500  # Si ocurre un error, devolver el mensaje
