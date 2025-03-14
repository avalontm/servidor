import base64
import datetime
import uuid
from flask import Blueprint, json, request, jsonify
from exeptions.DatabaseErrorException import DatabaseErrorException
from utils.jwt_utils import token_required
from utils.db_utils import get_user_access, query
from utils.app_config import APP_PUBLIC, APP_SITE
from mysql.connector import Error
import os
from werkzeug.utils import secure_filename
# Importar funciones para manejo de imágenes
from utils.img_utils import convertir_base64_a_archivo, procesar_imagen

site_bp = Blueprint('site', __name__)

@site_bp.route('/panel/configuracion', methods=['GET'])
@token_required
def obtener_configuracion(user_id):
    access = get_user_access(user_id)
    
    if access != "admin":
        return jsonify({"error": "No tiene permisos para realizar esta acción"}), 403
    
    try:
        # Consulta para obtener la configuración actual del sitio
        sql_config = """
            SELECT 
                nombre,
                descripcion,
                logo, 
                email, 
                telefono, 
                codigo_postal, 
                ciudad, 
                direccion,
                puntos,
                total_puntos,
                impuesto, 
                mantenimiento
            FROM sitio 
            WHERE id = 1
        """
        
        config = query(sql_config)
                
        return jsonify({"status": True, "message": "datos del sitio", "config" : config}), 200
    
    except DatabaseErrorException as e:
        return jsonify({"status": False, "message": str(e.message)}), 500
    except Exception as e:
        return jsonify({"status": False, "message": str(e)}), 500

@site_bp.route('/panel/configuracion/actualizar', methods=['POST'])
@token_required
def actualizar_configuracion(user_id):
    access = get_user_access(user_id)
    
    if access != "admin":
        return jsonify({"error": "No tiene permisos para realizar esta acción"}), 403
    
    try:
        # Determinar el tipo de solicitud (archivo o JSON)
        has_file = request.files and 'logo' in request.files and request.files['logo'].filename
        
        # Obtener los datos según el tipo de solicitud
        if has_file:
            # Obtener datos de form-data con archivo
            data = {
                'nombre': request.form.get('nombre', ''),
                'descripcion': request.form.get('descripcion', ''),
                'email': request.form.get('email', ''),
                'telefono': request.form.get('telefono', ''),
                'codigo_postal': request.form.get('codigo_postal', ''),
                'ciudad': request.form.get('ciudad', ''),
                'direccion': request.form.get('direccion', ''),
                'puntos': int(request.form.get('puntos', 1)),
                'total_puntos': int(request.form.get('total_puntos', 0)),
                'impuesto': float(request.form.get('impuesto', 16)),
                'mantenimiento': 1 if request.form.get('mantenimiento', '0') in ['true', '1', 'on'] else 0
            }
            
            # Procesar el archivo del logo
            file = request.files['logo']
            if file and file.filename:
                # Generar un nombre único para el archivo
                filename = f"site_logo.png"
                upload_folder = os.path.join(APP_PUBLIC, "logos")
                
                # Asegurarse de que el directorio existe
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)
                
                # Guardar el archivo
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                
                # URL relativa para guardar en la base de datos
                logo_url = f"/assets/logos/{filename}?{uuid.uuid4()}"
                data['logo'] = logo_url
        else:
            # Obtener datos de JSON
            data = request.json
            
            # Convertir valores si es necesario
            if isinstance(data.get('mantenimiento'), str):
                data['mantenimiento'] = 1 if data['mantenimiento'].lower() in ['true', '1', 'on'] else 0
            elif isinstance(data.get('mantenimiento'), bool):
                data['mantenimiento'] = 1 if data['mantenimiento'] else 0
            
            # Procesar la imagen en base64 si existe
            imagen_url = None
            if 'logo' in data and isinstance(data['logo'], str) and data['logo'].startswith('data:image'):
                try:

                    # Extraer los datos de base64
                    if "," in data['logo']:
                        img_data = base64.b64decode(data['logo'].split(',')[1])
                        
                        # Generar nombre único para el archivo
                        filename = f"site_logo.png"
                        upload_folder = os.path.join(APP_PUBLIC, "logos")
                        
                        # Asegurarse de que el directorio existe
                        if not os.path.exists(upload_folder):
                            os.makedirs(upload_folder)
                        
                        # Guardar la imagen
                        imagen_path = os.path.join(upload_folder, filename)
                        with open(imagen_path, 'wb') as f:
                            f.write(img_data)
                        
                        # URL relativa para guardar en la base de datos
                        imagen_url = f"/assets/logos/{filename}?{uuid.uuid4()}"
                        data['logo'] = imagen_url
                except Exception as e:
                    print("Error al procesar la imagen:", e)
                    return jsonify({"status": False, "message": "Error al procesar la imagen del logo"}), 500
            
            # Si no se envió una nueva imagen o es una URL, mantener la existente si es necesario
            elif 'logo' in data:
                # Si es None o vacío, no modificar el logo
                if data['logo'] is None or data['logo'] == '':
                    # Obtener el logo actual de la base de datos
                    sql_logo = "SELECT logo FROM sitio WHERE id = 1"
                    logo_actual = query(sql_logo)
                    
                    if logo_actual and logo_actual.get('logo'):
                        # Mantener el logo actual
                        data['logo'] = logo_actual['logo']
                    else:
                        # Si no hay logo actual, dejar vacío
                        data['logo'] = ''
        
        # Actualizar la configuración en la base de datos
        sql_update = """
            UPDATE sitio SET
                nombre = %s,
                descripcion = %s,
                email = %s,
                telefono = %s,
                codigo_postal = %s,
                ciudad = %s,
                direccion = %s,
                puntos = %s,
                total_puntos = %s,
                impuesto = %s,
                mantenimiento = %s
        """
        
        params = [
            data.get('nombre', ''),
            data.get('descripcion', ''),
            data.get('email', ''),
            data.get('telefono', ''),
            data.get('codigo_postal', ''),
            data.get('ciudad', ''),
            data.get('direccion', ''),
            data.get('puntos', 1),
            data.get('total_puntos', 0),
            data.get('impuesto', 16),
            int(data.get('mantenimiento', 0))
        ]
        
        # Añadir logo a la consulta solo si se proporcionó uno nuevo
        if 'logo' in data and data['logo'] is not None:
            sql_update += ", logo = %s"
            params.append(data['logo'])
        
        sql_update += " WHERE id = 1"
        
        # Ejecutar la consulta
        cursor = query(sql_update, tuple(params), commit=True, return_cursor=True)
        
        if cursor:
            return jsonify({"status": True, "message": "Configuración actualizada correctamente"}), 200
        else:
            return jsonify({"status": False, "message": "No se encontró la configuración para actualizar"}), 404
    
    except DatabaseErrorException as e:
        return jsonify({"status": False, "message": str(e.message)}), 500
    except Exception as e:
        print("Error:", e)  # Añadir para debugging
        return jsonify({"status": False, "message": str(e)}), 500