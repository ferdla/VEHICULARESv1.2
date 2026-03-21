import os

class Config:
    # Base de datos
    MYSQL_HOST     = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER     = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'root')
    MYSQL_DB       = os.environ.get('MYSQL_DB', 'MavacVehiculos')

    # Flask
    SECRET_KEY     = os.environ.get('SECRET_KEY', 'dev_key_cambiar_en_produccion')

    # Paginación
    PER_PAGE       = 20
