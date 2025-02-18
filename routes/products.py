# routes/products.py
# Proyecto: API de Productos
# Desarrollado por: Scarleth
# Versión: 1.0.0
# Fecha de última modificación: 2025-02-15
# Descripción: API para gestionar productos en la base de datos.

import uuid as uuid_module
import os
import base64

from mysql.connector import Error
from flask import Blueprint, jsonify, request
from utils.db_utils import query
from utils.jwt_utils import token_required
from flask import jsonify, request
from werkzeug.utils import secure_filename
from utils.app_config import APP_PUBLIC, APP_SITE

# Definimos el directorio donde guardar las imágenes
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

products_bp = Blueprint("products", __name__)

# Función para verificar si el archivo tiene una extensión permitida
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

# Ruta para obtener un producto por UUID
@products_bp.route('/dashboard/<string:uuid>', methods=['GET'])
@token_required  # Asegura que el token sea validado antes de acceder a esta ruta
def dashboard_obtener_producto(user_id, uuid):
    """Obtiene un producto específico de la base de datos por su uuid, incluyendo el uuid de la categoría."""
    sql = """
        SELECT p.*, c.uuid AS categoria_uuid
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id
        WHERE p.uuid = %s AND p.no_disponible = 0
    """
    producto = query(sql, fetchall=False, params=(uuid,))

    if not producto:
        return jsonify({"error": "Producto no encontrado"}), 404

    # Eliminamos los campos "id" y "categoria_id" si es necesario
    producto = {key: value for key, value in producto.items() if key not in ["id", "categoria_id"]}

    return jsonify(producto)
     
# Ruta para obtener un producto por UUID
@products_bp.route('/<string:uuid>', methods=['GET'])
def obtener_producto(uuid):
    """Obtiene un producto de la base de datos por su identificador, incluyendo el uuid de la categoría."""
    sql = """
        SELECT p.*, c.uuid AS categoria_uuid
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id
        WHERE p.uuid = %s AND p.no_disponible = 0
    """
    producto = query(sql, (uuid,))

    if not producto:
        return jsonify({"error": "Producto no encontrado"}), 404

    # Formatear el resultado para excluir 'id' y 'categoria_id'
    producto = {key: value for key, value in producto.items() if key not in ["id", "categoria_id"]}
    
    return jsonify(producto)


@products_bp.route('/dashboard/pagina', methods=['GET'])
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
    sql = "SELECT p.*, c.uuid AS categoria_uuid FROM productos p LEFT JOIN categorias c ON p.categoria_id = c.id WHERE p.no_disponible=0"
    
    # Si se pasó un id de categoría, agregar el filtro
    if categoria_id:
        sql += " AND p.categoria_id = %s"
    
    # Agregar la paginación
    sql += " LIMIT %s OFFSET %s"
    
    # Ejecutar la consulta con los parámetros
    try:
        # Ejecutar la consulta y obtener los productos
        params = (categoria_id, productos_por_pagina, offset) if categoria_id else (productos_por_pagina, offset)
        productos = query(sql, params=params, fetchall=True)
        
        if not productos:
            return jsonify({
            "productos": productos,
            "totalPaginas": 1,
            "paginaActual": 1
        })  # Si no hay productos, devolver una lista vacía
        
        # Limpiar los productos para quitar el campo 'id' y 'categoria_id'
        productos = [
            {key: value for key, value in producto.items() if key not in ["id", "categoria_id"]}
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

@products_bp.route('/dashboard/crear', methods=['POST'])
@token_required  # Asegura que el token sea validado antes de acceder a esta ruta
def crear_producto(user_id):
    """Crea un nuevo producto en la base de datos."""
    try:
        # Obtener los datos del producto enviados en la solicitud
        data = request.get_json()

        # Validar que los campos requeridos estén presentes
        required_fields = ['nombre', 'descripcion', 'precio', 'cantidad', 'no_disponible', 'categoria_uuid']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"El campo {field} es requerido"}), 400

        # Extraer los datos del cuerpo de la solicitud
        nombre = data['nombre']
        descripcion = data['descripcion']
        precio = data['precio']
        cantidad = data['cantidad']
        no_disponible = data['no_disponible']
        categoria_uuid = data['categoria_uuid']  # Usamos el UUID de la categoría en lugar del id directamente
        imagen = data.get('imagen', None)  # Imagen es opcional (base64)

        # Paso 1: Obtener la categoría por uuid
        sql_categoria = "SELECT id FROM categorias WHERE uuid = %s"
        categoria = query(sql_categoria, (categoria_uuid,))

        if not categoria:
            return jsonify({"error": "Categoría no encontrada"}), 404

        categoria_id = categoria['id']  # Usar el id de la categoría encontrada

        # Paso 1: generamos el uuid
        uuid_producto = str(uuid_module.uuid4())  # Generar un UUID único
        
        # Paso 2: Procesar la imagen si está presente
        imagen_url = None
        if imagen:
            # Decodificar la imagen base64
            try:
                img_data = base64.b64decode(imagen.split(',')[1])  # Eliminar el prefijo 'data:image/png;base64,' si existe
            except Exception as e:
                return jsonify({"error": "Error al decodificar la imagen", "details": str(e)}), 400

            # Generar un nombre único para la imagen
            uuid_obj = uuid_module.UUID(uuid_producto)  # Convertir el string a UUID

            # Generar un nombre único para la imagen
            imagen_filename = f"{uuid_obj.hex}.png"  # Cambia la extensión si es necesario

            # Definir la ruta donde se guardará la imagen
            imagen_path = os.path.join(APP_PUBLIC, imagen_filename)

            # Guardar la imagen en el directorio
            with open(imagen_path, 'wb') as f:
                f.write(img_data)

            # Generar la URL para la imagen
            imagen_url = f"/assets/productos/{imagen_filename}"

        # Paso 3: Consulta SQL para insertar el nuevo producto
        sql_producto = """
            INSERT INTO productos (uuid, nombre, descripcion, precio, cantidad, 
                                no_disponible, categoria_id, imagen) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        query(sql_producto, (uuid_producto, nombre, descripcion, precio, cantidad, no_disponible, categoria_id, imagen_url), commit=True)

        # Responder con éxito
        return jsonify({"status": True, "message": "Producto creado con éxito"}), 201

    except Exception as e:
        return jsonify({"error": "Error al crear el producto", "details": str(e)}), 500


@products_bp.route('/dashboard/<string:uuid>', methods=['PUT'])
@token_required  # Asegura que el token sea validado antes de acceder a esta ruta
def actualizar_producto(user_id, uuid):
    """Actualiza un producto en la base de datos."""
    try:
        # Obtener los datos del producto enviados en la solicitud
        data = request.get_json()

        # Validar que los campos requeridos estén presentes
        required_fields = ['nombre', 'descripcion', 'precio', 'cantidad', 'no_disponible', 'categoria_uuid']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"El campo {field} es requerido"}), 400

        # Extraer los datos del cuerpo de la solicitud
        nombre = data['nombre']
        descripcion = data['descripcion']
        precio = data['precio']
        cantidad = data['cantidad']
        no_disponible = data['no_disponible']
        categoria_uuid = data['categoria_uuid']  # Usamos el UUID de la categoría en lugar del id directamente
        imagen = data.get('imagen', None)  # Imagen es opcional

        # Paso 1: Obtener la categoría por uuid
        sql_categoria = "SELECT id FROM categorias WHERE uuid = %s"
        categoria = query(sql_categoria, (categoria_uuid,))

        if not categoria:
            return jsonify({"error": "Categoría no encontrada"}), 404

        categoria_id = categoria['id']  # Usar el id de la categoría encontrada

        # Paso 2: Procesar la imagen si está presente
        imagen_url = None
        if imagen:
          
            # Decodificar la imagen base64
            img_data = base64.b64decode(imagen.split(',')[1])  # Eliminar el prefijo 'data:image/png;base64,' si existe

            # Generar un nombre único para la imagen
            uuid_obj = uuid_module.UUID(uuid)  # Convertir el string a UUID
            imagen_nombre = f"{uuid_obj.hex}.png"  # Puedes cambiar la extensión según el tipo de imagen

            # Definir la ruta donde se guardará la imagen
            imagen_path = os.path.join(APP_PUBLIC, imagen_nombre)

            # Guardar la imagen en el directorio
            with open(imagen_path, 'wb') as f:
                f.write(img_data)

            # Generar la URL para la imagen (ajusta esto según tu configuración)
            imagen_url = f"/assets/productos/{imagen_nombre}"
            
        # Paso 3: Consulta SQL para actualizar el producto
        sql_producto = """
            UPDATE productos 
            SET nombre = %s, descripcion = %s, precio = %s, cantidad = %s, 
                no_disponible = %s, categoria_id = %s, imagen = %s
            WHERE uuid = %s
        """

        # Ejecutar la consulta para actualizar el producto
        producto = query(sql_producto, (nombre, descripcion, precio, cantidad, no_disponible, categoria_id, imagen_url, uuid), commit=True)
       
        print(producto)
        # Responder con éxito
        return jsonify({"status": True, "message": "Producto actualizado con éxito"}), 200
    
    except Exception as e:
        print(e)
        return jsonify({"error": "Error al actualizar el producto"}), 500


@products_bp.route('/dashboard/<string:uuid>', methods=['DELETE'])
@token_required  # Asegura que el token sea validado antes de acceder a esta ruta
def eliminar_producto(user_id, uuid):
    """Elimina un producto de la base de datos por su UUID."""
    try:
        # Paso 1: Verificar si el producto existe
        sql_verificar = "SELECT id FROM productos WHERE uuid = %s"
        producto = query(sql_verificar, (uuid,))

        if not producto:
            return jsonify({"error": "Producto no encontrado"}), 404

        # Paso 2: Eliminar el producto
        sql_eliminar = "DELETE FROM productos WHERE uuid = %s"
        query(sql_eliminar, (uuid,), commit=True)

        return jsonify({"status": True, "message": "Producto eliminado con éxito"}), 200

    except Exception as e:
        return jsonify({"error": "Error al eliminar el producto", "details": str(e)}), 500
