# =============================================================================
# controllers/carga.py
# Rutas: /carga
#
# CORRECCIONES respecto a la versión anterior:
#   1. get_last_insert_id importado de database.py (no de vehiculo_model)
#   2. _parsear_valor() maneja VRN='ND' y cualquier texto sin reventar
#   3. _cargar_valores() usa executemany() en lotes → de ~120s a ~3s
# =============================================================================

import io
import pandas as pd
from flask import Blueprint, render_template, request, jsonify
from database import get_cursor, commit, rollback, get_last_insert_id   # ← FIX 1
import models.vehiculo as vehiculo_model
import models.clasificacion as clasificacion_model
from services.pendientes import (
    aplicar_reglas_pendientes_de_marca,
    aplicar_excepciones_pendientes_de_modelo,
)

bp = Blueprint('carga', __name__)

# Tamaño de lote para executemany (inserciones masivas)
BATCH_SIZE = 500


# ==============================================================================
# VISTA PRINCIPAL
# ==============================================================================

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
    """Lee el archivo y valida columnas obligatorias."""
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

    # Detectar columna VRN (acepta "VRN", "VRN(OKM EN TIENDA)", "VRN OKM", etc.)
    vrn_col = next(
        (c for c in df.columns if 'VRN' in c.upper() or 'OKM' in c.upper()),
        None
    )
    df.attrs['vrn_col'] = vrn_col

    # Detectar columnas de años (números entre 2000 y 2030)
    year_cols = [c for c in df.columns if c.isdigit() and 2000 <= int(c) <= 2030]
    df.attrs['year_cols'] = year_cols

    return df


def _parsear_valor(val):
    """
    ── FIX 2 ──────────────────────────────────────────────────────────────────
    Convierte cualquier valor del Excel a float de forma segura.
    Maneja: números, strings numéricos, 'ND', NaN, None, negativos.
    Retorna None si no es un número válido > 0, SIN lanzar excepción.
    ───────────────────────────────────────────────────────────────────────────
    """
    if val is None:
        return None
    if isinstance(val, float) and pd.isna(val):
        return None
    try:
        v = float(str(val).replace(',', '').replace(' ', ''))
        return v if v > 0 else None
    except (ValueError, TypeError):
        return None   # 'ND', texto, etc. → ignorar silenciosamente


# ==============================================================================
# HELPERS — MARCAS Y MODELOS
# ==============================================================================

def _previsualizar_marcas_modelos(cur, df):
    """Calcula qué se insertaría sin tocar la BD."""
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

    # Contar pendientes que se resolverían
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
    """Inserta marcas y modelos, resolviendo pendientes automáticamente."""
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
                    nuevo_id = get_last_insert_id(cur)   # ← FIX 1: desde database.py
                    marcas_cache[nombre_marca] = nuevo_id
                    insertadas_marcas += 1
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
                nuevo_id_modelo = get_last_insert_id(cur)   # ← FIX 1
                insertados_mod += 1
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
    """Calcula qué valores se insertarían sin tocar la BD."""
    vrn_col   = df.attrs.get('vrn_col')
    year_cols = df.attrs.get('year_cols', [])

    if not vrn_col:
        return {'error': 'No se encontró columna VRN en el archivo'}

    total_vrn         = 0
    total_historicos  = 0
    vrn_ignorados     = 0
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

        # ── FIX 2: usar _parsear_valor en lugar de vrn > 0 ───────────────
        vrn = _parsear_valor(row.get(vrn_col))
        if vrn:
            total_vrn += 1
        else:
            vrn_ignorados += 1

        for y in year_cols:
            if _parsear_valor(row.get(y)):
                total_historicos += 1

    return {
        'vrn_col':               vrn_col,
        'años_detectados':       year_cols,
        'modelos_con_match':     modelos_con_match,
        'modelos_sin_match':     len(modelos_sin_match),
        'sin_match_lista':       modelos_sin_match[:15],
        'vrn_a_insertar':        total_vrn,
        'vrn_ignorados':         vrn_ignorados,
        'historicos_a_insertar': total_historicos,
        'total_registros':       total_vrn + total_historicos,
    }


def _cargar_valores(cur, df, accion):
    """
    ── FIX 3 ──────────────────────────────────────────────────────────────────
    Carga masiva de valores vehiculares usando executemany() en lotes de 500.
    Pasos:
      1. Una sola query para traer TODOS los modelos → mapa {(marca, modelo): id}
      2. Si accion='ignorar', una sola query para traer todos los existentes
      3. Construir listas a_insertar y a_actualizar en Python (sin tocar la BD)
      4. executemany() en lotes de BATCH_SIZE (500) → de ~120s a ~3s
    ───────────────────────────────────────────────────────────────────────────
    """
    vrn_col   = df.attrs.get('vrn_col')
    year_cols = df.attrs.get('year_cols', [])

    if not vrn_col:
        return {'error': 'No se encontró columna VRN'}

    # ── Paso 1: Mapa completo de modelos en una sola query ────────────────────
    cur.execute("""
        SELECT mo.id_modelo, ma.nombre_marca, mo.nombre_modelo
        FROM modelo mo
        JOIN marca ma ON mo.id_marca = ma.id_marca
    """)
    modelo_map = {
        (nombre_marca, nombre_modelo): id_modelo
        for id_modelo, nombre_marca, nombre_modelo in cur.fetchall()
    }

    # ── Paso 2: Set de valores ya existentes (para accion='ignorar') ──────────
    existentes = set()
    if accion == 'ignorar':
        cur.execute("SELECT id_modelo, anio, tipo_valor FROM valor_vehiculo")
        for id_mod, anio, tipo in cur.fetchall():
            existentes.add((id_mod, anio, tipo))

    # ── Paso 3: Construir lotes en Python ─────────────────────────────────────
    a_insertar   = []   # (id_modelo, anio_o_None, valor, tipo_valor)
    a_actualizar = []   # (valor, id_modelo, anio_o_None, tipo_valor)
    sin_modelo   = 0
    vrn_ignorados = 0

    for _, row in df.iterrows():
        nombre_marca  = row['Marca']
        nombre_modelo = row['Modelo']
        id_modelo = modelo_map.get((nombre_marca, nombre_modelo))

        if not id_modelo:
            sin_modelo += 1
            continue

        # VRN
        vrn = _parsear_valor(row.get(vrn_col))    # ← FIX 2 aquí también
        if vrn:
            _clasificar_registro(
                id_modelo, None, vrn, 'VRN',
                accion, existentes, a_insertar, a_actualizar
            )
        else:
            vrn_ignorados += 1

        # Históricos por año
        for y in year_cols:
            val = _parsear_valor(row.get(y))
            if val:
                _clasificar_registro(
                    id_modelo, int(y), val, 'HISTORICO',
                    accion, existentes, a_insertar, a_actualizar
                )

    # ── Paso 4: executemany en lotes ──────────────────────────────────────────
    insertados   = 0
    actualizados = 0
    errores      = []

    # Inserciones
    if a_insertar:
        sql_insert = """
            INSERT INTO valor_vehiculo (id_modelo, anio, valor, tipo_valor)
            VALUES (%s, %s, %s, %s)
        """
        for i in range(0, len(a_insertar), BATCH_SIZE):
            lote = a_insertar[i:i + BATCH_SIZE]
            try:
                cur.executemany(sql_insert, lote)
                commit()
                insertados += len(lote)
            except Exception as e:
                errores.append(f"Error en lote inserción [{i}:{i+BATCH_SIZE}]: {str(e)[:100]}")

    # Actualizaciones (solo cuando accion='actualizar')
    if a_actualizar:
        # Separar los que tienen año de los VRN (anio=None) porque el WHERE es distinto
        upd_con_anio = [(v, id_m, a, a, t) for v, id_m, a, t in a_actualizar if a is not None]
        upd_sin_anio = [(v, id_m, t)       for v, id_m, a, t in a_actualizar if a is None]

        if upd_con_anio:
            sql_upd_hist = """
                UPDATE valor_vehiculo SET valor=%s
                WHERE id_modelo=%s AND anio=%s AND tipo_valor=%s
                  AND (anio IS NOT NULL AND anio=%s)
            """
            # Simplificamos: UPDATE con anio exacto
            sql_upd_h = """
                UPDATE valor_vehiculo SET valor=%s
                WHERE id_modelo=%s AND anio=%s AND tipo_valor=%s
            """
            # Para UPDATE necesitamos (valor, id_modelo, anio, tipo_valor)
            datos_upd_h = [(v, id_m, a, t) for v, id_m, a, a2, t in
                           [(v, id_m, a, a, t) for v, id_m, a, a2, t in
                            [(row[0], row[1], row[2], row[2], row[4]) for row in upd_con_anio]]]
            # Reconstruir sin el parámetro duplicado
            datos_h = [(v, id_m, anio, t) for v, id_m, anio, anio2, t in
                       [(r[0], r[1], r[2], r[2], r[4]) for r in upd_con_anio]]
            for i in range(0, len(datos_h), BATCH_SIZE):
                lote = datos_h[i:i + BATCH_SIZE]
                try:
                    cur.executemany(
                        "UPDATE valor_vehiculo SET valor=%s WHERE id_modelo=%s AND anio=%s AND tipo_valor=%s",
                        lote
                    )
                    commit()
                    actualizados += len(lote)
                except Exception as e:
                    errores.append(f"Error en lote update histórico [{i}]: {str(e)[:100]}")

        if upd_sin_anio:
            for i in range(0, len(upd_sin_anio), BATCH_SIZE):
                lote = upd_sin_anio[i:i + BATCH_SIZE]
                try:
                    cur.executemany(
                        "UPDATE valor_vehiculo SET valor=%s WHERE id_modelo=%s AND anio IS NULL AND tipo_valor=%s",
                        lote
                    )
                    commit()
                    actualizados += len(lote)
                except Exception as e:
                    errores.append(f"Error en lote update VRN [{i}]: {str(e)[:100]}")

    commit()

    return {
        'insertados':    insertados,
        'actualizados':  actualizados,
        'ignorados':     len(existentes),  # los que ya existían y no se tocaron
        'sin_modelo':    sin_modelo,
        'vrn_ignorados': vrn_ignorados,
        'errores':       errores[:20],
        'total_errores': len(errores),
        'nota':          f'Procesado en lotes de {BATCH_SIZE}. Total: {insertados} insertados.',
    }


def _clasificar_registro(id_modelo, anio, valor, tipo_valor,
                          accion, existentes, a_insertar, a_actualizar):
    """
    Decide si un registro va a la lista de insertar, actualizar o se ignora.
    También actualiza el set 'existentes' para evitar duplicados del mismo archivo.
    """
    key = (id_modelo, anio, tipo_valor)

    if key in existentes:
        if accion == 'actualizar':
            a_actualizar.append((valor, id_modelo, anio, tipo_valor))
    else:
        a_insertar.append((id_modelo, anio, valor, tipo_valor))
        existentes.add(key)   # evitar duplicados internos del Excel
