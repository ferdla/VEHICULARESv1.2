# =============================================================================
# services/cotizacion.py
# Lógica de negocio del cotizador:
#   - calcular_prima_empresa()   → tasa + prima para una empresa
#   - calcular_cotizacion()      → cotización completa para las 4 empresas
#
# CATEGORÍAS DE VEHÍCULO:
#   - PICKUP      → bypass clasificador, usa tipo_riesgo con código 'PK'
#   - CHINO_HINDU → bypass clasificador, usa tipo_riesgo con código 'CH-H'
#   - SEDAN       → usa clasificador normal
#   - SUV         → usa clasificador normal
# =============================================================================

import datetime
from services.clasificacion import clasificar_vehiculo
from models.tasa import get_tasa, get_tasa_fallback
from models.empresa import get_empresas_activas
from models.vehiculo import get_modelo_by_id

AÑO_ACTUAL = datetime.date.today().year

# Mapa de categoría → código(s) interno(s) de tipo_riesgo
# Para PICKUP: busca PK primero, si no existe usa CH-H-PK como fallback
CATEGORIA_CODIGO = {
    'PICKUP':       ['PK', 'CH-H-PK'],   # fallback en orden
    'CHINO_HINDU':  ['CH-H'],
}


def _get_tipo_riesgo_directo(cur, id_empresa, codigos):
    """
    Busca el id_tipo_riesgo y nombre para una empresa probando los códigos
    en orden (el primero que encuentre activo en empresa_tipo_riesgo).
    Retorna (id_tipo_riesgo, nombre_riesgo) o (None, None) si ninguno existe.
    """
    for codigo in codigos:
        cur.execute("""
            SELECT tr.id_tipo_riesgo, tr.nombre_riesgo
            FROM tipo_riesgo tr
            JOIN empresa_tipo_riesgo etr ON tr.id_tipo_riesgo = etr.id_tipo_riesgo
            WHERE etr.id_empresa = %s
              AND tr.codigo_interno = %s
              AND etr.activo = 1
            LIMIT 1
        """, (id_empresa, codigo))
        row = cur.fetchone()
        if row:
            return row[0], row[1]
    return None, None


def calcular_prima_empresa(cur, id_empresa, id_modelo, anio_fabricacion,
                           suma_asegurada, categoria=None):
    """
    Clasifica el vehículo para una empresa y calcula su prima.

    Si categoria es PICKUP o CHINO_HINDU, bypass el clasificador y
    usa directamente el tipo de riesgo correspondiente.

    Retorna dict con:
        id_empresa, asegurable,
        tipo_riesgo, id_tipo_riesgo,
        tasa, prima, detalle
    """
    tasa  = None
    prima = None

    # ── BYPASS: Pickup o Chino-Hindu ─────────────────────────────────────────
    if categoria in CATEGORIA_CODIGO:
        codigos = CATEGORIA_CODIGO[categoria]
        id_tipo_riesgo, nombre_riesgo = _get_tipo_riesgo_directo(cur, id_empresa, codigos)

        if id_tipo_riesgo is None:
            # Esta empresa no tiene ese tipo de riesgo asignado
            return {
                'id_empresa':     id_empresa,
                'asegurable':     False,
                'tipo_riesgo':    'No Asegurable',
                'id_tipo_riesgo': None,
                'tasa':           None,
                'prima':          None,
                'detalle':        f'Esta empresa no tiene tipo de riesgo {codigos[0]} asignado.',
            }

        es_0km = 1 if anio_fabricacion >= AÑO_ACTUAL else 0
        tasa = get_tasa(cur, id_empresa, id_tipo_riesgo, anio_fabricacion, es_0km)

        if tasa is None and es_0km:
            tasa = get_tasa_fallback(cur, id_empresa, id_tipo_riesgo, anio_fabricacion)

        if tasa is not None:
            prima = round(suma_asegurada * tasa / 100, 2)

        return {
            'id_empresa':     id_empresa,
            'asegurable':     True,
            'tipo_riesgo':    nombre_riesgo,
            'id_tipo_riesgo': id_tipo_riesgo,
            'tasa':           tasa,
            'prima':          prima,
            'detalle':        f'Categoría {categoria} — tipo de riesgo directo.',
        }

    # ── CLASIFICADOR NORMAL: Sedan / SUV / None ───────────────────────────────
    clasificacion = clasificar_vehiculo(cur, id_empresa, id_modelo, anio_fabricacion)

    if clasificacion['asegurable']:
        es_0km = 1 if anio_fabricacion >= AÑO_ACTUAL else 0

        tasa = get_tasa(cur, id_empresa, clasificacion['id_tipo_riesgo'],
                        anio_fabricacion, es_0km)

        if tasa is None and es_0km:
            tasa = get_tasa_fallback(cur, id_empresa,
                                     clasificacion['id_tipo_riesgo'],
                                     anio_fabricacion)

        if tasa is not None:
            prima = round(suma_asegurada * tasa / 100, 2)

    return {
        'id_empresa':     id_empresa,
        'asegurable':     clasificacion['asegurable'],
        'tipo_riesgo':    clasificacion['tipo_riesgo'],
        'id_tipo_riesgo': clasificacion['id_tipo_riesgo'],
        'tasa':           tasa,
        'prima':          prima,
        'detalle':        clasificacion['detalle'],
    }


def calcular_cotizacion(cur, id_modelo, anio_fabricacion, suma_asegurada,
                        categoria=None):
    """
    Calcula la cotización completa para todas las empresas activas.

    Retorna dict con:
        modelo, marca, anio, suma_asegurada, categoria,
        alguna_asegurable,
        resultados: [lista de calcular_prima_empresa() con nombre_empresa]
    """
    info     = get_modelo_by_id(cur, id_modelo)
    empresas = get_empresas_activas(cur)

    resultados        = []
    alguna_asegurable = False

    for id_empresa, nombre_empresa in empresas:
        resultado = calcular_prima_empresa(
            cur, id_empresa, id_modelo, anio_fabricacion,
            suma_asegurada, categoria
        )
        resultado['empresa'] = nombre_empresa
        resultados.append(resultado)

        if resultado['asegurable']:
            alguna_asegurable = True

    return {
        'modelo':            info[2] if info else 'Desconocido',
        'marca':             info[3] if info else 'Desconocida',
        'anio':              anio_fabricacion,
        'suma_asegurada':    suma_asegurada,
        'categoria':         categoria,
        'alguna_asegurable': alguna_asegurable,
        'resultados':        resultados,
    }
