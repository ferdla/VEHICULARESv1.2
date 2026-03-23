from flask_mysqldb import MySQL

mysql = MySQL()


def get_cursor():
    """Devuelve un cursor activo. Usar dentro de un contexto de aplicación Flask."""
    return mysql.connection.cursor()


def commit():
    mysql.connection.commit()


def rollback():
    mysql.connection.rollback()


def get_last_insert_id(cur):
    """
    Devuelve el ID del último registro insertado en cualquier tabla.
    Centralizado aquí para que no dependa de ningún model específico.
    """
    cur.execute("SELECT LAST_INSERT_ID()")
    return cur.fetchone()[0]