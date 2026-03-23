# =============================================================================
# services/depreciacion.py
# Lógica de cálculo de valor estimado de vehículo con depreciación.
#
# REGLA DE NEGOCIO:
#   1. Si existe valor histórico exacto para el año → usar ese
#   2. Si no, pero hay VRN → calcular: VRN × FACTOR_DEPRECIACION ^ años_uso
#   3. Si no hay VRN → sin datos, el usuario debe ingresar manualmente
# =============================================================================

import datetime
from models.vehiculo import get_vrn, get_valor_historico

FACTOR_DEPRECIACION = 0.90
AÑO_ACTUAL = datetime.date.today().year  # ← dinámico, ya no hardcodeado


def calcular_valor_vehiculo(cur, id_modelo, anio_fabricacion):
    """
    Calcula el valor estimado de un vehículo.

    Retorna un dict con:
        valor  : float | None
        vrn    : float | None
        fuente : 'historico' | 'calculado' | 'sin_datos'
        nota   : str con descripción del cálculo
    """
    vrn = get_vrn(cur, id_modelo)

    if not vrn:
        return {
            'valor':  None,
            'vrn':    None,
            'fuente': 'sin_datos',
            'nota':   'No hay valor de referencia para este modelo. Ingresa el valor manualmente.'
        }

    # Buscar valor histórico exacto
    valor_historico = get_valor_historico(cur, id_modelo, anio_fabricacion)
    if valor_historico:
        return {
            'valor':  valor_historico,
            'vrn':    vrn,
            'fuente': 'historico',
            'nota':   f'Valor de referencia del año {anio_fabricacion}'
        }

    # Calcular por depreciación
    años_uso = AÑO_ACTUAL - anio_fabricacion
    if años_uso <= 0:
        valor_calculado = vrn
        nota = 'Vehículo 0km — valor de lista'
    else:
        valor_calculado = round(vrn * (FACTOR_DEPRECIACION ** años_uso), 2)
        nota = f'Calculado: VRN ${vrn:,.0f} × {FACTOR_DEPRECIACION}^{años_uso} años'

    return {
        'valor':  valor_calculado,
        'vrn':    vrn,
        'fuente': 'calculado',
        'nota':   nota
    }