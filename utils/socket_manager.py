# socket_manager.py
from flask_socketio import SocketIO

socketio = SocketIO(cors_allowed_origins="*")  # Instancia de SocketIO
