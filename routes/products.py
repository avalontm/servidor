# routes/products.py
# Proyecto: API de Productos
# Desarrollado por: Scarleth
# Versión: 1.0.0
# Fecha de última modificación: 2025-02-15
# Descripción: API para gestionar productos en la base de datos.

from mysql.connector import Error
from flask import Blueprint, jsonify

from utils.db_config import get_db_connection

def query(sql, params=None, fetchall=False):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(sql, params)
            if fetchall:
                result = cursor.fetchall()
                cursor.fetchall()  # Consumir resultados pendientes
            else:
                result = cursor.fetchone()
                cursor.fetchall()  # Consumir resultados pendientes
            return result
        except Error as e:
            print(f"Error al ejecutar la consulta: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    return None

products_bp = Blueprint("products", __name__)

@products_bp.route('/listar', methods=['GET'])
def obtener_productos():
    """Obtiene todos los productos de la base de datos."""
    sql = "SELECT * FROM productos WHERE no_disponible=0"
    productos = query(sql, fetchall=True)
    
    if not productos:
        return jsonify([])
    
    productos = [
        {key: value for key, value in producto.items() if key != "id"}
        for producto in productos
    ]
    
    return jsonify(productos)

@products_bp.route('/<string:identifier>', methods=['GET'])
def obtener_producto(identifier):
    """Obtiene un producto de la base de datos por su identificador."""
    sql = "SELECT * FROM productos WHERE identifier=%s AND no_disponible=0"
    producto = query(sql, (identifier,))
    
    if not producto:
        return jsonify({"error": "Producto no encontrado"}), 404
    
    producto = {key: value for key, value in producto.items() if key != "id"}
    return jsonify(producto)