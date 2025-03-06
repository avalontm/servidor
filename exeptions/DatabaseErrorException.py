class DatabaseErrorException(Exception):
    """Excepción personalizada para errores en la base de datos."""
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
