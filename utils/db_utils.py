# db_utils.py
import mysql.connector
from mysql.connector import Error
from utils.db_config import DB_CONFIG  # Importa la configuración desde db_config.py

# Función para verificar la conexión a la base de datos
def verify_db_connection():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchall()  # Asegura que no queden resultados abiertos
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error al conectar con la base de datos: {e}")
        return False
        
def get_db_connection():
    """Devuelve una conexión a la base de datos utilizando la configuración de db_config.py"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
        else:
            print("No se pudo conectar a la base de datos.")
            return None
    except Error as e:
        print(f"Error al conectar a la base de datos: {e}")
        return None

def get_user_name(user_id):
    """Obtiene el nombre del usuario desde la base de datos por su ID"""
    connection = get_db_connection()
    
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            # Consulta para obtener el nombre del usuario
            query = "SELECT nombre FROM users WHERE id = %s"
            cursor.execute(query, (user_id,))
            result = cursor.fetchone()  # Obtener el primer resultado
            
            if result:
                return result['nombre']  # Devuelve el nombre si existe el usuario
            else:
                return None  # Si no existe, devuelve None
        except Error as e:
            print(f"Error al ejecutar la consulta: {e}")
            return None
        finally:
            cursor.close()  # Cierra el cursor
            connection.close()  # Cierra la conexión
    else:
        return None


def query(sql, params=None, fetchall=False, commit=False, return_cursor=False):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(sql, params)

            if commit:
                connection.commit()
                if return_cursor:
                    return cursor  # Devuelve el cursor para verificar rowcount
                return cursor.rowcount  # Devuelve la cantidad de filas afectadas

            if fetchall:
                result = cursor.fetchall()
            else:
                result = cursor.fetchone()

            return result
        except Error as e:
            print(f"Error al ejecutar la consulta: {e}")
            return None
        finally:
            if not return_cursor and cursor:
                cursor.close()
            if connection:
                connection.close()
    return None
