# apis/users.py
from flask import Blueprint, request, jsonify
from utils.auth_utils import create_user, check_user_credentials
from utils.jwt_utils import generate_jwt_token, token_required
from utils.db_utils import get_user_name
import mysql.connector

users_bp = Blueprint('user', __name__)

# Ruta para registrar un nuevo usuario
@users_bp.route('/register', methods=['POST'])
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
@users_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    username = data.get('email')
    password = data.get('password')

    if not username or not password:
        return jsonify({'status': False, "message": "Faltan parámetros"}), 400

    user = check_user_credentials(username, password)

    if user:
        # Mapeo de role según el valor en la base de datos
        role = 'admin' if user['role'] == 99 else 'user' if user['role'] == 0 else 'user'

        # Generar JWT
        token = generate_jwt_token(user['id'], role)
        
        return jsonify({'status': True, "name": user['name'], "role": role, "avatar" : user['avatar'], "token": token})

    return jsonify({'status': False, "message": "Usuario o contraseña incorrectos"}), 401

# Ruta protegida que requiere autenticación JWT
@users_bp.route('/protected', methods=['GET'])
@token_required  # Asegura que el token sea validado antes de acceder a esta ruta
def protected(user_id):
    user_name = get_user_name(user_id)
    
    if user_name:
        return jsonify({'status': True, "message": f"Bienvenido, {user_name}!"})
    else:
        return jsonify({'status': False, "message": "Usuario no encontrado"}), 404
