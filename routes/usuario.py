import os
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from exeptions.DatabaseErrorException import DatabaseErrorException
from utils.auth_utils import check_user_credentials, create_user
from utils.jwt_utils import generate_jwt_token, token_required
from utils.db_utils import get_user_access, query
from utils.app_config import APP_PUBLIC, APP_SITE
from werkzeug.security import generate_password_hash, check_password_hash

user_bp = Blueprint('usuario', __name__)

# Ruta para registrar un nuevo usuario
@user_bp.route('/registrar', methods=['POST'])
def register():
    data = request.get_json()
    
    name = data.get('name')
    last_name = data.get('last_name')
    email = data.get('email')
    password = data.get('password')

    if not name or not last_name or not email or not password:
        return jsonify({'status': False, "message": "Faltan parámetros"}), 400

    # Intentar crear el usuario
    if create_user(email, password, name, last_name):
        return jsonify({'status': True, "message": "Usuario creado exitosamente"}), 201
    else:
        return jsonify({'status': False, "message": "El nombre de usuario ya está en uso o hubo un error al crear el usuario"}), 409


# Ruta para login y obtener el JWT
@user_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'status': False, "message": "Faltan parámetros"}), 400

    user = check_user_credentials(email, password)

    if user:
        # Mapeo de role según el valor en la base de datos
        role = 'admin' if user['role'] == 99 else 'user' if user['role'] == 0 else 'user'

        # Generar JWT
        token = generate_jwt_token(user['id'], role)
        
        return jsonify({'status': True, "name": user['nombre'], "role": role, "avatar" : user['avatar'], "token": token})

    return jsonify({'status': False, "message": "Usuario o contraseña incorrectos"}), 401

# Ruta protegida que requiere autenticación JWT
@user_bp.route('/info', methods=['GET'])
@token_required  # Asegura que el token sea validado antes de acceder a esta ruta
def protected(user_id):
    user = query("SELECT * FROM usuarios WHERE id = %s LIMIT 1", (user_id,))
    
    if user:
         # Eliminamos campos no deseados
        user = {key: value for key, value in user.items() if key not in ["id", "contrasena"]}
        return jsonify(user), 200
    else:
        return jsonify({'status': False, "message": "Usuario no encontrado"}), 404
    
# Ruta para actualizar perfil
@user_bp.route('/actualizar', methods=['POST'])
@token_required
def actualizar_usuario(user_id):
    try:
        nombre = request.form.get('nombre')
        telefono = request.form.get('telefono')
        genero = request.form.get('genero')
        foto = request.files.get('foto')
        nueva_password = request.form.get('password')
        confirmar_password = request.form.get('confirm_password')
        password_actual = request.form.get('current_password')

        # Validar que al menos un campo haya sido enviado
        if not any([nombre, telefono, genero, foto, nueva_password]):
            return jsonify({'status': False, "message": "No hay datos para actualizar"}), 400

        # Verificar la contraseña actual si el usuario intenta cambiar la contraseña
        if nueva_password or confirmar_password:
            if not password_actual:
                return jsonify({'status': False, "message": "Debes ingresar tu contraseña actual"}), 400
            
            # Obtener la contraseña actual desde la base de datos
            usuario = query("SELECT contrasena FROM usuarios WHERE id = %s LIMIT 1", (user_id,))
            if not usuario:
                return jsonify({'status': False, "message": "Usuario no encontrado"}), 404
            
            if not check_password_hash(usuario['contrasena'], password_actual):
                return jsonify({'status': False, "message": "La contraseña actual es incorrecta"}), 400
            
            if nueva_password != confirmar_password:
                return jsonify({'status': False, "message": "Las contraseñas nuevas no coinciden"}), 400
            
            hashed_password = generate_password_hash(nueva_password)

        # Directorio donde se guardarán las imágenes de perfil
        os.makedirs(os.path.join(APP_PUBLIC, "avatares"), exist_ok=True)

        # Procesar imagen si se subió
        foto_url = None
        if foto:
            filename = secure_filename(f"user_{user_id}.jpg")  # Guardar siempre con el mismo nombre para cada usuario
            foto_path = os.path.join(APP_PUBLIC, "avatares", filename)
            foto.save(foto_path)
            foto_url = f"/assets/avatares/{filename}"

        # Construir la consulta dinámica
        updates = []
        params = []
        if nombre:
            updates.append("nombre = %s")
            params.append(nombre)
        if telefono:
            updates.append("telefono = %s")
            params.append(telefono)
        if genero:
            updates.append("genero = %s")
            params.append(genero)
        if foto_url:
            updates.append("avatar = %s")
            params.append(foto_url)
        if nueva_password and confirmar_password:
            updates.append("contrasena = %s")
            params.append(hashed_password)

        if updates:
            params.append(user_id)
            cursor = query(f"UPDATE usuarios SET {', '.join(updates)} WHERE id = %s", tuple(params), commit=True, return_cursor=True)

            if not cursor:
                return jsonify({"status": False, "error": "Error desconocido"}), 500
            
        return jsonify({'status': True, "message": "Perfil actualizado correctamente"}), 200
    
    except DatabaseErrorException as e:
            return jsonify({"status": False, "message": str(e.message)}), 500
        
    except Exception as e:
        return jsonify({'status': False, "message": f"Error interno: {str(e)}"}), 500

@user_bp.route('/buscar', methods=['GET'])
@token_required
def buscar_usuario(user_id):
    access = get_user_access(user_id)
    
    if access != "admin":
        return jsonify({'status': False, "message": "No tiene permisos para realizar esta acción"}), 403
    
    # Obtener el término de búsqueda desde la URL
    search_term = request.args.get('search', '').strip()

    if not search_term:
        return jsonify({'status': False, 'message': 'Se requiere un término de búsqueda'}), 400

    # Construir la consulta con búsqueda en nombre completo (nombre + apellido) y filtrando solo usuarios activos
    query_str = """
        SELECT uuid, email, nombre, apellido, CONCAT(nombre, ' ', apellido) AS nombre_completo, telefono, puntos 
        FROM usuarios 
        WHERE (CONCAT(nombre, ' ', apellido) LIKE %s 
        OR email LIKE %s 
        OR telefono LIKE %s)
        AND eliminado = 0
    """

    # Parámetros para la consulta, buscando el término en el nombre completo o en los otros campos
    params = [f'%{search_term}%', f'%{search_term}%', f'%{search_term}%']

    try:
        # Ejecutar la consulta
        users = query(query_str, tuple(params), fetchall=True)

        if users:
            return jsonify({'status': True, 'usuarios': users}), 200
        else:
            return jsonify({'status': False, 'message': 'No se encontraron usuarios'}), 404
    
    except DatabaseErrorException as e:
        return jsonify({"status": False, "message": str(e.message)}), 500
