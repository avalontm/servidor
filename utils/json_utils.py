import json

def convertir_metodos_pago(metodos_pago_str):
    """Convierte una cadena JSON de métodos de pago en una lista filtrada de Python."""
    try:
        # Verificar si la cadena es válida y no está vacía
        if not metodos_pago_str:
            return []

        # Convertir de JSON a lista de Python
        metodos_pago = json.loads(metodos_pago_str)

        # Verificar si el resultado es una lista válida
        if not isinstance(metodos_pago, list):
            return []

        # Filtrar pagos con monto mayor a 0 y ordenar por fecha
        metodos_pago_filtrados = [
            pago for pago in metodos_pago if isinstance(pago, dict) and pago.get('monto', 0) > 0
        ]
        metodos_pago_filtrados.sort(key=lambda x: x.get('fecha', ''))

        return metodos_pago_filtrados

    except json.JSONDecodeError:
        print("Error: metodos_pago no es un JSON válido")
        return []