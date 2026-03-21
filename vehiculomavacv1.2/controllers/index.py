# =============================================================================
# controllers/index.py
# Rutas: /
# Maneja: empresa, tipo_riesgo, empresa_tipo_riesgo
# =============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from database import get_cursor, commit
import models.empresa as empresa_model

bp = Blueprint('index', __name__)


@bp.route('/')
def index():
    cur = get_cursor()
    empresas     = empresa_model.get_all_empresas(cur)
    tipo_riesgo  = empresa_model.get_all_tipos_riesgo(cur)
    asignaciones = empresa_model.get_all_asignaciones(cur)
    cur.close()
    return render_template('index.html',
                           empresas=empresas,
                           tipo_riesgo=tipo_riesgo,
                           asignaciones=asignaciones)


# ── Empresas ──────────────────────────────────────────────────────────────────

@bp.route('/agregar_empresa', methods=['POST'])
def agregar_empresa():
    nombre = request.form['nombre_empresa']
    activo = 1 if 'activo' in request.form else 0
    cur = get_cursor()
    try:
        empresa_model.insert_empresa(cur, nombre, activo)
        commit()
        flash('Empresa agregada exitosamente', 'success')
    except Exception as e:
        flash(f'Error al agregar empresa: {e}', 'danger')
    finally:
        cur.close()
    return redirect(url_for('index.index'))


@bp.route('/editar_empresa/<int:id>', methods=['POST'])
def editar_empresa(id):
    nombre = request.form['nombre_empresa']
    activo = request.form.get('activo', 0)
    cur = get_cursor()
    try:
        empresa_model.update_empresa(cur, id, nombre, activo)
        commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        cur.close()


# ── Tipos de Riesgo ───────────────────────────────────────────────────────────

@bp.route('/agregar_tipo_riesgo', methods=['POST'])
def agregar_tipo_riesgo():
    nombre = request.form['nombre_riesgo']
    codigo = request.form['codigo_interno']
    cur = get_cursor()
    try:
        empresa_model.insert_tipo_riesgo(cur, nombre, codigo)
        commit()
        flash('Tipo de riesgo agregado exitosamente', 'success')
    except Exception as e:
        flash(f'Error al agregar tipo de riesgo: {e}', 'danger')
    finally:
        cur.close()
    return redirect(url_for('index.index'))


@bp.route('/editar_tipo_riesgo/<int:id>', methods=['POST'])
def editar_tipo_riesgo(id):
    nombre = request.form['nombre_riesgo']
    codigo = request.form['codigo_interno']
    cur = get_cursor()
    try:
        empresa_model.update_tipo_riesgo(cur, id, nombre, codigo)
        commit()
        flash('Tipo de riesgo actualizado exitosamente', 'success')
    except Exception as e:
        flash(f'Error al actualizar tipo de riesgo: {e}', 'danger')
    finally:
        cur.close()
    return redirect(url_for('index.index'))


@bp.route('/eliminar_tipo_riesgo/<int:id>', methods=['POST'])
def eliminar_tipo_riesgo(id):
    cur = get_cursor()
    try:
        empresa_model.delete_tipo_riesgo(cur, id)
        commit()
        flash('Tipo de riesgo eliminado exitosamente', 'success')
    except Exception as e:
        flash(f'Error al eliminar tipo de riesgo: {e} (posiblemente está en uso)', 'danger')
    finally:
        cur.close()
    return redirect(url_for('index.index'))


# ── Asignaciones empresa_tipo_riesgo ──────────────────────────────────────────

@bp.route('/agregar_asignacion', methods=['POST'])
def agregar_asignacion():
    id_empresa     = request.form['id_empresa']
    id_tipo_riesgo = request.form['id_tipo_riesgo']
    activo         = 1 if 'activo' in request.form else 0
    cur = get_cursor()
    try:
        empresa_model.insert_asignacion(cur, id_empresa, id_tipo_riesgo, activo)
        commit()
        flash('Asignación agregada exitosamente', 'success')
    except Exception as e:
        flash(f'Error al agregar asignación: {e}', 'danger')
    finally:
        cur.close()
    return redirect(url_for('index.index'))


@bp.route('/editar_asignacion/<int:id_empresa>/<int:id_tipo_riesgo>', methods=['POST'])
def editar_asignacion(id_empresa, id_tipo_riesgo):
    activo = 1 if 'activo' in request.form else 0
    cur = get_cursor()
    try:
        empresa_model.update_asignacion(cur, id_empresa, id_tipo_riesgo, activo)
        commit()
        flash('Asignación actualizada exitosamente', 'success')
    except Exception as e:
        flash(f'Error al actualizar asignación: {e}', 'danger')
    finally:
        cur.close()
    return redirect(url_for('index.index'))


@bp.route('/eliminar_asignacion/<int:id_empresa>/<int:id_tipo_riesgo>', methods=['POST'])
def eliminar_asignacion(id_empresa, id_tipo_riesgo):
    cur = get_cursor()
    try:
        empresa_model.delete_asignacion(cur, id_empresa, id_tipo_riesgo)
        commit()
        flash('Asignación eliminada exitosamente', 'success')
    except Exception as e:
        flash(f'Error al eliminar asignación: {e}', 'danger')
    finally:
        cur.close()
    return redirect(url_for('index.index'))
