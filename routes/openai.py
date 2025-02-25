from flask import Blueprint, request, jsonify
from openai import OpenAI

# Crear un Blueprint para la API de OpenAI
openai_bp = Blueprint("openai", __name__)

# Configurar el cliente de OpenAI con OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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",
)

# Ruta para generar descripciones de productos
@openai_bp.route('/generar-descripcion', methods=['POST'])
def generar_descripcion():
    data = request.get_json()
    
    if not data or "nombre_producto" not in data:
        return jsonify({"error": "Falta el nombre del producto"}), 400
    
    nombre_producto = data["nombre_producto"]
    
    messages = [
        {"role": "system", "content": (
            "Eres un asistente especializado en crear descripciones atractivas y breves de productos para vender. "
            "El usuario solo te proporcionará el nombre del producto, y tú debes generar una descripción corta, llamativa y convincente en español. "
            "No uses emojis ni símbolos especiales. "
            "La respuesta debe ser solo la descripción, sin saludos, introducciones o texto adicional."
        )},
        {"role": "user", "content": nombre_producto}
    ]



    try:
        response = client.chat.completions.create(
            model="cognitivecomputations/dolphin3.0-r1-mistral-24b:free",  # Modelo válido
            messages=messages
        )
        descripcion = response.choices[0].message.content
        return jsonify({"nombre_producto": nombre_producto, "descripcion": descripcion})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Ruta para verificar el estado del servicio
@openai_bp.route('/info', methods=['GET'])
def info():
    return jsonify({
        "servicio": "API de generación de descripciones de productos",
        "estado": "activo"
    })
