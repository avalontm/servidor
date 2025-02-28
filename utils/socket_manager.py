# socket_manager.py
from flask_socketio import SocketIO
from flask import request

socketio = SocketIO(cors_allowed_origins="*")  # Instancia de SocketIO

@socketio.on("connect")
def handle_connect():
    print("🟢 Cliente conectado!")

@socketio.on("disconnect")
def handle_disconnect():
    print(f"❌ Cliente desconectado: {request.sid}")
    
def nueva_orden(orden):
    print(f"📦 Enviando nueva orden: {orden}")
    socketio.emit("nueva_orden", orden)  # Emitiendo evento