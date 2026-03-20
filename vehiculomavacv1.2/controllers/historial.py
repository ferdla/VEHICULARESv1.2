# =============================================================================
# controllers/historial.py
# Rutas: /historial
# =============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from database import get_cursor, commit
from config import Config
import models.historial as historial_model

bp = Blueprint('historial', __name__)


@bp.route('/historial')
def historial():
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

    total       = historial_model.count_historial(cur, filtros)
    cotizaciones = historial_model.get_historial_paginado(cur, filtros, per_page, offset)
    cur.close()

    pages = (total + per_page - 1) // per_page if per_page else 1

    return render_template('historial.html',
                           cotizaciones=cotizaciones,
                           page=page,
                           pages=pages,
                           total=total,
                           per_page=per_page,
                           filtros=filtros)


@bp.route('/historial/eliminar/<int:id_cotizacion>', methods=['POST'])
def eliminar_cotizacion(id_cotizacion):
    cur = get_cursor()
    try:
        historial_model.delete_cotizacion(cur, id_cotizacion)
        commit()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
    finally:
        cur.close()
