from datetime import datetime
import uuid
from flask import Blueprint, json, request, jsonify
from exeptions.DatabaseErrorException import DatabaseErrorException
from utils.jwt_utils import token_required
from utils.db_utils import get_user_access, query
from utils.app_config import APP_PUBLIC, APP_SITE
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
    except DatabaseErrorException as e:
        return jsonify({"status": False, "message": str(e.message)}), 500
    except Exception as e:
        return jsonify({"status": False, "message": str(e) }), 500


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
        fecha_orden = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        numero_orden = f"ORD-{int(datetime.now().timestamp())}"

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
                return jsonify({"status": False, "message": "Error desconocido"}), 400
        except DatabaseErrorException as e:
            return jsonify({"status": False, "message": str(e.message)}), 500
        except Error as ie:
            return jsonify({"status": False, "message": str(ie)}), 400
        
    except Exception as e:
        return jsonify({"status": False, "message": str(e)}), 500
    
@venta_bp.route('/crear', methods=['POST'])
@token_required
def crear_venta(user_id):
    access = get_user_access(user_id)

    if access != "admin":
        return jsonify({"error": "No tiene permisos para realizar esta acción"}), 403

    try:
        # Obtener datos del cuerpo de la solicitud
        data = request.json
        cliente_uuid = data.get('cliente') 
        productos = data.get('productos', [])
        total = float(data.get('total', 0))
        metodo_pago = data.get('metodo_pago', '')
        monto_pagado = float(data.get('monto_pagado', 0))
        puntos_usados = float(data.get('puntos_usados', 0))
        orden_uuid = data.get('orden_uuid')
       
        #Estado de la venta
        estado_venta = 0
        
        # Crear la lista de pagos con fecha, metodo_pago y monto
        metodos_pago = []
        
        # Inicializar la variable de ganancias
        ganancia_total = 0

        if not productos:
            return jsonify({"status": False, "message": "No hay productos en el carrito"}), 400
        
        if not cliente_uuid:
            cliente_uuid = "publico-general"
            
        # Buscar el cliente por UUID
        sql_cliente = "SELECT id, puntos FROM usuarios WHERE uuid = %s"
        cliente = query(sql_cliente, (cliente_uuid,), fetchall=False)

        if not cliente:
            return jsonify({"status": False, "message": "Cliente no encontrado"}), 404

        cliente_id = cliente['id']
        
        
        if puntos_usados > float(cliente['puntos']):
            return jsonify({"status": False, "message": "No tienes puntos suficientes."}), 400
        
        # Validar que el total con puntos no sea negativo
        total_con_puntos = total - puntos_usados
        if total_con_puntos < 0:
            return jsonify({"status": False, "message": "Los puntos usados no pueden exceder el total"}), 400
        
        # Generar UUID para la venta
        venta_uuid = str(uuid.uuid4())
        fecha_venta = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        folio_venta = f"VEN-{int(datetime.now().timestamp())}"

     
        # Agregar el método de pago correspondiente
        if monto_pagado > 0 and metodo_pago == "efectivo":
            metodos_pago.append({
                "fecha": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "metodo_pago": "efectivo",
                "monto": monto_pagado if metodo_pago == "efectivo" else 0
            })
            
        if monto_pagado > 0 and metodo_pago == "tarjeta":
            metodos_pago.append({
                "fecha": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "metodo_pago": "tarjeta",
                "monto": monto_pagado if metodo_pago == "tarjeta" else 0
            })
            
        if monto_pagado > 0 and metodo_pago == "transferencia":
            metodos_pago.append({
                "fecha": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "metodo_pago": "transferencia",
                "monto": monto_pagado if metodo_pago == "transferencia" else 0
            })
    
        # Agregar el pago de puntos si se usaron
        if puntos_usados > 0:
            metodos_pago.append({
                "fecha": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "metodo_pago": "puntos",
                "monto": puntos_usados
            })

        # Convertir la lista a JSON
        metodos_pago_json = json.dumps(metodos_pago)
       
        # Obtener los UUIDs de los productos en la venta
        uuids_productos = [producto["uuid"] for producto in productos]

        # Verificar que haya UUIDs válidos antes de hacer la consulta
        if not uuids_productos:
            return jsonify({"message": "No se encontraron UUIDs válidos en los productos", "status": False}), 400

        # Construir la consulta con los placeholders (%s)
        query_sql = """
            SELECT uuid, nombre, precio_unitario, precio, imagen, inversionista_id 
            FROM productos
            WHERE uuid IN (%s)
        """ % ",".join(["%s"] * len(uuids_productos))  # Construye el número correcto de placeholders
 
        # Ejecutar la consulta con los valores de los UUIDs
        productos_db = query(query_sql, tuple(uuids_productos), fetchall=True)
        
        # Si no se encontraron productos en la base de datos
        if not productos_db:
            return jsonify({"message": "No se encontraron productos en la base de datos", "status": False}), 400

        # Crear un diccionario con los datos reales de los productos
        productos_dict = {producto["uuid"]: producto for producto in productos_db}

  
        # Filtrar y combinar los datos con la cantidad y precio total
        productos_filtrados = []
        for producto in productos:
            _uuid = producto["uuid"]
            
            if _uuid in productos_dict:
                producto_real = productos_dict[_uuid]
                productos_filtrados.append({
                    "uuid": _uuid,
                    "nombre": producto_real["nombre"],
                    "cantidad": producto["cantidad"],  # Mantener la cantidad ingresada en la venta
                    "precio_unitario": producto_real["precio_unitario"],  # Precio real de la base de datos
                    "precio": producto["cantidad"] * producto_real["precio"],  # Recalcular precio total
                    "inversionista_id": producto_real["inversionista_id"],
                })

        # Si después del filtrado no hay productos válidos
        if not productos_filtrados:
            return jsonify({"message": "No se pudieron validar los productos", "status": False}), 400

        # Convertir la lista filtrada a JSON
        productos_json = json.dumps(productos_filtrados)

        # Iterar sobre los productos para calcular las ganancias
        for producto in productos_filtrados:
            precio_unitario = producto['precio_unitario']
            precio_venta = producto['precio']
            cantidad = producto['cantidad']
            
            # Calcular la ganancia por este producto
            ganancia_producto = (precio_venta - precio_unitario) * cantidad
            ganancia_total += ganancia_producto
            
            cantidad_disponible = producto['cantidad']

            if cantidad > cantidad_disponible:
                return jsonify({"status": False, "message": f"No hay suficiente stock para {producto['nombre']}"}), 400

            # Descontar las unidades, asegurándose de que no se vuelva negativo
            nueva_cantidad = max(0, cantidad_disponible - cantidad)

            # Actualizar la cantidad en productos
            sql_actualizar_inventario = "UPDATE productos SET cantidad = %s WHERE uuid = %s"
            query(sql_actualizar_inventario, (nueva_cantidad, producto['uuid']), commit=True)

        # Iterar sobre los productos para calcular las ganancias
        for producto in productos_filtrados:
            precio_unitario = producto['precio_unitario']  # Suponemos que el producto tiene un campo 'precio_unitario'
            precio_venta = producto['precio']  # El precio de venta
            cantidad = producto['cantidad']  # Cantidad del producto en la venta
            
            # Calcular la ganancia por este producto
            ganancia_producto = (precio_venta - precio_unitario) * cantidad
            
            # Sumar la ganancia del producto al total
            ganancia_total += ganancia_producto
    
        # Verificar si el monto cubre la totalidad
        if metodo_pago == "efectivo" and monto_pagado + puntos_usados >= total_con_puntos:
            estado_venta = 1  # El monto cubre la totalidad
        else:
            estado_venta = 0  # El monto no cubre la totalidad

        # Registrar la venta en la base de datos
        sql = """
            INSERT INTO ventas (uuid, fecha_creacion, folio, cliente_id, empleado_id, productos, metodos_pago, efectivo, tarjeta, transferencia, puntos, ganancia, subtotal, impuesto, total, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        try:
            # Insertar la venta en la base de datos
            cursor = query(sql, (
                venta_uuid, 
                fecha_venta, 
                folio_venta, 
                cliente_id, 
                user_id, 
                productos_json, 
                metodos_pago_json,  # Aquí insertamos el JSON de métodos de pago
                monto_pagado if metodo_pago == "efectivo" else 0,
                monto_pagado if metodo_pago == "tarjeta" else 0, 
                monto_pagado if metodo_pago == "transferencia" else 0,
                puntos_usados, 
                ganancia_total, #Ganancias 
                total_con_puntos - (total_con_puntos * 0.08), #subTotal
                total_con_puntos * 0.08, #impuesto
                total_con_puntos, #Total
                estado_venta  # Estado
            ), commit=True, return_cursor=True)

            if cursor:  # rowcount indica cuántas filas se han afectado
                # Definir la venta que se enviará al frontend
                venta = {
                    "uuid": venta_uuid,
                    "folio": folio_venta,
                    "cliente_id": cliente_id,
                    "empleado_id": user_id,
                    "productos": productos_filtrados,  # Aquí ya usamos la lista filtrada de productos
                    "total": total_con_puntos,
                    "estado": estado_venta,  
                    "fecha_venta": fecha_venta
                }

                # Restar los puntos al cliente si se usaron puntos
                if puntos_usados > 0:
                    query("""
                        UPDATE usuarios 
                        SET puntos = GREATEST(0, puntos - %s)
                        WHERE id = %s
                    """, (puntos_usados, cliente_id), commit=True)

                # Actualizar la orden y marcarla como "terminada"
                if orden:
                    query("""
                        UPDATE ordenes 
                        SET estado = 4, venta_uuid = %s
                        WHERE uuid = %s
                    """, (venta_uuid, orden_uuid), commit=True)

                # Emitir la impresion del ticket de venta
                #imprimir_venta(venta)
                
                return jsonify({
                    "status": True,
                    "message": "Venta registrada exitosamente",
                    "folio": folio_venta,
                    "nota": venta,
                }), 201
            else:
                return jsonify({"status": False, "message": "Error al registrar la venta" }), 500
        
        except DatabaseErrorException as e:
            return jsonify({"status": False, "message": str(e)}), 500
    
        except Error as ie:
            return jsonify({"status": False, "message": str(ie)}), 500
        
    except Exception as e:
        return jsonify({"status": False, "message": str(e)}), 500
