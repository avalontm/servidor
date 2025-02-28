import datetime
import uuid
from flask import Blueprint, json, request, jsonify
from utils.jwt_utils import token_required
from utils.db_utils import get_user_access, query
from utils.app_config import APP_PUBLIC, APP_SITE
from utils.db_utils import error_message
from mysql.connector import Error
from utils.socket_manager import nueva_orden  # Importa socketio

orden_bp = Blueprint('orden', __name__)

#Ruta para obtener todas las ordenes
@orden_bp.route('/panel/lista', methods=['GET'])
@token_required
def ordenes(user_id):
    
    access = get_user_access(user_id)
    
    if access != "admin":
        return jsonify({"error": "No tiene permisos para realizar esta acción"}), 403
    
    estado = request.args.get("estado", type=int) 
    
    try:
        sql = """
            SELECT o.uuid, o.fecha_orden, o.numero_orden, o.usuario_id, o.tipo_entrega, o.direccion_id, o.productos, o.total, o.estado
            FROM ordenes o
            WHERE o.estado = %s
            ORDER BY o.fecha_orden DESC
        """
        ordenes = query(sql, (estado,), fetchall=True)
        
        return jsonify({"status": True, "ordenes": ordenes}), 200
    except Exception as e:
        return jsonify({"status": False, "message": str(e)}), 500
    
    
@orden_bp.route('/panel/<string:uuid>', methods=['GET'])
@token_required
def get_orden(user_id, uuid):
    access = get_user_access(user_id)

    if access != "admin":
        return jsonify({"error": "No tiene permisos para realizar esta acción"}), 403

    try:
        # Obtener la orden junto con el nombre del usuario
        sql_orden = """
            SELECT o.uuid, o.fecha_orden, o.usuario_id, u.nombre AS nombre_usuario, 
                   o.numero_orden, o.tipo_entrega, o.direccion_id, 
                   o.productos, o.total, o.estado
            FROM ordenes o
            JOIN usuarios u ON o.usuario_id = u.id
            WHERE o.uuid = %s
        """
        orden = query(sql_orden, (uuid,))

        if not orden:
            return jsonify({"status": False, "message": "Orden no encontrada"}), 404

        # Asegurar que productos es una lista válida
        productos_json = json.loads(orden["productos"]) if isinstance(orden["productos"], str) else orden["productos"]
        if not isinstance(productos_json, list):
            productos_json = []

        # Extraer los UUIDs de los productos
        uuids_productos = [p["uuid"] for p in productos_json if "uuid" in p]

        productos_detalles = []
        if uuids_productos:
            # Consultar detalles de los productos en la base de datos
            sql_productos = f"""
                SELECT uuid, nombre, precio, imagen 
                FROM productos 
                WHERE uuid IN ({','.join(['%s'] * len(uuids_productos))})
            """
            productos_detalles = query(sql_productos, tuple(uuids_productos), fetchall=True)

            # Asociar cantidad de la orden con los productos obtenidos
            for p in productos_json:
                for pd in productos_detalles:
                    if p["uuid"] == pd["uuid"]:
                        p.update({
                            "nombre": pd["nombre"],
                            "precio": pd["precio"],
                            "imagen": pd["imagen"]
                        })

        orden["productos"] = productos_json

        return jsonify({"status": True, "orden": orden}), 200
    except Exception as e:
        return jsonify({"status": False, "message": str(e)}), 500


# Ruta para modificar el estado de una orden
@orden_bp.route('/panel/<string:uuid>', methods=['PUT'])
@token_required
def modificar_estado(user_id, uuid):
    access = get_user_access(user_id)

    if access != "admin":
        return jsonify({"error": "No tiene permisos para realizar esta acción"}), 403

    data = request.get_json()
    
    if not data or "estado" not in data:
        return jsonify({"error": "No se han proporcionado datos o falta el estado"}), 400

    try:
        estado = data["estado"]

        # Validar que el estado sea un número entre 0 y 5
        if not isinstance(estado, int) or estado not in range(6):
            return jsonify({"error": "Estado inválido"}), 400

        sql = """
            UPDATE ordenes
            SET estado = %s
            WHERE uuid = %s
        """
        cursor = query(sql, (estado, uuid), commit=True, return_cursor=True)

        if not cursor:
            return jsonify({"status": False, "message": error_message}), 500
        
        return jsonify({"status": True, "message": "Estado de la orden actualizado"}), 200

    except Exception as e:
        return jsonify({"status": False, "message": str(e)}), 500
