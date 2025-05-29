import os
import tempfile
import time
import imghdr
import uuid as uuid_module
import subprocess
import base64
from werkzeug.utils import secure_filename
from flask import jsonify
from utils.app_config import APP_PUBLIC
from werkzeug.datastructures import FileStorage

# Lista de extensiones de imágenes permitidas
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}

# Función para verificar si el archivo tiene una extensión permitida
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def procesar_imagen(foto, user_id):
    """
    Procesa una imagen: valida su tipo, la convierte a JPG y la guarda con un nombre estándar.
    
    :param foto: Objeto FileStorage de Flask con la imagen a procesar
    :param user_id: ID del usuario, usado para nombrar el archivo
    :return: URL de la imagen procesada si tiene éxito, None en caso de error
    """
    try:
        # Verificar si el archivo tiene una extensión permitida
        if not allowed_file(foto.filename):
            return None

        # Directorio donde se guardarán las imágenes de perfil
        os.makedirs(os.path.join(APP_PUBLIC, "avatares"), exist_ok=True)

        # Guardar temporalmente la imagen original
        file_type = foto.filename.rsplit('.', 1)[1].lower() if '.' in foto.filename else 'jpg'
        temp_filename = secure_filename(f"user_{user_id}_temp.{file_type}")
        temp_path = os.path.join(APP_PUBLIC, "avatares", temp_filename)
        foto.save(temp_path)

        # Verificar el tipo de archivo usando imghdr
        actual_file_type = imghdr.what(temp_path)
        if actual_file_type not in ALLOWED_EXTENSIONS:
            os.remove(temp_path)
            return None

        # Definir el nombre final para la imagen en JPG
        jpg_filename = f"user_{user_id}.jpg"
        jpg_path = os.path.join(APP_PUBLIC, "avatares", jpg_filename)

        # Usar ImageMagick para convertir la imagen a JPG
        subprocess.run(['convert', temp_path, jpg_path], check=True)

        # Eliminar el archivo temporal
        os.remove(temp_path)

        # Obtener el timestamp actual y agregarlo a la URL
        timestamp = int(time.time())
        foto_url = f"/assets/avatares/{jpg_filename}?{timestamp}"

        # Retornar la ruta de la imagen
        return foto_url

    except Exception as e:
        print(f"Error al procesar imagen: {str(e)}")
        # Asegurarse de eliminar el archivo temporal en caso de error
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        return None

def procesar_imagen(foto_input, user_id):
    """
    Procesa una imagen: valida su tipo, la convierte a JPG y la guarda con un nombre estándar.
    Puede manejar tanto objetos FileStorage como rutas de archivo.
    
    :param foto_input: Objeto FileStorage de Flask o ruta de archivo de la imagen
    :param user_id: ID del usuario, usado para nombrar el archivo
    :return: URL de la imagen procesada si tiene éxito, None en caso de error
    """
    temp_path = None
    try:
        # Directorio donde se guardarán las imágenes de perfil
        os.makedirs(os.path.join(APP_PUBLIC, "avatares"), exist_ok=True)
        
        # Detectar si es un objeto FileStorage o una ruta de archivo
        from werkzeug.datastructures import FileStorage
        
        if isinstance(foto_input, FileStorage):
            # Es un objeto FileStorage (subida directa)
            if not allowed_file(foto_input.filename):
                return None
                
            # Guardar temporalmente la imagen original
            file_type = foto_input.filename.rsplit('.', 1)[1].lower() if '.' in foto_input.filename else 'jpg'
            temp_filename = secure_filename(f"user_{user_id}_temp.{file_type}")
            temp_path = os.path.join(APP_PUBLIC, "avatares", temp_filename)
            foto_input.save(temp_path)
        else:
            # Es una ruta de archivo (convertida de base64)
            temp_path = foto_input
            
        # Verificar el tipo de archivo usando imghdr
        actual_file_type = imghdr.what(temp_path)
        if actual_file_type not in ALLOWED_EXTENSIONS:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return None

        # Definir el nombre final para la imagen en JPG
        jpg_filename = f"user_{user_id}.jpg"
        jpg_path = os.path.join(APP_PUBLIC, "avatares", jpg_filename)

        # Usar ImageMagick para convertir la imagen a JPG
        subprocess.run(['convert', temp_path, jpg_path], check=True)

        # Eliminar el archivo temporal
        if os.path.exists(temp_path):
            os.remove(temp_path)

        # Obtener el timestamp actual y agregarlo a la URL
        timestamp = int(time.time())
        foto_url = f"/assets/avatares/{jpg_filename}?{timestamp}"

        # Retornar la ruta de la imagen
        return foto_url

    except Exception as e:
        print(f"Error al procesar imagen: {str(e)}")
        # Asegurarse de eliminar el archivo temporal en caso de error
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        return None
    
# Función para convertir base64 a bytes
def convertir_base64_a_bytes(base64_string):
    """
    Convierte una cadena base64 de una imagen en datos binarios.

    :param base64_string: Cadena base64 de la imagen
    :return: Datos binarios de la imagen
    """
    # Verificar si la cadena base64 contiene los datos de la imagen
    if base64_string and isinstance(base64_string, str) and base64_string.startswith('data:image'):
        # Extraer solo los datos base64 (sin el prefijo 'data:image/...;base64,')
        base64_string = base64_string.split(',')[1]

    try:
        # Decodificar la cadena base64 a bytes
        image_data = base64.b64decode(base64_string)
        return image_data
    except Exception as e:
        raise ValueError(f"Error al decodificar la imagen: {str(e)}")

# Función para convertir base64 en un archivo temporal compatible con `procesar_imagen`
def convertir_base64_a_archivo(base64_string):
    """
    Convierte una cadena base64 en un archivo temporal y retorna la ruta del archivo.
    
    :param base64_string: Cadena base64 de la imagen
    :return: Ruta del archivo temporal con los datos de la imagen
    """
    if not base64_string:
        return None
        
    try:
        image_data = convertir_base64_a_bytes(base64_string)

        # Crear un archivo temporal en el sistema de archivos
        temp_file = tempfile.NamedTemporaryFile(delete=False, mode='wb', suffix='.jpg')
        temp_file.write(image_data)
        temp_file_path = temp_file.name
        temp_file.close()

        return temp_file_path  # Devolver la ruta completa del archivo temporal
    except Exception as e:
        print(f"Error al convertir base64 a archivo: {str(e)}")
        return None
    
def procesar_banner(foto, name):
    """
    Procesa una imagen: valida su tipo, la convierte a JPG y la guarda con un nombre estándar.
    
    :param foto: Objeto FileStorage de Flask con la imagen a procesar
    :param name: nombre del archivo, usado para nombrar el archivo final
    :return: URL de la imagen procesada si tiene éxito, None en caso de error
    """
    try:
        # Verificar si el archivo tiene una extensión permitida
        if not allowed_file(foto.filename):
            return None

        # Directorio donde se guardarán las imágenes de perfil
        os.makedirs(os.path.join(APP_PUBLIC, "banners"), exist_ok=True)

        # Guardar temporalmente la imagen original
        file_type = foto.filename.rsplit('.', 1)[1].lower() if '.' in foto.filename else 'jpg'
        temp_filename = secure_filename(f"{name}.{file_type}")
        temp_path = os.path.join(APP_PUBLIC, "banners", temp_filename)
        foto.save(temp_path)

        # Verificar el tipo de archivo usando imghdr
        actual_file_type = imghdr.what(temp_path)
        if actual_file_type not in ALLOWED_EXTENSIONS:
            os.remove(temp_path)
            return None

        # Definir el nombre final para la imagen en JPG
        jpg_filename = f"banner_{name}.jpg"
        jpg_path = os.path.join(APP_PUBLIC, "banners", jpg_filename)

        # Usar ImageMagick para convertir la imagen a JPG
        subprocess.run(['convert', temp_path, jpg_path], check=True)

        # Eliminar el archivo temporal
        os.remove(temp_path)

        # Obtener el timestamp actual y agregarlo a la URL
        timestamp = int(time.time())
        foto_url = f"/assets/banners/{jpg_filename}?{timestamp}"

        # Retornar la ruta de la imagen
        return foto_url

    except Exception as e:
        print(f"Error al procesar imagen: {str(e)}")
        # Asegurarse de eliminar el archivo temporal en caso de error
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        return None