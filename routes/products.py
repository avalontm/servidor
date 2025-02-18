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

@products_bp.route('/<string:uuid>', methods=['GET'])
def obtener_producto(identifier):
    """Obtiene un producto de la base de datos por su identificador."""
    sql = "SELECT * FROM productos WHERE uuid=%s AND no_disponible=0"
    producto = query(sql, (identifier,))
    
    if not producto:
        return jsonify({"error": "Producto no encontrado"}), 404
    
    producto = {key: value for key, value in producto.items() if key != "id"}
    return jsonify(producto)


@products_bp.route('/pagina', methods=['GET'])
@token_required  # Asegura que el token sea validado antes de acceder a esta ruta
def obtener_pagina_productos(user_id):
    """Obtiene los productos de la base de datos con paginación y filtrado por categoría."""
    
    # Obtener los parámetros de la consulta
    page = int(request.args.get('page', 1))  # Página actual (por defecto 1)
    categoria_uuid = request.args.get('categoria', None)  # UUID de la categoría seleccionada (si existe)
    
    # Número de productos por página
    productos_por_pagina = 50  # Cambié a 50 para que traiga 50 productos
    offset = (page - 1) * productos_por_pagina  # Calcular el OFFSET
    
    # Obtener el id de la categoría a partir de su uuid
    categoria_id = None
    if categoria_uuid:
        sql_categoria = "SELECT id FROM categorias WHERE uuid = %s"
        categoria_resultado = query(sql_categoria, params=(categoria_uuid,))
        
        if categoria_resultado:
            categoria_id = categoria_resultado['id']
        else:
            return jsonify({"error": "Categoría no encontrada"}), 404  # Si no se encuentra la categoría
    
    # Construir la consulta SQL para los productos
    sql = "SELECT * FROM productos WHERE no_disponible=0"
    
    # Si se pasó un id de categoría, agregar el filtro
    if categoria_id:
        sql += " AND categoria_id = %s"
    
    # Agregar la paginación
    sql += " LIMIT %s OFFSET %s"
    
    # Ejecutar la consulta con los parámetros
    try:
        # Ejecutar la consulta y obtener los productos
        params = (categoria_id, productos_por_pagina, offset) if categoria_id else (productos_por_pagina, offset)
        productos = query(sql, params=params, fetchall=True)
        
        if not productos:
            return jsonify([])  # Si no hay productos, devolver una lista vacía
        
        # Limpiar los productos para quitar el campo 'id' si existe
        productos = [
            {key: value for key, value in producto.items() if key != "id"}
            for producto in productos
        ]
        
        # Contar el total de productos para calcular las páginas totales
        sql_count = "SELECT COUNT(*) AS total FROM productos WHERE no_disponible=0"
        if categoria_id:
            sql_count += " AND categoria_id = %s"
        
        total_resultados = query(sql_count, params=(categoria_id,) if categoria_id else None, fetchall=False)['total']
        
        # Calcular el número total de páginas
        total_paginas = (total_resultados // productos_por_pagina) + (1 if total_resultados % productos_por_pagina > 0 else 0)
        
        # Retornar los productos y la información de paginación
        return jsonify({
            "productos": productos,
            "totalPaginas": total_paginas,
            "paginaActual": page
        })
    
    except Error as e:
        return jsonify({"error": str(e)}), 500