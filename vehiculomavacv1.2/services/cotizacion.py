# =============================================================================
# services/cotizacion.py
# Lógica de negocio del cotizador:
#   - calcular_prima_empresa()   → tasa + prima para una empresa
#   - calcular_cotizacion()      → cotización completa para las 4 empresas
#
# Usa:
#   services/clasificacion.py   → clasificar_vehiculo()
#   models/tasa.py              → get_tasa(), get_tasa_fallback()
#   models/empresa.py           → get_empresas_activas()
#   models/vehiculo.py          → get_modelo_by_id()
# =============================================================================

from services.clasificacion import clasificar_vehiculo
from models.tasa import get_tasa, get_tasa_fallback
from models.empresa import get_empresas_activas
from models.vehiculo import get_modelo_by_id

AÑO_ACTUAL = 2026


def calcular_prima_empresa(cur, id_empresa, id_modelo, anio_fabricacion, suma_asegurada):
    """
    Clasifica el vehículo para una empresa y calcula su prima.

    Retorna dict con:
        empresa, id_empresa, asegurable,
        tipo_riesgo, id_tipo_riesgo,
        tasa, prima, detalle
    """
    clasificacion = clasificar_vehiculo(cur, id_empresa, id_modelo, anio_fabricacion)

    tasa  = None
    prima = None

    if clasificacion['asegurable']:
        es_0km = 1 if anio_fabricacion >= AÑO_ACTUAL else 0

        tasa = get_tasa(cur, id_empresa, clasificacion['id_tipo_riesgo'],
                        anio_fabricacion, es_0km)

        # Fallback: si es 0km pero no hay tasa 0km, usar la tasa normal
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


def calcular_cotizacion(cur, id_modelo, anio_fabricacion, suma_asegurada):
    """
    Calcula la cotización completa para todas las empresas activas.

    Retorna dict con:
        modelo, marca, anio, suma_asegurada,
        alguna_asegurable,
        resultados: [lista de calcular_prima_empresa() con nombre_empresa]
    """
    info = get_modelo_by_id(cur, id_modelo)
    empresas = get_empresas_activas(cur)

    resultados = []
    alguna_asegurable = False

    for id_empresa, nombre_empresa in empresas:
        resultado = calcular_prima_empresa(
            cur, id_empresa, id_modelo, anio_fabricacion, suma_asegurada
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
        'alguna_asegurable': alguna_asegurable,
        'resultados':        resultados,
    }
