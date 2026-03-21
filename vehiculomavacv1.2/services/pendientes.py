# =============================================================================
# services/pendientes.py
# Lógica unificada para resolver reglas y excepciones pendientes.
#
# Antes esta lógica estaba DUPLICADA en:
#   routes/carga.py     → _aplicar_reglas_pendientes(), _aplicar_excepciones_pendientes()
#   routes/vehiculos.py → resolver_regla_pendiente(), resolver_pendiente()
#
# Ahora ambos controllers usan estas mismas funciones.
#
# DIFERENCIA entre los dos modos de uso:
#   - Manual (vehiculos):  el usuario confirma cada pendiente en un modal
#   - Masivo (carga):      se aplican todos automáticamente sin modal
# =============================================================================

from database import get_last_insert_id  # ← centralizado en database.py
from models.clasificacion import (
    get_regla_pendiente_by_id,
    get_reglas_pendientes_por_marca,
    marcar_regla_pendiente_resuelta,
    get_excepcion_pendiente_by_id,
    get_excepciones_pendientes_masivo,
    marcar_excepcion_pendiente_resuelta,
    insert_excepcion_pendiente_ignore,
    upsert_excepcion_confirmada,
    insert_regla,
)
from models.vehiculo import get_modelo_by_marca_nombre


# ==============================================================================
# MODO MANUAL — el usuario confirma/ignora en el modal (vehiculos.py)
# ==============================================================================

def resolver_regla_pendiente(cur, id_pendiente, id_marca, confirmar, commit_fn):
    """
    Aplica o ignora una regla pendiente individual.
    Llamado desde controllers/vehiculos.py tras la confirmación del usuario.

    Retorna dict {'success': bool, 'mensaje': str, 'error': str|None}
    """
    if confirmar:
        pend = get_regla_pendiente_by_id(cur, id_pendiente)
        if not pend:
            return {'success': False, 'error': 'Regla pendiente no encontrada', 'mensaje': None}

        id_emp, id_tr, nom_mod, a_ini, a_fin, s_min, s_max, nota = pend

        # Intentar resolver el id_modelo si el modelo ya existe
        id_modelo_final = None
        if nom_mod:
            mod_row = get_modelo_by_marca_nombre(cur, id_marca, nom_mod)
            if mod_row:
                id_modelo_final = mod_row[0]

        insert_regla(cur, id_emp, id_tr, id_marca, id_modelo_final,
                     a_ini, a_fin, s_min, s_max, nota)
        commit_fn()

        # Si había modelo específico pero aún no existe → excepcion_pendiente
        if nom_mod and id_modelo_final is None:
            id_rc = get_last_insert_id(cur)  # ← ID de regla_clasificacion recién insertada
            insert_excepcion_pendiente_ignore(
                cur, id_rc, nom_mod, 'INCLUIR_SOLO', None,
                f'Modelo pendiente: {nom_mod}'
            )
            commit_fn()

    marcar_regla_pendiente_resuelta(cur, id_pendiente)
    commit_fn()

    return {
        'success': True,
        'mensaje': 'Regla aplicada correctamente' if confirmar else 'Regla ignorada',
        'error':   None,
    }


def resolver_excepcion_pendiente(cur, id_pendiente, id_modelo, confirmar, commit_fn):
    """
    Aplica o ignora una excepción pendiente individual.
    Llamado desde controllers/vehiculos.py tras la confirmación del usuario.

    Retorna dict {'success': bool, 'mensaje': str, 'error': str|None}
    """
    if confirmar:
        pend = get_excepcion_pendiente_by_id(cur, id_pendiente)
        if not pend:
            return {'success': False, 'error': 'Excepción no encontrada o ya resuelta', 'mensaje': None}

        id_rc, tipo_exc, id_tipo_alt, nota = pend
        upsert_excepcion_confirmada(cur, id_rc, id_modelo, tipo_exc, id_tipo_alt, nota)

    marcar_excepcion_pendiente_resuelta(cur, id_pendiente)
    commit_fn()

    return {
        'success': True,
        'mensaje': 'Excepción aplicada' if confirmar else 'Excepción ignorada',
        'error':   None,
    }


# ==============================================================================
# MODO MASIVO — aplica automáticamente sin modal (carga.py)
# ==============================================================================

def aplicar_reglas_pendientes_de_marca(cur, nombre_marca, id_marca, commit_fn):
    """
    Busca en regla_pendiente las reglas que esperaban esta marca
    y las aplica automáticamente.

    Retorna el número de reglas aplicadas.
    """
    pendientes = get_reglas_pendientes_por_marca(cur, nombre_marca)
    aplicadas = 0

    for pend in pendientes:
        id_pend, id_emp, _, id_tr, _, nom_mod, a_ini, a_fin, s_min, s_max, nota = pend

        id_modelo_final = None
        if nom_mod:
            mod_row = get_modelo_by_marca_nombre(cur, id_marca, nom_mod)
            if mod_row:
                id_modelo_final = mod_row[0]

        try:
            insert_regla(cur, id_emp, id_tr, id_marca, id_modelo_final,
                         a_ini, a_fin, s_min, s_max, nota)
            commit_fn()

            if nom_mod and id_modelo_final is None:
                id_rc = get_last_insert_id(cur)  # ← ID de regla_clasificacion recién insertada
                insert_excepcion_pendiente_ignore(
                    cur, id_rc, nom_mod, 'INCLUIR_SOLO', None,
                    f'Modelo pendiente: {nom_mod}'
                )
                commit_fn()

            marcar_regla_pendiente_resuelta(cur, id_pend)
            commit_fn()
            aplicadas += 1
        except Exception:
            pass  # Si falla una regla individual, continuar con las demás

    return aplicadas


def aplicar_excepciones_pendientes_de_modelo(cur, id_marca, nombre_modelo, id_modelo, commit_fn):
    """
    Busca en excepcion_pendiente las excepciones que esperaban este modelo
    y las aplica automáticamente.

    Retorna el número de excepciones aplicadas.
    """
    pendientes = get_excepciones_pendientes_masivo(cur, id_marca, nombre_modelo)
    aplicadas = 0

    for pend in pendientes:
        id_pend, id_rc, tipo_exc, id_tipo_alt, nota = pend
        try:
            upsert_excepcion_confirmada(cur, id_rc, id_modelo, tipo_exc, id_tipo_alt, nota)
            marcar_excepcion_pendiente_resuelta(cur, id_pend)
            commit_fn()
            aplicadas += 1
        except Exception:
            pass

    return aplicadas
