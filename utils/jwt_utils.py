# jwt_utils.py
import jwt
import datetime
from flask import jsonify, request
from functools import wraps

SECRET_KEY = 'b#$Q@^rgtd%$^e34%23$&^N524n8&2#$xq3%&C%^E&c'  # clave segura

def generate_jwt_token(user_id, role):
    """Genera un token JWT"""
    expiration_time = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    token = jwt.encode(
        {'user_id': user_id, 'role': role, 'exp': expiration_time},
        SECRET_KEY,
        algorithm='HS256'
    )
    return token  # PyJWT 2.x devuelve un string, no bytes



def token_required(f):
    """Decora una ruta para requerir un token JWT válido"""
    @wraps(f)
    def decorator(*args, **kwargs):
        token = None
        # Intentamos obtener el token desde el encabezado Authorization
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]  # El token está después de "Bearer "
        
        if not token:
            return jsonify({"message": "Token no proporcionado"}), 403
        
        try:
            decoded = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            kwargs['user_id'] = decoded['user_id']  # Extraemos el user_id del token decodificado
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "El token ha expirado"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Token inválido"}), 401
        
        return f(*args, **kwargs)
    
    return decorator
