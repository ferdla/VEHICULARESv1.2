# =============================================================================
# controllers/auth.py
# Rutas: /login, /logout, /admin/usuarios
# =============================================================================

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session, jsonify)
from functools import wraps
from database import get_cursor, commit
import models.usuario as usuario_model

bp = Blueprint('auth', __name__)


# ==============================================================================
# DECORADORES DE ACCESO
# ==============================================================================

def login_required(f):
    """Requiere que el usuario esté logueado."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'id_usuario' not in session:
            flash('Debes iniciar sesión para continuar.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Requiere rol admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'id_usuario' not in session:
            flash('Debes iniciar sesión para continuar.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('rol') != 'admin':
            flash('No tienes permisos para acceder a esta sección.', 'danger')
            return redirect(url_for('cotizador.cotizador'))
        return f(*args, **kwargs)
    return decorated


# ==============================================================================
# LOGIN / LOGOUT
# ==============================================================================

@bp.route('/login', methods=['GET', 'POST'])
def login():
    # Si ya está logueado, redirigir
    if 'id_usuario' in session:
        return redirect(url_for('cotizador.cotizador'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Ingresa usuario y contraseña.', 'danger')
            return render_template('login.html')

        cur = get_cursor()
        try:
            usuario = usuario_model.get_usuario_by_username(cur, username)

            if not usuario:
                flash('Usuario o contraseña incorrectos.', 'danger')
                return render_template('login.html')

            id_u, uname, pwd_hash, rol, activo = usuario

            if not activo:
                flash('Tu cuenta está desactivada. Contacta al administrador.', 'danger')
                return render_template('login.html')

            if not usuario_model.verificar_password(pwd_hash, password):
                flash('Usuario o contraseña incorrectos.', 'danger')
                return render_template('login.html')

            # Login exitoso
            session.permanent = True
            session['id_usuario'] = id_u
            session['username']   = uname
            session['rol']        = rol

            # Redirigir a la página que intentaba acceder, o al cotizador
            next_url = request.args.get('next') or url_for('cotizador.cotizador')
            return redirect(next_url)

        finally:
            cur.close()

    return render_template('login.html')


@bp.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente.', 'success')
    return redirect(url_for('auth.login'))


# ==============================================================================
# GESTIÓN DE USUARIOS (solo admin)
# ==============================================================================

@bp.route('/admin/usuarios')
@admin_required
def admin_usuarios():
    cur = get_cursor()
    usuarios = usuario_model.get_all_usuarios(cur)
    cur.close()
    return render_template('admin_usuarios.html', usuarios=usuarios)


@bp.route('/admin/usuarios/crear', methods=['POST'])
@admin_required
def crear_usuario():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    rol      = request.form.get('rol', 'trabajador')

    if not username or not password:
        flash('Username y contraseña son obligatorios.', 'danger')
        return redirect(url_for('auth.admin_usuarios'))

    if rol not in ('admin', 'trabajador'):
        flash('Rol inválido.', 'danger')
        return redirect(url_for('auth.admin_usuarios'))

    cur = get_cursor()
    try:
        usuario_model.insert_usuario(cur, username, password, rol)
        commit()
        flash(f'Usuario "{username}" creado correctamente.', 'success')
    except Exception as e:
        if 'Duplicate' in str(e):
            flash(f'El username "{username}" ya existe.', 'danger')
        else:
            flash(f'Error al crear usuario: {e}', 'danger')
    finally:
        cur.close()
    return redirect(url_for('auth.admin_usuarios'))


@bp.route('/admin/usuarios/editar/<int:id_usuario>', methods=['POST'])
@admin_required
def editar_usuario(id_usuario):
    rol    = request.form.get('rol', 'trabajador')
    activo = 1 if request.form.get('activo') else 0

    # Protección: no desactivar el último admin
    if activo == 0 or rol != 'admin':
        cur = get_cursor()
        if usuario_model.count_admins(cur) <= 1:
            cur.close()
            flash('No puedes desactivar o cambiar el rol del único administrador activo.', 'danger')
            return redirect(url_for('auth.admin_usuarios'))
        cur.close()

    cur = get_cursor()
    try:
        usuario_model.update_usuario_rol_activo(cur, id_usuario, rol, activo)
        commit()
        flash('Usuario actualizado correctamente.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    finally:
        cur.close()
    return redirect(url_for('auth.admin_usuarios'))


@bp.route('/admin/usuarios/cambiar_password/<int:id_usuario>', methods=['POST'])
@admin_required
def cambiar_password(id_usuario):
    nuevo_password = request.form.get('nuevo_password', '').strip()

    if len(nuevo_password) < 6:
        flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
        return redirect(url_for('auth.admin_usuarios'))

    cur = get_cursor()
    try:
        usuario_model.update_usuario_password(cur, id_usuario, nuevo_password)
        commit()
        flash('Contraseña actualizada correctamente.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    finally:
        cur.close()
    return redirect(url_for('auth.admin_usuarios'))


@bp.route('/admin/usuarios/eliminar/<int:id_usuario>', methods=['POST'])
@admin_required
def eliminar_usuario(id_usuario):
    # No eliminarse a sí mismo
    if id_usuario == session.get('id_usuario'):
        flash('No puedes eliminar tu propio usuario.', 'danger')
        return redirect(url_for('auth.admin_usuarios'))

    cur = get_cursor()
    try:
        # Verificar que no sea el último admin
        u = usuario_model.get_all_usuarios(cur)
        admins_activos = [x for x in u if x[2] == 'admin' and x[3] == 1]
        target = next((x for x in u if x[0] == id_usuario), None)

        if target and target[2] == 'admin' and len(admins_activos) <= 1:
            flash('No puedes eliminar el único administrador activo.', 'danger')
            return redirect(url_for('auth.admin_usuarios'))

        usuario_model.delete_usuario(cur, id_usuario)
        commit()
        flash('Usuario eliminado correctamente.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    finally:
        cur.close()
    return redirect(url_for('auth.admin_usuarios'))
