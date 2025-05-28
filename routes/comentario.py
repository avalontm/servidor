from flask import Blueprint, jsonify
from utils.db_utils import query  # Asegúrate de tener una función `query` para manejar SQL
from utils.jwt_utils import token_required

comentario_bp = Blueprint('comentario', __name__)

# Ruta para obtener los últimos 10 comentarios
@comentario_bp.route('/recientes', methods=['GET'])
def obtener_comentarios_recientes():
    try:
        sql = """
            SELECT 
                c.comentario,
                c.calificacion,
                c.fecha_creacion,
                u.nombre,
                u.apellido,
                u.avatar
            FROM comentarios c
            JOIN usuarios u ON c.user_id = u.uuid
            ORDER BY c.fecha_creacion DESC
            LIMIT 10
        """
        resultados = query(sql, fetchall=True)

        comentarios = []
        for row in resultados:
            comentarios.append({
                "nombre": row["nombre"],
                "apellido": row["apellido"],
                "avatar": row["avatar"],
                "comentario": row["comentario"],
                "calificacion": int(row["calificacion"]),
                "fecha_creacion": row["fecha_creacion"].strftime("%Y-%m-%d %H:%M:%S")
            })

        return jsonify({
            "status": True,
            "comentarios": comentarios
        }), 200

    except Exception as e:
        return jsonify({"status": False, "message": str(e)}), 500
