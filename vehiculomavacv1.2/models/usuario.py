# =============================================================================
# models/usuario.py
# Queries de: usuario
# =============================================================================

from werkzeug.security import generate_password_hash, check_password_hash


# ── Autenticación ─────────────────────────────────────────────────────────────

def get_usuario_by_username(cur, username):
    cur.execute(
        "SELECT id_usuario, username, password_hash, rol, activo FROM usuario WHERE username = %s",
        (username,)
    )
    return cur.fetchone()


def verificar_password(password_hash, password):
    """Verifica si el password ingresado coincide con el hash almacenado."""
    return check_password_hash(password_hash, password)


# ── CRUD usuarios (solo admin) ────────────────────────────────────────────────

def get_all_usuarios(cur):
    cur.execute(
        "SELECT id_usuario, username, rol, activo, fecha_creacion FROM usuario ORDER BY id_usuario"
    )
    return cur.fetchall()


def insert_usuario(cur, username, password, rol):
    password_hash = generate_password_hash(password)
    cur.execute(
        "INSERT INTO usuario (username, password_hash, rol, activo) VALUES (%s, %s, %s, 1)",
        (username, password_hash, rol)
    )


def update_usuario_password(cur, id_usuario, nuevo_password):
    password_hash = generate_password_hash(nuevo_password)
    cur.execute(
        "UPDATE usuario SET password_hash = %s WHERE id_usuario = %s",
        (password_hash, id_usuario)
    )


def update_usuario_rol_activo(cur, id_usuario, rol, activo):
    cur.execute(
        "UPDATE usuario SET rol = %s, activo = %s WHERE id_usuario = %s",
        (rol, activo, id_usuario)
    )


def delete_usuario(cur, id_usuario):
    cur.execute("DELETE FROM usuario WHERE id_usuario = %s", (id_usuario,))


def count_admins(cur):
    """Verifica que siempre quede al menos un admin activo."""
    cur.execute(
        "SELECT COUNT(*) FROM usuario WHERE rol = 'admin' AND activo = 1"
    )
    return cur.fetchone()[0]
