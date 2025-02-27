# db_utils.py
import mysql.connector
from mysql.connector import Error, IntegrityError, DataError, DatabaseError, OperationalError, ProgrammingError, InterfaceError, InternalError, NotSupportedError
from utils.db_config import DB_CONFIG  # Importa la configuración desde db_config.py

error_message = None  # Variable para almacenar el error

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

def get_user_access(user_id):
    """Obtiene el nivel de acceso del usuario desde la base de datos por su ID y devuelve 'admin' o 'user'."""
    connection = get_db_connection()
    
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            # Consulta para obtener el rol del usuario
            query = "SELECT role FROM usuarios WHERE id = %s AND eliminado=0"
            cursor.execute(query, (user_id,))
            result = cursor.fetchone()  # Obtener el primer resultado
            
            if result and 'role' in result:
                return "admin" if int(result['role']) == 99 else "user"
            else:
                return "user"  # Si el usuario no existe, es tratado como usuario normal

        except Error as e:
            print(f"Error al ejecutar la consulta: {e}")
            return "user"  # En caso de error, se considera usuario normal
        
        finally:
            cursor.close()
            connection.close()

    return "user"  # Si no hay conexión, se considera usuario normal

    
def query(sql, params=None, fetchall=False, commit=False, return_cursor=False):
    global error_message  # Declaramos que vamos a modificar la variable global
    error_message = None  # Reiniciamos el mensaje de error
    
    connection = get_db_connection()
    if not connection:
        error_message = "No se pudo establecer la conexión con la base de datos."
        return None, error_message  # Devuelve None y el error
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sql, params)

        if commit:
            connection.commit()
            return cursor.rowcount if cursor.rowcount is not None else 0  

        result = cursor.fetchall() if fetchall else cursor.fetchone()
        return result  
        # ERRORES CLASIFICADOS
    except (IntegrityError, DataError, DatabaseError, OperationalError, ProgrammingError, InterfaceError, InternalError, NotSupportedError) as e:
        error_message = f"{type(e).__name__}: {str(e)}"
        return None  # Devuelve el error correctamente
    except Exception as e:
        error_message = f"UnknownError: {e}"  # Cualquier otro error inesperado
        return None  
    finally:
        if not return_cursor and cursor:
            cursor.close()
        if connection:
            connection.close()