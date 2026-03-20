# =============================================================================
# controllers/carga.py
# Rutas: /carga
# =============================================================================

import io
import pandas as pd
from flask import Blueprint, render_template, request, jsonify
from database import get_cursor, commit, rollback
import models.vehiculo as vehiculo_model
import models.clasificacion as clasificacion_model
from services.pendientes import (
    aplicar_reglas_pendientes_de_marca,
    aplicar_excepciones_pendientes_de_modelo,
)

bp = Blueprint('carga', __name__)


@bp.route('/carga')
def carga():
    return render_template('carga.html')


# ==============================================================================
# API: PREVISUALIZAR EXCEL
# ==============================================================================

@bp.route('/carga/previsualizar', methods=['POST'])
def previsualizar():
    if 'archivo' not in request.files:
        return jsonify({'error': 'No se recibió ningún archivo'}), 400

    archivo = request.files['archivo']
    if not archivo.filename.endswith('.xlsx'):
        return jsonify({'error': 'El archivo debe ser .xlsx'}), 400

    modo = request.form.get('modo', 'marcas_modelos')

    try:
        df = _leer_excel(archivo)
        if isinstance(df, str):
            return jsonify({'error': df}), 400

        cur = get_cursor()
        resumen = _previsualizar_marcas_modelos(cur, df) if modo == 'marcas_modelos' \
                  else _previsualizar_valores(cur, df)
        cur.close()
        return jsonify({'ok': True, 'resumen': resumen})

    except Exception as e:
        return jsonify({'error': f'Error al leer el archivo: {str(e)}'}), 500


# ==============================================================================
# API: EJECUTAR CARGA
# ==============================================================================

@bp.route('/carga/ejecutar', methods=['POST'])
def ejecutar():
    if 'archivo' not in request.files:
        return jsonify({'error': 'No se recibió ningún archivo'}), 400

    archivo = request.files['archivo']
    modo    = request.form.get('modo', 'marcas_modelos')
    accion  = request.form.get('accion_duplicado', 'ignorar')

    try:
        df = _leer_excel(archivo)
        if isinstance(df, str):
            return jsonify({'error': df}), 400

        cur = get_cursor()
        resultado = _cargar_marcas_modelos(cur, df, accion) if modo == 'marcas_modelos' \
                    else _cargar_valores(cur, df, accion)
        commit()
        cur.close()
        return jsonify({'ok': True, 'resultado': resultado})

    except Exception as e:
        rollback()
        return jsonify({'error': f'Error durante la carga: {str(e)}'}), 500


# ==============================================================================
# HELPERS — LECTURA Y VALIDACIÓN EXCEL
# ==============================================================================

def _leer_excel(archivo):
    try:
        contenido = archivo.read()
        df = pd.read_excel(io.BytesIO(contenido))
    except Exception as e:
        return f'No se pudo leer el archivo Excel: {e}'

    df.columns = [str(c).strip() for c in df.columns]

    if 'Marca' not in df.columns:
        return 'El archivo no tiene la columna "Marca"'
    if 'Modelo' not in df.columns:
        return 'El archivo no tiene la columna "Modelo"'

    df = df.dropna(subset=['Marca', 'Modelo'])
    df['Marca']  = df['Marca'].astype(str).str.strip()
    df['Modelo'] = df['Modelo'].astype(str).str.strip()

    vrn_col = next((c for c in df.columns if 'VRN' in c.upper() or 'OKM' in c.upper()), None)
    df.attrs['vrn_col'] = vrn_col

    year_cols = [c for c in df.columns if c.isdigit() and 2000 <= int(c) <= 2030]
    df.attrs['year_cols'] = year_cols

    return df


# ==============================================================================
# HELPERS — MARCAS Y MODELOS
# ==============================================================================

def _previsualizar_marcas_modelos(cur, df):
    marcas_nuevas      = []
    modelos_nuevos     = []
    modelos_existentes = []
    marcas_vistas      = {}

    for _, row in df.iterrows():
        nombre_marca  = row['Marca']
        nombre_modelo = row['Modelo']

        if nombre_marca not in marcas_vistas:
            r = vehiculo_model.get_marca_by_nombre(cur, nombre_marca)
            marcas_vistas[nombre_marca] = r[0] if r else None
            if not r:
                marcas_nuevas.append(nombre_marca)

        id_marca = marcas_vistas[nombre_marca]
        if id_marca:
            if vehiculo_model.get_modelo_by_marca_nombre(cur, id_marca, nombre_modelo):
                modelos_existentes.append(f"{nombre_marca} — {nombre_modelo}")
            else:
                modelos_nuevos.append(f"{nombre_marca} — {nombre_modelo}")
        else:
            modelos_nuevos.append(f"{nombre_marca} — {nombre_modelo}")

    reglas_a_resolver = sum(
        clasificacion_model.count_reglas_pendientes_por_marca(cur, nm)
        for nm in marcas_nuevas
    )

    exc_a_resolver = 0
    for item in modelos_nuevos:
        if ' — ' in item:
            nm, mod = item.split(' — ', 1)
            cur.execute("""
                SELECT COUNT(*) FROM excepcion_pendiente ep
                JOIN regla_clasificacion rc ON ep.id_regla_clasificacion = rc.id_regla_clasificacion
                JOIN marca ma ON rc.id_marca = ma.id_marca
                WHERE ma.nombre_marca = %s AND ep.resuelta = 0
                  AND %s LIKE CONCAT(ep.nombre_modelo_pendiente, '%%')
            """, (nm, mod))
            exc_a_resolver += cur.fetchone()[0]

    return {
        'total_filas':                  len(df),
        'marcas_nuevas':                len(marcas_nuevas),
        'marcas_nuevas_lista':          marcas_nuevas[:20],
        'modelos_nuevos':               len(modelos_nuevos),
        'modelos_existentes':           len(modelos_existentes),
        'modelos_exist_lista':          modelos_existentes[:10],
        'reglas_pendientes_a_resolver': reglas_a_resolver,
        'exc_pendientes_a_resolver':    exc_a_resolver,
    }


def _cargar_marcas_modelos(cur, df, accion):
    marcas_cache      = {}
    insertadas_marcas = 0
    insertados_mod    = 0
    actualizados_mod  = 0
    ignorados_mod     = 0
    reglas_aplicadas  = 0
    exc_aplicadas     = 0
    errores           = []

    for _, row in df.iterrows():
        nombre_marca  = row['Marca']
        nombre_modelo = row['Modelo']

        try:
            # ── Resolver marca ────────────────────────────────────────────
            if nombre_marca not in marcas_cache:
                r = vehiculo_model.get_marca_by_nombre(cur, nombre_marca)
                if r:
                    marcas_cache[nombre_marca] = r[0]
                else:
                    vehiculo_model.insert_marca(cur, nombre_marca)
                    commit()
                    nuevo_id = vehiculo_model.get_last_insert_id(cur)
                    marcas_cache[nombre_marca] = nuevo_id
                    insertadas_marcas += 1
                    # Aplicar reglas pendientes automáticamente
                    reglas_aplicadas += aplicar_reglas_pendientes_de_marca(
                        cur, nombre_marca, nuevo_id, commit
                    )

            id_marca = marcas_cache[nombre_marca]

            # ── Resolver modelo ───────────────────────────────────────────
            existe = vehiculo_model.get_modelo_by_marca_nombre(cur, id_marca, nombre_modelo)

            if existe:
                if accion == 'actualizar':
                    vehiculo_model.update_modelo(cur, existe[0], id_marca, nombre_modelo, None)
                    actualizados_mod += 1
                else:
                    ignorados_mod += 1
            else:
                vehiculo_model.insert_modelo(cur, id_marca, nombre_modelo, None)
                commit()
                nuevo_id_modelo = vehiculo_model.get_last_insert_id(cur)
                insertados_mod += 1
                # Aplicar excepciones pendientes automáticamente
                exc_aplicadas += aplicar_excepciones_pendientes_de_modelo(
                    cur, id_marca, nombre_modelo, nuevo_id_modelo, commit
                )

        except Exception as e:
            errores.append(f"{nombre_marca} — {nombre_modelo}: {str(e)}")

    commit()
    return {
        'marcas_insertadas':               insertadas_marcas,
        'modelos_insertados':              insertados_mod,
        'modelos_actualizados':            actualizados_mod,
        'modelos_ignorados':               ignorados_mod,
        'reglas_pendientes_aplicadas':     reglas_aplicadas,
        'exc_pendientes_aplicadas':        exc_aplicadas,
        'errores':                         errores[:20],
        'total_errores':                   len(errores),
    }


# ==============================================================================
# HELPERS — VALORES VEHICULARES
# ==============================================================================

def _previsualizar_valores(cur, df):
    vrn_col   = df.attrs.get('vrn_col')
    year_cols = df.attrs.get('year_cols', [])

    if not vrn_col:
        return {'error': 'No se encontró columna VRN en el archivo'}

    total_vrn         = 0
    total_historicos  = 0
    modelos_sin_match = []
    modelos_con_match = 0

    for _, row in df.iterrows():
        nombre_marca  = row['Marca']
        nombre_modelo = row['Modelo']
        marca = vehiculo_model.get_marca_by_nombre(cur, nombre_marca)
        if not marca:
            modelos_sin_match.append(f"{nombre_marca} — {nombre_modelo}")
            continue

        modelo = vehiculo_model.get_modelo_by_marca_nombre(cur, marca[0], nombre_modelo)
        if not modelo:
            modelos_sin_match.append(f"{nombre_marca} — {nombre_modelo}")
            continue

        modelos_con_match += 1
        if pd.notna(row.get(vrn_col)) and row.get(vrn_col) > 0:
            total_vrn += 1
        for y in year_cols:
            val = row.get(y)
            if pd.notna(val) and val > 0:
                total_historicos += 1

    return {
        'vrn_col':               vrn_col,
        'años_detectados':       year_cols,
        'modelos_con_match':     modelos_con_match,
        'modelos_sin_match':     len(modelos_sin_match),
        'sin_match_lista':       modelos_sin_match[:15],
        'vrn_a_insertar':        total_vrn,
        'historicos_a_insertar': total_historicos,
        'total_registros':       total_vrn + total_historicos,
    }


def _cargar_valores(cur, df, accion):
    vrn_col   = df.attrs.get('vrn_col')
    year_cols = df.attrs.get('year_cols', [])

    if not vrn_col:
        return {'error': 'No se encontró columna VRN'}

    insertados   = 0
    actualizados = 0
    ignorados    = 0
    sin_modelo   = 0
    errores      = []

    for _, row in df.iterrows():
        nombre_marca  = row['Marca']
        nombre_modelo = row['Modelo']

        marca = vehiculo_model.get_marca_by_nombre(cur, nombre_marca)
        if not marca:
            sin_modelo += 1
            continue
        modelo = vehiculo_model.get_modelo_by_marca_nombre(cur, marca[0], nombre_modelo)
        if not modelo:
            sin_modelo += 1
            continue

        id_modelo = modelo[0]

        try:
            vrn = row.get(vrn_col)
            if pd.notna(vrn) and vrn > 0:
                ins, act, ign = _upsert_valor(cur, id_modelo, None, vrn, 'VRN', accion)
                insertados += ins; actualizados += act; ignorados += ign

            for y in year_cols:
                val = row.get(str(y)) if str(y) in df.columns else row.get(y)
                if pd.notna(val) and val > 0:
                    ins, act, ign = _upsert_valor(cur, id_modelo, int(y), val, 'HISTORICO', accion)
                    insertados += ins; actualizados += act; ignorados += ign

        except Exception as e:
            errores.append(f"{nombre_marca} — {nombre_modelo}: {str(e)}")

    commit()
    return {
        'insertados':    insertados,
        'actualizados':  actualizados,
        'ignorados':     ignorados,
        'sin_modelo':    sin_modelo,
        'errores':       errores[:20],
        'total_errores': len(errores),
    }


def _upsert_valor(cur, id_modelo, anio, valor, tipo_valor, accion):
    existe = vehiculo_model.get_valor_by_anio_tipo(cur, id_modelo, anio, tipo_valor)
    if existe:
        if accion == 'actualizar':
            vehiculo_model.update_valor_vehiculo(cur, existe[0], valor)
            return 0, 1, 0
        return 0, 0, 1
    else:
        vehiculo_model.insert_valor_vehiculo(cur, id_modelo, anio, valor, tipo_valor)
        return 1, 0, 0
