import datetime
import uuid
from flask import Blueprint, json, request, jsonify
from utils.jwt_utils import token_required
from utils.db_utils import query
from utils.app_config import APP_PUBLIC, APP_SITE
from utils.db_utils import error_message
from mysql.connector import Error
from utils.socket_manager import nueva_orden  # Importa socketio

venta_bp = Blueprint('venta', __name__)

#Ruta para obtener todas las ordenes
@venta_bp.route('/ordenes', methods=['GET'])
@token_required
def ordenes(user_id):
    try:
        sql = """
            SELECT o.uuid, o.fecha_orden, o.numero_orden, o.tipo_entrega, o.direccion_id, o.productos, o.total, o.estado
            FROM ordenes o
            WHERE o.usuario_id = %s
            ORDER BY o.fecha_orden DESC
        """
        ordenes = query(sql, (user_id,), fetchall=True)
        return jsonify({"status": True, "ordenes": ordenes}), 200
    except Exception as e:
        return jsonify({"status": False, "message": str(e)}), 500    

#Ruta para mostrar los detalles de una orden
@venta_bp.route('/orden/<uuid>', methods=['GET'])
@token_required
def orden(uuid, user_id):
    try:
        # Obtener la orden
        sql_orden = """
            SELECT o.uuid, o.fecha_orden, o.numero_orden, o.tipo_entrega, o.direccion_id, 
                   o.productos, o.total, o.estado
            FROM ordenes o
            WHERE o.numero_orden = %s AND o.usuario_id = %s
        """
        orden = query(sql_orden, (uuid, user_id,))

        if not orden:
            return jsonify({"status": False, "message": "Orden no encontrada"}), 404

        productos_json = json.loads(orden["productos"]) if isinstance(orden["productos"], str) else orden["productos"]

        # Extraer los UUIDs de los productos
        uuids_productos = [p["uuid"] for p in productos_json]

        if uuids_productos:
            # Consultar detalles de los productos en la base de datos
            sql_productos = f"""
                SELECT uuid, nombre, precio, imagen 
                FROM productos 
                WHERE uuid IN ({','.join(['%s'] * len(uuids_productos))})
            """
            productos_detalles = query(sql_productos, tuple(uuids_productos,), fetchall=True)

            # Asociar cantidad de la orden con los productos obtenidos
            for producto in productos_detalles:
                producto["cantidad"] = next(p["cantidad"] for p in productos_json if p["uuid"] == producto["uuid"])

            orden["productos"] = productos_detalles

        return jsonify({"status": True, "orden": orden}), 200
    except Exception as e:
        return jsonify({"status": False, "message": str(e) ,"error": error_message}), 500


# Ruta para registrar una nueva orden desde el carrito
@venta_bp.route('/ordenar', methods=['POST'])
@token_required
def ordenar(user_id):
    try:
        data = request.json
        productos = data.get('productos', [])
        total_cliente = float(data.get('total', 0))
        tipo_entrega = data.get('tipoEntrega', 'Sucursal')
        direccion_id = 0

        if not productos:
            return jsonify({"message": "No hay productos en la orden"}), 400
        
        # Obtener IDs de los productos para validarlos
        producto_ids = [str(p["uuid"]) for p in productos]
        
        # Consultar precios y existencia de los productos
        sql = f"SELECT uuid, precio FROM productos WHERE uuid IN ({','.join(['%s'] * len(producto_ids))})"
        productos_db = query(sql, tuple(producto_ids), fetchall=True)

        if not productos_db or len(productos_db) != len(productos):
            return jsonify({"message": "Uno o más productos no existen"}), 400

       # Convertir resultado de la BD a diccionario {uuid: precio}
        if isinstance(productos_db[0], dict):  # Si query() devuelve diccionarios
            precios_db = {str(p["uuid"]): float(p["precio"]) for p in productos_db}
        else:  # Si query() devuelve listas de tuplas
            precios_db = {str(p[0]): float(p[1]) for p in productos_db}

         # Calcular total esperado
        total_calculado = sum(precios_db[str(p["uuid"])] * int(p["cantidad"]) for p in productos)

        # Comparar total calculado con el total enviado
        if round(total_calculado, 2) != round(total_cliente, 2):
            return jsonify({"message": "El total enviado no coincide con el precio real"}), 400


        # Generar UUID y número de orden
        orden_uuid = str(uuid.uuid4())
        fecha_orden = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        numero_orden = f"ORD-{int(datetime.datetime.now().timestamp())}"

        # Convertir productos a JSON
        productos_json = json.dumps(productos)

        sql = """
            INSERT INTO ordenes (uuid, fecha_orden, numero_orden, usuario_id, tipo_entrega, direccion_id, productos, total, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        try:
            # Insertar la orden en la base de datos
            rows_affected = query(sql, (orden_uuid, fecha_orden, numero_orden, user_id, tipo_entrega, direccion_id, productos_json, total_cliente, 0), commit=True)

            if rows_affected and rows_affected > 0 :
                # Definir la orden que se enviará al frontend
                orden = {
                    "uuid": orden_uuid,
                    "numero_orden": numero_orden,
                    "usuario_id": user_id,
                    "tipo_entrega": tipo_entrega,
                    "productos": productos,
                    "total": total_cliente,
                    "estado": "Pendiente",
                    "fecha_orden": fecha_orden
                }
                # Emitir evento a todos los clientes conectados
                nueva_orden(orden)
                return jsonify({"status": True,"message": "Puedes pasar a recoger a sucursal", "numero_orden": numero_orden}), 201
            else:
                return jsonify({"status": False, "message": error_message if error_message else "Error desconocido"}), 400
        
        except Error as ie:
            return jsonify({"status": False, "message": str(ie)}), 400
        
    except Exception as e:
        return jsonify({"status": False, "message": str(e)}), 500