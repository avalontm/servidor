# routes/products.py
# Proyecto: API de Productos
# Desarrollado por: Scarleth
# Versión: 1.0.0
# Fecha de última modificación: 2025-02-15
# Descripción: API para gestionar productos en la base de datos.

import uuid as uuid_module
import os
import base64

import mysql
from mysql.connector import Error
from flask import Blueprint, jsonify, render_template, request
import mysql.connector
from exeptions.DatabaseErrorException import DatabaseErrorException
from utils.db_utils import get_user_access, query
from utils.jwt_utils import token_required
from flask import jsonify, request
from werkzeug.utils import secure_filename
from utils.app_config import APP_PUBLIC, APP_SITE

# Definimos el directorio donde guardar las imágenes
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

product_bp = Blueprint("producto", __name__)

# Función para verificar si el archivo tiene una extensión permitida
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@product_bp.route('/listar', methods=['GET'])
def obtener_productos():
    """Obtiene productos paginados con opción de ordenar por precio o fecha de creación y filtrar por nombre."""

    # Obtener parámetros de paginación
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 10))
        if page < 1 or limit < 1:
            raise ValueError("Los valores de 'page' y 'limit' deben ser mayores a 0")
    except ValueError:
        return jsonify({"error": "Parámetros de paginación inválidos"}), 400

    offset = (page - 1) * limit  # Calcular desde qué fila empezar

    # Obtener los parámetros de orden
    orden = request.args.get("orden", "asc").lower()
    ordenar_por = request.args.get("ordenar_por", "precio").lower()

    if orden not in ["asc", "desc"]:
        return jsonify({"error": "El parámetro 'orden' solo puede ser 'asc' o 'desc'"}), 400

    if ordenar_por not in ["precio", "fecha_creacion"]:
        return jsonify({"error": "El parámetro 'ordenar_por' solo puede ser 'precio' o 'fecha_creacion'"}), 400

    # Construir la parte de ORDER BY dinámicamente
    order_by = f"ORDER BY {ordenar_por} {orden.upper()}"

    # Obtener el término de búsqueda
    search = request.args.get("search", "").strip()

    # Construir la consulta SQL con búsqueda
    sql = "SELECT * FROM productos WHERE no_disponible=0"
    params = []

    if search:
        sql += " AND nombre LIKE %s"
        params.append(f"%{search}%")

    sql += f" {order_by} LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    productos = query(sql, params, fetchall=True)

    # Contar el total de productos disponibles con la misma búsqueda
    sql_count = "SELECT COUNT(*) as total FROM productos WHERE no_disponible=0"
    count_params = []

    if search:
        sql_count += " AND nombre LIKE %s"
        count_params.append(f"%{search}%")

    count_params = count_params if count_params else None
    total_result = query(sql_count, count_params)
    total_productos = total_result["total"] if total_result else 0  # Extraer el número correcto
    has_more = (page * limit) < total_productos

    # Formatear la respuesta
    productos = [
        {key: value for key, value in producto.items() if key != "id"}
        for producto in productos
    ]

    return jsonify({
        "productos": productos,
        "page": page,
        "limit": limit,
        "has_more": has_more
    })


# Ruta para obtener un producto por UUID
@product_bp.route('/panel/<string:uuid>', methods=['GET'])
@token_required  # Asegura que el token sea validado antes de acceder a esta ruta
def dashboard_obtener_producto(user_id, uuid):
    """Obtiene un producto específico de la base de datos por su uuid, incluyendo el uuid de la categoría e inversionistas asociados."""
    sql = """
        SELECT p.*, c.uuid AS categoria_uuid, i.uuid AS inversionista_uuid
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id
        LEFT JOIN inversionistas i ON p.inversionista_id = i.id
        WHERE p.uuid = %s AND p.no_disponible = 0
    """
    producto = query(sql, fetchall=False, params=(uuid,))

    if not producto:
        return jsonify({"error": "Producto no encontrado"}), 404

    # Eliminamos campos no deseados
    producto = {key: value for key, value in producto.items() if key not in ["id", "categoria_id", "inversionista_id"]}

    return jsonify(producto)

     
# Ruta para obtener un producto por UUID
@product_bp.route('/<string:uuid>', methods=['GET'])
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

    # Detectar si el usuario es un bot de redes sociales
    user_agent = request.headers.get('User-Agent', '').lower()
    if any(bot in user_agent for bot in ["twitterbot", "facebookexternalhit", "whatsapp", "slackbot"]):
        return render_template("producto.html", producto=producto)

    # Respuesta normal en JSON para el frontend React
    return jsonify(producto)

# Ruta para renderizar el producto como HTML si es un bot
@product_bp.route('/render/<string:uuid>', methods=['GET'])
def renderizar_producto(uuid):
    """Renderiza un producto como HTML estático con meta tags para redes sociales."""

    sql = """
        SELECT p.*, c.uuid AS categoria_uuid
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id
        WHERE p.uuid = %s AND p.no_disponible = 0
    """
    producto = query(sql, (uuid,))

    if not producto:
        return "<html><head><meta name='robots' content='noindex'></head><body>Producto no encontrado</body></html>", 404

    return render_template("producto.html", producto=producto)


@product_bp.route('/panel/pagina', methods=['GET'])
@token_required  # Asegura que el token sea validado antes de acceder a esta ruta
def obtener_pagina_productos(user_id):
    """Obtiene los productos de la base de datos con paginación, filtrado por categoría y búsqueda por nombre."""
    
    access = get_user_access(user_id)

    if access != "admin":
        return jsonify({"error": "No tiene permisos para realizar esta acción"}), 403

    # Obtener los parámetros de la consulta
    page = int(request.args.get('page', 1))  # Página actual (por defecto 1)
    categoria_uuid = request.args.get('categoria', None)  # UUID de la categoría seleccionada (si existe)
    search_term = request.args.get('buscar', '')  # Término de búsqueda (por defecto vacío)
    
    # Número de productos por página
    productos_por_pagina = 50  # maximo deproductos por pagina
    offset = (page - 1) * productos_por_pagina  # Calcular el OFFSET
    
    # Obtener el id de la categoría a partir de su uuid
    categoria_id = None
    if categoria_uuid and not search_term:  # Solo filtrar por categoría si no hay búsqueda
        sql_categoria = "SELECT id FROM categorias WHERE uuid = %s ORDER BY nombre ASC"
        categoria_resultado = query(sql_categoria, params=(categoria_uuid,))

        if categoria_resultado:
            categoria_id = categoria_resultado['id']
        else:
            return jsonify({"error": "Categoría no encontrada"}), 404  # Si no se encuentra la categoría
    
    # Construir la consulta SQL para los productos
    sql = "SELECT p.*, c.uuid AS categoria_uuid FROM productos p LEFT JOIN categorias c ON p.categoria_id = c.id WHERE p.no_disponible=0"
    
    # Si se pasó un id de categoría y no hay búsqueda, agregar el filtro
    if categoria_id and not search_term:
        sql += " AND p.categoria_id = %s"
    
    # Si se pasó un término de búsqueda, agregar el filtro solo al nombre (sin importar la categoría)
    if search_term:
        sql += " AND p.nombre LIKE %s"  # Filtro solo por nombre
    
    sql += " ORDER BY p.id DESC"
    
    # Agregar la paginación
    sql += " LIMIT %s OFFSET %s"
    
    # Ejecutar la consulta con los parámetros
    try:
        # Ejecutar la consulta y obtener los productos
        params = (
            f"%{search_term}%", productos_por_pagina, offset
        ) if search_term else (
            productos_por_pagina, offset
        )
        if categoria_id and not search_term:
            params = (categoria_id, productos_por_pagina, offset)

        productos = query(sql, params=(params), fetchall=True)
        
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
        
        # Construir la consulta para contar los productos
        sql_count = "SELECT COUNT(*) AS total FROM productos p WHERE p.no_disponible=0"

        # Si hay categoría, agregar el filtro por categoría
        if categoria_id and not search_term:
            sql_count += " AND p.categoria_id = %s"

        # Si hay búsqueda, agregar el filtro de búsqueda
        if search_term:
            sql_count += " AND p.nombre LIKE %s"

        # Definir los parámetros correctamente
        params = ()
        if categoria_id and not search_term:
            params = (categoria_id,)
        elif search_term:
            params = (f"%{search_term}%",)

        # Ejecutar la consulta para obtener el total de productos
        total_resultados = query(sql_count, params=params, fetchall=False)['total']
        
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


@product_bp.route('/panel/crear', methods=['POST'])
@token_required  # Asegura que el token sea validado antes de acceder a esta ruta
def crear_producto(user_id):
    """Crea un nuevo producto en la base de datos."""
    
    access = get_user_access(user_id)
    
    if access != "admin":
        return jsonify({"error": "No tiene permisos para realizar esta acción"}), 403
    
    try:
        # Obtener los datos del producto enviados en la solicitud
        data = request.get_json()

        # Validar que los campos requeridos estén presentes
        required_fields = ['sku', 'nombre', 'descripcion', 'precio_unitario', 'precio', 'cantidad', 'no_disponible', 'categoria_uuid', 'inversionista_uuid', 'bandera']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"El campo {field} es requerido"}), 400

        # Extraer los datos del cuerpo de la solicitud
        sku = data['sku']
        nombre = data['nombre']
        descripcion = data['descripcion']
        precio_unitario = data['precio_unitario']
        precio = data['precio']
        cantidad = data['cantidad']
        no_disponible = data['no_disponible']
        bandera = data['bandera']  
        categoria_uuid = data['categoria_uuid']  # Usamos el UUID 
        inversionista_uuid = data['inversionista_uuid']  # Usamos el UUID
        
        imagen = data.get('imagen', None)  # Imagen es opcional (base64)

        # Paso 1: Obtener la categoría por uuid
        sql_categoria = "SELECT id FROM categorias WHERE uuid = %s"
        categoria = query(sql_categoria, (categoria_uuid,))

        if not categoria:
            return jsonify({"error": "Categoría no encontrada"}), 404

        categoria_id = categoria['id']  # Usar el id de la categoría encontrada

        # Paso 2: Obtener el inversionista por uuid
        sql_inversionista = "SELECT id FROM inversionistas WHERE uuid = %s"
        inversionista = query(sql_inversionista, (inversionista_uuid,))

        if not inversionista:
            return jsonify({"error": "Inversionista no encontrado"}), 404

        inversionista_id = inversionista['id']  # Usar el id del inversionista encontrado
        
        # Paso 3: generamos el uuid
        uuid_producto = str(uuid_module.uuid4())  # Generar un UUID único
        
        # Paso 4: Procesar la imagen si está presente
        imagen_url = None
        if imagen and "," in imagen:
            # Decodificar la imagen base64
            try:
                img_data = base64.b64decode(imagen.split(',')[1])  # Eliminar el prefijo 'data:image/png;base64,' si existe
            except Exception as e:
                img_data = None

            # Generar un nombre único para la imagen
            uuid_obj = uuid_module.UUID(uuid_producto)  # Convertir el string a UUID

            # Generar un nombre único para la imagen
            imagen_filename = f"{uuid_obj.hex}.png"  # Cambia la extensión si es necesario

            # Definir la ruta donde se guardará la imagen
            imagen_path = os.path.join(APP_PUBLIC, "productos", imagen_filename)

            # Guardar la imagen en el directorio
            if img_data:
                # Guardar la imagen en el directorio
                with open(imagen_path, 'wb') as f:
                    f.write(img_data)

            # Generar la URL para la imagen
            imagen_url = f"/assets/productos/{imagen_filename}"

        # Paso 5: Consulta SQL para insertar el nuevo producto
        sql_producto = """
            INSERT INTO productos (uuid, sku, nombre, descripcion, precio_unitario, precio, cantidad, 
                                no_disponible, categoria_id, inversionista_id, bandera, imagen) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # Verificar si el SKU ya existe
        sku_existente = query("SELECT id FROM productos WHERE sku = %s", (sku,))

        if sku_existente:
            return jsonify({"status": False, "error": "El SKU ya existe"}), 400

        try:
            # Intentamos ejecutar la consulta SQL de inserción
            rows_affected = query(sql_producto, (uuid_producto, sku, nombre, descripcion, precio_unitario, precio, cantidad, no_disponible, categoria_id, inversionista_id, bandera, imagen_url), commit=True)

            # Verificar si la inserción fue exitosa (al menos una fila debe haber sido afectada)
            if rows_affected and rows_affected > 0 :
                return jsonify({"status": True, "message": "Producto creado con éxito"}), 201
            else:
                return jsonify({"status": False, "error": "Error desconocido." }), 400

        except DatabaseErrorException as e:
            return jsonify({"status": False, "message": str(e.message)}), 500
        
        except mysql.connector.IntegrityError as ie:
            return jsonify({"status": False, "error": "Ya existe un producto con este SKU", "details": str(ie)}), 400

    except Error as e:
        return jsonify({"status": False, "error": "Error al crear el producto", "details": str(e)}), 500



@product_bp.route('/panel/<string:uuid>', methods=['PUT'])
@token_required  
def actualizar_producto(user_id, uuid):
    """Actualiza un producto en la base de datos."""
    
    access = get_user_access(user_id)
    
    if access != "admin":
        return jsonify({"error": "No tiene permisos para realizar esta acción"}), 403
    
    try:
        data = request.get_json()

        # Validar que los campos requeridos estén presentes
        required_fields = ['nombre', 'sku', 'descripcion', 'precio_unitario', 'precio', 'cantidad', 'no_disponible', 'categoria_uuid', 'inversionista_uuid', 'bandera', 'imagen']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"El campo {field} es requerido"}), 400

        # Extraer datos
        sku = data['sku']
        nombre = data['nombre']
        descripcion = data['descripcion']
        precio_unitario = data['precio_unitario']
        precio = data['precio']
        cantidad = data['cantidad']
        no_disponible = data['no_disponible']
        bandera = data['bandera']
        categoria_uuid = data['categoria_uuid']
        inversionista_uuid = data['inversionista_uuid']
        imagen = data.get('imagen', None)  

        # Obtener IDs de categoría e inversionista
        sql_categoria = "SELECT id FROM categorias WHERE uuid = %s"
        categoria = query(sql_categoria, (categoria_uuid,))
        if not categoria:
            return jsonify({"error": "Categoría no encontrada"}), 404

        sql_inversionista = "SELECT id FROM inversionistas WHERE uuid = %s"
        inversionista = query(sql_inversionista, (inversionista_uuid,))
        if not inversionista:
            return jsonify({"error": "Inversionista no encontrada"}), 404

        categoria_id = categoria['id']
        inversionista_id = inversionista['id']
        
        # Procesar la imagen si está presente
        imagen_url = None
        # Procesar la imagen solo si no está vacía y tiene el formato correcto
        if imagen and "," in imagen:
            try:
                img_data = base64.b64decode(imagen.split(',')[1])  # Decodifica solo si tiene ","
                uuid_obj = uuid_module.UUID(uuid)
                imagen_nombre = f"{uuid_obj.hex}.png"
                imagen_path = os.path.join(APP_PUBLIC,"productos", imagen_nombre)

                with open(imagen_path, 'wb') as f:
                    f.write(img_data)

                imagen_url = f"/assets/productos/{imagen_nombre}"
            except Exception as e:
                print("Error al procesar la imagen:", e)
                imagen_url = None  # No actualizar la imagen si hay error
        else:
            imagen_url = None  # No modificar si no se envió una nueva imagen

         # Verificar si el SKU ya existe
        producto = query("SELECT * FROM productos WHERE uuid = %s", (uuid,))

        if not producto:
            return jsonify({"status": False, "error": "No se encontro el producto."}), 400
        
        if producto['sku'] != sku:
            sku_existe = query("SELECT * FROM productos WHERE sku=%s AND uuid != %s", (sku, uuid,))
        
            if sku_existe:
                return jsonify({"status": False, "error": "El SKU ya existe"}),
        
        producto_id = producto['id']
            
        # SQL para actualizar producto (omite la imagen si no se actualizó)
        sql_producto = """
            UPDATE productos 
            SET sku = %s, nombre = %s, descripcion = %s, precio_unitario = %s, precio = %s, cantidad = %s, 
                no_disponible = %s, categoria_id = %s, bandera = %s, inversionista_id = %s, fecha_modificacion = NOW()
        """ + (", imagen = %s" if imagen_url else "") + " WHERE id = %s"

        # Parámetros (excluye la imagen si no se actualizó)
        params = [sku, nombre, descripcion, precio_unitario, precio, cantidad, no_disponible, categoria_id, bandera, inversionista_id]
        if imagen_url:
            params.append(imagen_url)
        params.append(producto_id)  # Agregar el ID del producto al final

        cursor = query(sql_producto, tuple(params), commit=True, return_cursor=True)

        if not cursor:
            return jsonify({"status": False, "error": "erro desconocido."}), 500

        return jsonify({"status": True, "message": "Producto actualizado con éxito"}), 200

    except DatabaseErrorException as e:
            return jsonify({"status": False, "message": str(e.message)}), 500
    except Exception as e:
        return jsonify({"error": "Error al actualizar el producto"}), 500


@product_bp.route('/panel/<string:uuid>', methods=['DELETE'])
@token_required  # Asegura que el token sea validado antes de acceder a esta ruta
def eliminar_producto(user_id, uuid):
    """Elimina un producto de la base de datos por su UUID."""
    
    access = get_user_access(user_id)
    
    if access != "admin":
        return jsonify({'status': False, "error": "No tiene permisos para realizar esta acción"}), 403
    
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
