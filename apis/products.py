# apis/products.py
# Esta sección está siendo desarrollada por Scarleth
from flask import Blueprint, jsonify
from mysql.connector import Error
from utils.db_utils import get_db_connection

products_bp = Blueprint('product', __name__)

# Ruta para ver todos los productos
@products_bp.route('/listar', methods=['GET'])
def obtener_productos():
    """Obtiene todos los productos de la base de datos."""
    connection = get_db_connection()

    if not connection:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500  # Retorna error si no hay conexión

    try:
        cursor = connection.cursor(dictionary=True)
        query = "SELECT * FROM productos WHERE no_disponible=0"  # Ajusta los campos según tu BD
        cursor.execute(query)
        productos = cursor.fetchall()  # Obtiene todos los productos
        
        # Excluir el campo 'id' de cada producto antes de enviarlo
        productos = [
            {key: value for key, value in producto.items() if key != "id"}
            for producto in productos
        ]
        
        return jsonify(productos)  # Retorna una lista de diccionarios con los productos
    except Error as e:
        print(f"Error al ejecutar la consulta: {e}")
        return jsonify({"error": "Error al obtener los productos"}), 500  # Retorna error si algo sale mal
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

# Ruta para ver un producto por su identificador
@products_bp.route('/<string:identifier>', methods=['GET'])
def obtener_producto(identifier):
    """Obtiene un producto de la base de datos por su identificador."""
    connection = get_db_connection()

    if not connection:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500  # Retorna error si no hay conexión

    try:
        cursor = connection.cursor(dictionary=True)
        # Query para obtener el producto por su identifier
        query = "SELECT * FROM productos WHERE identifier=%s AND no_disponible=0"
        cursor.execute(query, (identifier,))
        producto = cursor.fetchone()  # Usamos fetchone() para obtener un solo producto
        
        if not producto:
            return jsonify({"error": "Producto no encontrado"}), 404  # Si no hay producto, retornar error 404

        # Excluir el campo 'id' del producto antes de enviarlo
        producto = {key: value for key, value in producto.items() if key != "id"}
        
        return jsonify(producto)  # Retorna el producto como un diccionario
    except Error as e:
        print(f"Error al ejecutar la consulta: {e}")
        return jsonify({"error": "Error al obtener el producto"}), 500  # Retorna error si algo sale mal
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
