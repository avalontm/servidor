# auth_utils.py
from werkzeug.security import generate_password_hash, check_password_hash
from utils.db_config import get_db_connection
import mysql.connector
from mysql.connector import Error

def create_user(email, password, name, last_name):
    """Crea un usuario con la contraseña hasheada y maneja errores de duplicados. Devuelve True si el usuario fue creado, False si hubo un error."""
    hashed_password = generate_password_hash(password)
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Intentar insertar el nuevo usuario
        cursor.execute("INSERT INTO usuarios (email, contrasena, nombre, apellido) VALUES (%s, %s, %s, %s)", (email, hashed_password, name, last_name))
        conn.commit()
        return True  # Usuario creado exitosamente
    except mysql.connector.errors.IntegrityError as e:
        # Verificar si el error es de duplicado de username
        if '1062' in str(e):  # Código de error para entrada duplicada
            return False  # El nombre de usuario ya está en uso
        else:
            return False  # Otro tipo de error de integridad
    except Error as e:
        print(e)
        return False  # Cualquier otro error inesperado
    finally:
        # Cerrar la conexión y el cursor
        cursor.close()
        conn.close()

def check_user_credentials(email, password):
    """Verifica las credenciales del usuario"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user and check_password_hash(user['contrasena'], password):
        return user
    return None
