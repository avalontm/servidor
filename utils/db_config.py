# db_config.py
import mysql.connector

# Configuración de la base de datos
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',  # Cambia esto según tu configuración
    'password': '',  # Cambia esto según tu configuración
    'database': 'test_db'  # Cambia esto según tu base de datos
}

def get_db_connection():
    """Devuelve una conexión a la base de datos"""
    return mysql.connector.connect(**DB_CONFIG)
