# =============================================================================
# controllers/clasificador.py
# Rutas: /clasificador_riesgos
# =============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from database import get_cursor, commit, get_last_insert_id
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
# AGREGAR REGLA — ahora acepta múltiples marcas a la vez
# ==============================================================================

@bp.route('/clasificador_riesgos/agregar_regla', methods=['POST'])
def agregar_regla():
    cur = get_cursor()
    try:
        id_empresa     = request.form['id_empresa']
        id_tipo_riesgo = request.form['id_tipo_riesgo']
        anio_inicio    = request.form.get('anio_inicio') or None
        anio_fin       = request.form.get('anio_fin') or None
        suma_min       = request.form.get('suma_min') or None
        suma_max       = request.form.get('suma_max') or None
        nota_regla     = request.form.get('nota_regla') or None

        # ── Recoger listas de marcas, modelos y marcas nuevas ─────────────
        # Cada fila del formulario envía:
        #   tipo_marca[]         → 'existente' | 'nueva'
        #   id_marca[]           → id si existente, vacío si nueva
        #   nombre_marca_nueva[] → nombre si nueva, vacío si existente
        #   id_modelo[]          → id modelo específico (puede ser vacío = toda la marca)
        #   nombre_modelo_nuevo[]→ nombre modelo escrito manualmente

        tipos_marca         = request.form.getlist('tipo_marca[]')
        ids_marca           = request.form.getlist('id_marca[]')
        nombres_marca_nueva = request.form.getlist('nombre_marca_nueva[]')
        ids_modelo          = request.form.getlist('id_modelo[]')
        nombres_modelo_nuevo= request.form.getlist('nombre_modelo_nuevo[]')

        if not tipos_marca:
            flash('Debes agregar al menos una marca.', 'danger')
            return redirect(url_for('clasificador.clasificador_riesgos'))

        reglas_ok       = 0
        reglas_pend     = 0
        errores         = []

        for i, tipo_marca in enumerate(tipos_marca):
            id_marca_fila        = ids_marca[i] if i < len(ids_marca) else ''
            nombre_marca_nueva_f = nombres_marca_nueva[i].strip() if i < len(nombres_marca_nueva) else ''
            id_modelo_fila       = ids_modelo[i] if i < len(ids_modelo) else ''
            nombre_modelo_nuevo_f= nombres_modelo_nuevo[i].strip() if i < len(nombres_modelo_nuevo) else ''

            try:
                if tipo_marca == 'nueva' and nombre_marca_nueva_f:
                    # Verificar si la marca ya existe
                    marca_row = vehiculo_model.get_marca_by_nombre(cur, nombre_marca_nueva_f)
                    if marca_row:
                        # La marca ya existe, crear regla confirmada
                        _crear_regla_confirmada(
                            cur, id_empresa, id_tipo_riesgo, marca_row[0],
                            id_modelo_fila or None, nombre_modelo_nuevo_f,
                            anio_inicio, anio_fin, suma_min, suma_max, nota_regla
                        )
                        reglas_ok += 1
                    else:
                        # La marca no existe, crear regla pendiente
                        clasificacion_model.insert_regla_pendiente(
                            cur, id_empresa, id_tipo_riesgo, nombre_marca_nueva_f,
                            nombre_modelo_nuevo_f or None,
                            anio_inicio, anio_fin, suma_min, suma_max, nota_regla
                        )
                        commit()
                        reglas_pend += 1

                elif tipo_marca == 'existente' and id_marca_fila:
                    _crear_regla_confirmada(
                        cur, id_empresa, id_tipo_riesgo, id_marca_fila,
                        id_modelo_fila or None, nombre_modelo_nuevo_f,
                        anio_inicio, anio_fin, suma_min, suma_max, nota_regla
                    )
                    reglas_ok += 1
                else:
                    errores.append(f'Fila {i+1}: datos incompletos, se ignoró.')

            except Exception as e:
                errores.append(f'Fila {i+1}: {str(e)}')

        # ── Mensajes de resultado ─────────────────────────────────────────
        if reglas_ok > 0:
            flash(f'{reglas_ok} regla(s) guardada(s) correctamente.', 'success')
        if reglas_pend > 0:
            flash(f'{reglas_pend} regla(s) guardada(s) como pendiente (marca no existe en BD).', 'warning')
        for err in errores:
            flash(err, 'danger')

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

    if nombre_modelo_nuevo and not id_modelo and id_modelo_final is None:
        if not vehiculo_model.get_modelo_by_marca_nombre(cur, id_marca, nombre_modelo_nuevo):
            id_rc = get_last_insert_id(cur)
            clasificacion_model.insert_excepcion_pendiente(
                cur, id_rc, nombre_modelo_nuevo, 'INCLUIR_SOLO', None,
                f'Modelo específico pendiente: {nombre_modelo_nuevo}'
            )
            commit()


# ==============================================================================
# AGREGAR EXCEPCIÓN — acepta múltiples patrones a la vez
# ==============================================================================

@bp.route('/clasificador_riesgos/agregar_excepcion', methods=['POST'])
def agregar_excepcion():
    cur = get_cursor()
    try:
        id_regla    = request.form['id_regla_clasificacion']
        tipo_exc    = request.form['tipo_excepcion']
        nota_exc    = request.form.get('nota_excepcion') or None
        id_tipo_alt = request.form.get('id_tipo_riesgo_alternativo') or None
        if id_tipo_alt == '0':
            id_tipo_alt = None

        textos_raw = request.form.getlist('texto_modelo[]')
        textos = [t.strip() for t in textos_raw if t.strip()]

        if not textos:
            flash('Debes ingresar al menos un modelo o patrón.', 'danger')
            return redirect(url_for('clasificador.clasificador_riesgos'))

        id_marca = clasificacion_model.get_id_marca_de_regla(cur, id_regla)
        if not id_marca:
            flash('Regla no encontrada.', 'danger')
            return redirect(url_for('clasificador.clasificador_riesgos'))

        total_inserted   = 0
        total_pendientes = 0

        for texto in textos:
            ids_modelos = clasificacion_model.get_modelos_existentes_para_excepcion(
                cur, id_marca, texto
            )
            for id_modelo in ids_modelos:
                try:
                    clasificacion_model.upsert_excepcion_confirmada(
                        cur, id_regla, id_modelo, tipo_exc, id_tipo_alt, nota_exc
                    )
                    total_inserted += 1
                except Exception:
                    pass

            if clasificacion_model.count_excepcion_pendiente_existente(cur, id_regla, texto) == 0:
                clasificacion_model.insert_excepcion_pendiente(
                    cur, id_regla, texto, tipo_exc, id_tipo_alt, nota_exc
                )
                total_pendientes += 1

        commit()

        n = len(textos)
        if total_inserted > 0:
            flash(
                f'{n} patrón(es) procesado(s). '
                f'{total_inserted} excepción(es) aplicada(s) a modelos existentes. '
                f'{total_pendientes} patrón(es) guardado(s) para modelos futuros.',
                'success'
            )
        else:
            flash(
                f'{n} patrón(es) guardado(s) como pendiente(s) '
                f'(no se encontraron modelos existentes con esos nombres).',
                'warning'
            )

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
