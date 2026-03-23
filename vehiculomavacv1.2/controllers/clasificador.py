# =============================================================================
# controllers/clasificador.py
# Rutas: /clasificador_riesgos
# =============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from database import get_cursor, commit, get_last_insert_id  # ← centralizado
import models.empresa as empresa_model
import models.vehiculo as vehiculo_model
import models.clasificacion as clasificacion_model

bp = Blueprint('clasificador', __name__)


@bp.route('/clasificador_riesgos')
def clasificador_riesgos():
    cur = get_cursor()

    empresa_id     = request.args.get('empresa_id', type=int)
    tipo_riesgo_id = request.args.get('tipo_riesgo_id', type=int)
    marca_id       = request.args.get('marca_id', type=int)

    empresas          = empresa_model.get_empresas_activas(cur)
    tipos_riesgo      = empresa_model.get_all_tipos_riesgo(cur)
    marcas            = vehiculo_model.get_all_marcas(cur)
    reglas            = clasificacion_model.get_reglas(cur, empresa_id, tipo_riesgo_id, marca_id)
    reglas_pendientes = clasificacion_model.get_reglas_pendientes(cur, empresa_id)

    cur.close()
    return render_template('clasificador_riesgos.html',
                           empresas=empresas,
                           tipos_riesgo=tipos_riesgo,
                           marcas=marcas,
                           empresa_id=empresa_id,
                           tipo_riesgo_id=tipo_riesgo_id,
                           marca_id=marca_id,
                           reglas=reglas,
                           reglas_pendientes=reglas_pendientes)


# ==============================================================================
# API: EXCEPCIONES DE UNA REGLA
# ==============================================================================

@bp.route('/api/excepciones_por_regla/<int:id_regla>')
def api_excepciones_por_regla(id_regla):
    cur = get_cursor()

    confirmadas = [
        {'id': r[0], 'modelo': r[1], 'accion': r[2],
         'riesgo': r[3], 'nota': r[4], 'tipo': 'confirmada'}
        for r in clasificacion_model.get_excepciones_confirmadas_por_regla(cur, id_regla)
    ]
    pendientes = [
        {'id': r[0], 'modelo': f"{r[1]} ⏳", 'accion': r[2],
         'riesgo': r[3], 'nota': r[4], 'tipo': 'pendiente'}
        for r in clasificacion_model.get_excepciones_pendientes_por_regla(cur, id_regla)
    ]

    cur.close()
    return jsonify(confirmadas + pendientes)


# ==============================================================================
# AGREGAR REGLA
# ==============================================================================

@bp.route('/clasificador_riesgos/agregar_regla', methods=['POST'])
def agregar_regla():
    cur = get_cursor()
    try:
        id_empresa          = request.form['id_empresa']
        id_tipo_riesgo      = request.form['id_tipo_riesgo']
        id_marca_form       = request.form.get('id_marca') or None
        nombre_marca_nueva  = request.form.get('nombre_marca_nueva', '').strip()
        id_modelo_form      = request.form.get('id_modelo') or None
        nombre_modelo_nuevo = request.form.get('nombre_modelo_nuevo', '').strip()
        anio_inicio = request.form.get('anio_inicio') or None
        anio_fin    = request.form.get('anio_fin') or None
        suma_min    = request.form.get('suma_min') or None
        suma_max    = request.form.get('suma_max') or None
        nota_regla  = request.form.get('nota_regla') or None

        if nombre_marca_nueva:
            marca_row = vehiculo_model.get_marca_by_nombre(cur, nombre_marca_nueva)
            if marca_row:
                _crear_regla_confirmada(cur, id_empresa, id_tipo_riesgo, marca_row[0],
                                        id_modelo_form, nombre_modelo_nuevo,
                                        anio_inicio, anio_fin, suma_min, suma_max, nota_regla)
                flash('Regla guardada (la marca ya existía en BD).', 'success')
            else:
                clasificacion_model.insert_regla_pendiente(
                    cur, id_empresa, id_tipo_riesgo, nombre_marca_nueva,
                    nombre_modelo_nuevo or None,
                    anio_inicio, anio_fin, suma_min, suma_max, nota_regla
                )
                commit()
                flash(f'Marca "{nombre_marca_nueva}" no existe. Regla guardada como pendiente.', 'warning')
                return redirect(url_for('clasificador.clasificador_riesgos'))

        elif id_marca_form:
            _crear_regla_confirmada(cur, id_empresa, id_tipo_riesgo, id_marca_form,
                                    id_modelo_form, nombre_modelo_nuevo,
                                    anio_inicio, anio_fin, suma_min, suma_max, nota_regla)
            flash('Regla guardada correctamente.', 'success')
        else:
            flash('Debes seleccionar una marca o escribir una nueva.', 'danger')

    except Exception as e:
        flash(f'Error al guardar: {e}', 'danger')
    finally:
        cur.close()
    return redirect(url_for('clasificador.clasificador_riesgos'))


def _crear_regla_confirmada(cur, id_empresa, id_tipo_riesgo, id_marca,
                             id_modelo, nombre_modelo_nuevo,
                             anio_inicio, anio_fin, suma_min, suma_max, nota_regla):
    id_modelo_final = id_modelo or None

    if nombre_modelo_nuevo and not id_modelo:
        mod_row = vehiculo_model.get_modelo_by_marca_nombre(cur, id_marca, nombre_modelo_nuevo)
        id_modelo_final = mod_row[0] if mod_row else None

    clasificacion_model.insert_regla(
        cur, id_empresa, id_tipo_riesgo, id_marca, id_modelo_final,
        anio_inicio, anio_fin, suma_min, suma_max, nota_regla
    )
    commit()

    # Si el modelo específico no existe aún → excepcion_pendiente
    if nombre_modelo_nuevo and not id_modelo and id_modelo_final is None:
        if not vehiculo_model.get_modelo_by_marca_nombre(cur, id_marca, nombre_modelo_nuevo):
            id_rc = get_last_insert_id(cur)  # ← id de regla_clasificacion, desde database.py
            clasificacion_model.insert_excepcion_pendiente(
                cur, id_rc, nombre_modelo_nuevo, 'INCLUIR_SOLO', None,
                f'Modelo específico pendiente: {nombre_modelo_nuevo}'
            )
            commit()


# ==============================================================================
# AGREGAR EXCEPCIÓN
# ==============================================================================

@bp.route('/clasificador_riesgos/agregar_excepcion', methods=['POST'])
def agregar_excepcion():
    cur = get_cursor()
    try:
        id_regla    = request.form['id_regla_clasificacion']
        texto       = request.form['texto_modelo'].strip()
        tipo_exc    = request.form['tipo_excepcion']
        nota_exc    = request.form.get('nota_excepcion') or None
        id_tipo_alt = request.form.get('id_tipo_riesgo_alternativo') or None
        if id_tipo_alt == '0':
            id_tipo_alt = None

        id_marca = clasificacion_model.get_id_marca_de_regla(cur, id_regla)
        if not id_marca:
            flash('Regla no encontrada.', 'danger')
            return redirect(url_for('clasificador.clasificador_riesgos'))

        # Aplicar a modelos existentes
        ids_modelos = clasificacion_model.get_modelos_existentes_para_excepcion(cur, id_marca, texto)
        inserted = 0
        for id_modelo in ids_modelos:
            try:
                clasificacion_model.upsert_excepcion_confirmada(
                    cur, id_regla, id_modelo, tipo_exc, id_tipo_alt, nota_exc
                )
                inserted += 1
            except Exception:
                pass

        # Siempre guardar en pendiente para modelos futuros
        if clasificacion_model.count_excepcion_pendiente_existente(cur, id_regla, texto) == 0:
            clasificacion_model.insert_excepcion_pendiente(
                cur, id_regla, texto, tipo_exc, id_tipo_alt, nota_exc
            )

        commit()

        if inserted > 0:
            flash(f'Se aplicaron {inserted} excepción(es) a modelos existentes con "{texto}". '
                  f'Patrón guardado también para modelos futuros.', 'success')
        else:
            flash(f'No hay modelos existentes con "{texto}". '
                  f'Excepción guardada como pendiente.', 'warning')

    except Exception as e:
        flash(f'Error: {e}', 'danger')
    finally:
        cur.close()
    return redirect(url_for('clasificador.clasificador_riesgos'))


# ==============================================================================
# ELIMINAR
# ==============================================================================

@bp.route('/clasificador_riesgos/eliminar_excepcion/<int:id_excepcion>', methods=['POST'])
def eliminar_excepcion(id_excepcion):
    cur = get_cursor()
    try:
        clasificacion_model.delete_excepcion_confirmada(cur, id_excepcion)
        commit()
        flash('Excepción eliminada.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    finally:
        cur.close()
    return redirect(url_for('clasificador.clasificador_riesgos'))


@bp.route('/clasificador_riesgos/eliminar_excepcion_pendiente/<int:id_pendiente>', methods=['POST'])
def eliminar_excepcion_pendiente(id_pendiente):
    cur = get_cursor()
    try:
        clasificacion_model.delete_excepcion_pendiente(cur, id_pendiente)
        commit()
        flash('Excepción pendiente eliminada.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    finally:
        cur.close()
    return redirect(url_for('clasificador.clasificador_riesgos'))


@bp.route('/clasificador_riesgos/eliminar_regla_pendiente/<int:id_regla_pend>', methods=['POST'])
def eliminar_regla_pendiente(id_regla_pend):
    cur = get_cursor()
    try:
        clasificacion_model.delete_regla_pendiente(cur, id_regla_pend)
        commit()
        flash('Regla pendiente eliminada.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    finally:
        cur.close()
    return redirect(url_for('clasificador.clasificador_riesgos'))


@bp.route('/clasificador_riesgos/eliminar_regla/<int:id_regla>', methods=['POST'])
def eliminar_regla(id_regla):
    cur = get_cursor()
    try:
        clasificacion_model.delete_regla(cur, id_regla)
        commit()
        flash('Regla eliminada.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    finally:
        cur.close()
    return redirect(url_for('clasificador.clasificador_riesgos'))


# ==============================================================================
# API: PENDIENTES GLOBALES
# ==============================================================================

@bp.route('/api/pendientes_globales')
def api_pendientes_globales():
    cur = get_cursor()
    exc, reg = clasificacion_model.count_pendientes_globales(cur)
    cur.close()
    return jsonify({'excepciones_pendientes': exc, 'reglas_pendientes': reg, 'total': exc + reg})