# =============================================================================
# controllers/vehiculos.py
# Rutas: /vehiculos
# Maneja: marca, modelo, valor_vehiculo + resolución de pendientes con modal
# =============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from database import get_cursor, commit, rollback
from config import Config
import models.vehiculo as vehiculo_model
import models.clasificacion as clasificacion_model
from services.pendientes import resolver_regla_pendiente, resolver_excepcion_pendiente

bp = Blueprint('vehiculos', __name__)


@bp.route('/vehiculos')
def vehiculos():
    cur = get_cursor()

    page          = request.args.get('page', 1, type=int)
    per_page      = request.args.get('per_page', Config.PER_PAGE, type=int)
    marca_id      = request.args.get('marca_id', type=int)
    modelo_search = request.args.get('modelo', '').strip()
    offset        = (page - 1) * per_page

    total   = vehiculo_model.count_modelos(cur, marca_id, modelo_search)
    modelos = vehiculo_model.get_modelos_paginados(cur, marca_id, modelo_search, per_page, offset)
    marcas  = vehiculo_model.get_all_marcas(cur)
    cur.close()

    pages = (total + per_page - 1) // per_page if per_page else 1

    return render_template('vehiculos.html',
                           modelos=modelos,
                           marcas=marcas,
                           page=page, pages=pages,
                           per_page=per_page, total=total,
                           marca_id=marca_id, modelo_search=modelo_search)


@bp.route('/api/modelos_por_marca/<int:marca_id>')
def api_modelos_por_marca(marca_id):
    cur = get_cursor()
    modelos = vehiculo_model.get_modelos_por_marca(cur, marca_id)
    cur.close()
    return jsonify([{'id': r[0], 'nombre': r[1]} for r in modelos])


# ==============================================================================
# AGREGAR MODELO
# ==============================================================================

@bp.route('/vehiculos/agregar', methods=['POST'])
def agregar_modelo():
    id_marca           = request.form.get('id_marca')
    nueva_marca_nombre = request.form.get('nueva_marca', '').strip()
    nombre_modelo      = request.form['nombre_modelo'].strip()
    comentario         = request.form.get('comentario', '').strip()

    if not nombre_modelo:
        flash('El nombre del modelo es obligatorio.', 'danger')
        return redirect(url_for('vehiculos.vehiculos'))

    cur = get_cursor()
    try:
        # ── Resolver marca ────────────────────────────────────────────────
        if nueva_marca_nombre:
            if vehiculo_model.get_marca_by_nombre(cur, nueva_marca_nombre):
                flash(f'La marca "{nueva_marca_nombre}" ya existe. Usa la existente.', 'warning')
                return redirect(url_for('vehiculos.vehiculos'))

            vehiculo_model.insert_marca(cur, nueva_marca_nombre)
            commit()
            from database import get_last_insert_id
            id_marca = get_last_insert_id(cur)

            reglas_pend = _verificar_reglas_pendientes_marca(cur, nueva_marca_nombre, id_marca)
            if reglas_pend:
                vehiculo_model.insert_modelo(cur, id_marca, nombre_modelo, comentario)
                commit()
                nuevo_id_modelo = get_last_insert_id(cur)
                return jsonify({
                    'success':       True,
                    'tipo':          'reglas_pendientes',
                    'reglas_pend':   reglas_pend,
                    'id_marca':      id_marca,
                    'nombre_marca':  nueva_marca_nombre,
                    'id_modelo':     nuevo_id_modelo,
                    'nombre_modelo': nombre_modelo,
                })

        elif not id_marca:
            flash('Debes seleccionar una marca o crear una nueva.', 'danger')
            return redirect(url_for('vehiculos.vehiculos'))

        # ── Insertar modelo ───────────────────────────────────────────────
        vehiculo_model.insert_modelo(cur, id_marca, nombre_modelo, comentario)
        commit()
        from database import get_last_insert_id
        nuevo_id_modelo = get_last_insert_id(cur)

        # Revisar excepciones pendientes para este modelo
        exc_pend = _verificar_excepciones_pendientes_modelo(cur, id_marca, nombre_modelo)
        if exc_pend:
            return jsonify({
                'success':       True,
                'tipo':          'excepciones_pendientes',
                'pendientes':    exc_pend,
                'id_modelo':     nuevo_id_modelo,
                'nombre_modelo': nombre_modelo,
            })

        # ── Éxito: devolver JSON con id_modelo para abrir modal de valores
        return jsonify({
            'success':       True,
            'tipo':          'modelo_creado',
            'id_modelo':     nuevo_id_modelo,
            'nombre_modelo': nombre_modelo,
        })

    except Exception as e:
        rollback()
        flash(f'Error: {e}', 'danger')
    finally:
        cur.close()

    return redirect(url_for('vehiculos.vehiculos'))


def _verificar_reglas_pendientes_marca(cur, nombre_marca, id_marca):
    rows = clasificacion_model.get_reglas_pendientes_por_marca(cur, nombre_marca)
    return [{
        'id_pendiente':   r[0],
        'id_empresa':     r[1],
        'empresa':        r[2],
        'id_tipo_riesgo': r[3],
        'tipo_riesgo':    r[4],
        'nombre_modelo':  r[5],
        'anio_inicio':    r[6],
        'anio_fin':       r[7],
        'suma_min':       str(r[8]) if r[8] else None,
        'suma_max':       str(r[9]) if r[9] else None,
        'nota_regla':     r[10] or '',
        'id_marca':       id_marca,
        'nombre_marca':   nombre_marca,
    } for r in rows]


def _verificar_excepciones_pendientes_modelo(cur, id_marca, nombre_modelo):
    rows = clasificacion_model.get_excepciones_pendientes_para_modelo(cur, id_marca, nombre_modelo)
    return [{
        'id_pendiente':  r[0],
        'id_regla':      r[1],
        'nombre_patron': r[2],
        'tipo':          r[3],
        'riesgo_alt':    r[5],
        'empresa':       r[6],
        'nota_regla':    r[7] or '',
    } for r in rows]


# ==============================================================================
# RESOLVER PENDIENTES
# ==============================================================================

@bp.route('/vehiculos/resolver_regla_pendiente', methods=['POST'])
def resolver_regla_pendiente():
    data         = request.get_json()
    id_pendiente = data.get('id_pendiente')
    id_marca     = data.get('id_marca')
    confirmar    = data.get('confirmar', False)

    cur = get_cursor()
    try:
        from services.pendientes import resolver_regla_pendiente as svc_resolver_regla
        resultado = svc_resolver_regla(cur, id_pendiente, id_marca, confirmar, commit)
        return jsonify(resultado)
    except Exception as e:
        rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        cur.close()


@bp.route('/vehiculos/resolver_pendiente', methods=['POST'])
def resolver_pendiente():
    data         = request.get_json()
    id_pendiente = data.get('id_pendiente')
    id_modelo    = data.get('id_modelo')
    confirmar    = data.get('confirmar', False)

    cur = get_cursor()
    try:
        from services.pendientes import resolver_excepcion_pendiente as svc_resolver_exc
        resultado = svc_resolver_exc(cur, id_pendiente, id_modelo, confirmar, commit)
        return jsonify(resultado)
    except Exception as e:
        rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        cur.close()


# ==============================================================================
# EDITAR / ELIMINAR MODELO
# ==============================================================================

@bp.route('/vehiculos/editar/<int:id>', methods=['POST'])
def editar_modelo(id):
    id_marca      = request.form['id_marca']
    nombre_modelo = request.form['nombre_modelo'].strip()
    comentario    = request.form.get('comentario', '').strip()

    if not nombre_modelo:
        flash('El nombre del modelo es obligatorio.', 'danger')
        return redirect(url_for('vehiculos.vehiculos'))

    cur = get_cursor()
    try:
        vehiculo_model.update_modelo(cur, id, id_marca, nombre_modelo, comentario)
        commit()
        flash('Modelo actualizado correctamente.', 'success')
    except Exception as e:
        flash(f'Error al actualizar: {e}', 'danger')
    finally:
        cur.close()
    return redirect(url_for('vehiculos.vehiculos'))


@bp.route('/vehiculos/eliminar/<int:id>', methods=['POST'])
def eliminar_modelo(id):
    cur = get_cursor()
    try:
        vehiculo_model.delete_modelo(cur, id)
        commit()
        flash('Modelo eliminado correctamente.', 'success')
    except Exception as e:
        flash(f'Error al eliminar: {e}', 'danger')
    finally:
        cur.close()
    return redirect(url_for('vehiculos.vehiculos'))


# ==============================================================================
# VALORES VEHICULARES — API
# ==============================================================================

@bp.route('/api/valores_modelo/<int:id_modelo>')
def api_valores_modelo(id_modelo):
    """Devuelve todos los valores registrados para un modelo."""
    cur = get_cursor()
    try:
        valores = vehiculo_model.get_todos_valores_modelo(cur, id_modelo)
        # Info del modelo
        mod = vehiculo_model.get_modelo_by_id(cur, id_modelo)
        return jsonify({
            'ok':           True,
            'id_modelo':    id_modelo,
            'nombre':       f"{mod[3]} {mod[2]}" if mod else '',
            'valores':      valores,
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})
    finally:
        cur.close()


@bp.route('/api/valores_modelo/<int:id_modelo>/guardar', methods=['POST'])
def api_guardar_valores_modelo(id_modelo):
    """
    Guarda (upsert) los valores enviados para un modelo.
    Espera JSON:
    {
        "vrn": 25000.00,          ← null si no se ingresa
        "historicos": [
            {"anio": 2022, "valor": 21000},
            {"anio": 2021, "valor": 18500},
            ...
        ]
    }
    """
    data = request.get_json()
    cur  = get_cursor()
    try:
        insertados  = 0
        actualizados = 0

        # VRN
        vrn = data.get('vrn')
        if vrn is not None and float(vrn) > 0:
            accion = vehiculo_model.upsert_valor_vehiculo(cur, id_modelo, None, float(vrn), 'VRN')
            if accion == 'inserted':
                insertados += 1
            else:
                actualizados += 1

        # Históricos
        for item in data.get('historicos', []):
            anio  = item.get('anio')
            valor = item.get('valor')
            if anio and valor and float(valor) > 0:
                accion = vehiculo_model.upsert_valor_vehiculo(
                    cur, id_modelo, int(anio), float(valor), 'HISTORICO'
                )
                if accion == 'inserted':
                    insertados += 1
                else:
                    actualizados += 1

        commit()
        return jsonify({
            'ok':         True,
            'insertados': insertados,
            'actualizados': actualizados,
        })

    except Exception as e:
        rollback()
        return jsonify({'ok': False, 'error': str(e)})
    finally:
        cur.close()


@bp.route('/api/valores_modelo/eliminar/<int:id_valor>', methods=['POST'])
def api_eliminar_valor(id_valor):
    """Elimina un valor vehicular por su id_valor."""
    cur = get_cursor()
    try:
        vehiculo_model.delete_valor_vehiculo(cur, id_valor)
        commit()
        return jsonify({'ok': True})
    except Exception as e:
        rollback()
        return jsonify({'ok': False, 'error': str(e)})
    finally:
        cur.close()
