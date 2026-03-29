# =============================================================================
# controllers/historial.py
# Rutas: /historial, /historial/mis
# =============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from database import get_cursor, commit
from config import Config
import models.historial as historial_model
from controllers.auth import login_required

bp = Blueprint('historial', __name__)


@bp.route('/historial')
@login_required
def historial():
    """
    Vista principal del historial.
    - Admin: ve TODAS las cotizaciones de todos los usuarios.
    - Trabajador: ve TODAS las cotizaciones también (para cubrir ausencias),
                  pero con indicador de quién hizo cada una.
    """
    cur = get_cursor()

    page     = request.args.get('page', 1, type=int)
    per_page = Config.PER_PAGE
    offset   = (page - 1) * per_page

    filtros = {
        'cliente':     request.args.get('cliente', '').strip(),
        'placa':       request.args.get('placa', '').strip(),
        'fecha_desde': request.args.get('fecha_desde', '').strip(),
        'fecha_hasta': request.args.get('fecha_hasta', '').strip(),
    }

    # Ambos roles ven todas las cotizaciones aquí
    total        = historial_model.count_historial(cur, filtros)
    cotizaciones = historial_model.get_historial_paginado(cur, filtros, per_page, offset)
    cur.close()

    pages = (total + per_page - 1) // per_page if per_page else 1

    return render_template('historial.html',
                           cotizaciones=cotizaciones,
                           page=page, pages=pages,
                           total=total, per_page=per_page,
                           filtros=filtros,
                           vista='todas')


@bp.route('/historial/mis')
@login_required
def mis_cotizaciones():
    """
    Vista de cotizaciones propias del usuario logueado.
    Disponible para ambos roles.
    """
    cur = get_cursor()

    page     = request.args.get('page', 1, type=int)
    per_page = Config.PER_PAGE
    offset   = (page - 1) * per_page

    filtros = {
        'cliente':     request.args.get('cliente', '').strip(),
        'placa':       request.args.get('placa', '').strip(),
        'fecha_desde': request.args.get('fecha_desde', '').strip(),
        'fecha_hasta': request.args.get('fecha_hasta', '').strip(),
    }

    id_usuario_actual = session.get('id_usuario')

    total        = historial_model.count_historial(cur, filtros, id_usuario=id_usuario_actual)
    cotizaciones = historial_model.get_historial_paginado(
        cur, filtros, per_page, offset, id_usuario=id_usuario_actual
    )
    cur.close()

    pages = (total + per_page - 1) // per_page if per_page else 1

    return render_template('historial.html',
                           cotizaciones=cotizaciones,
                           page=page, pages=pages,
                           total=total, per_page=per_page,
                           filtros=filtros,
                           vista='mis')


@bp.route('/historial/eliminar/<int:id_cotizacion>', methods=['POST'])
@login_required
def eliminar_cotizacion(id_cotizacion):
    """Solo admin puede eliminar. Trabajador recibe 403."""
    if session.get('rol') != 'admin':
        return jsonify({'ok': False, 'error': 'Sin permisos para eliminar.'}), 403

    cur = get_cursor()
    try:
        historial_model.delete_cotizacion(cur, id_cotizacion)
        commit()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
    finally:
        cur.close()
