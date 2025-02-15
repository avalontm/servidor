# db_config.py
import mysql.connector

# Configuración de la base de datos
DB_CONFIG = {
    'host': '192.168.100.7',
    'user': 'avalontm',  # Cambia esto según tu configuración
    'password': '5mtcgder',  # Cambia esto según tu configuración
    'database': 'moshi'  # Cambia esto según tu base de datos
}

def get_db_connection():
    """Devuelve una conexión a la base de datos"""
    return mysql.connector.connect(**DB_CONFIG)
