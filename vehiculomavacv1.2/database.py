from flask_mysqldb import MySQL

mysql = MySQL()


def get_cursor():
    """Devuelve un cursor activo. Usar dentro de un contexto de aplicación Flask."""
    return mysql.connection.cursor()


def commit():
    mysql.connection.commit()


def rollback():
    mysql.connection.rollback()