# =============================================================================
# services/clasificacion.py
# Lógica de clasificación de riesgo vehicular
#
# TABLAS USADAS:
#   regla_clasificacion   (antes: riesgo_vehiculo)
#   excepcion_confirmada  (antes: riesgo_modelo_excepcion)
#   excepcion_pendiente
#
# ORDEN DE PRIORIDAD:
#   1. Regla específica por modelo  (id_modelo IS NOT NULL)
#   2. Excepción confirmada         (excepcion_confirmada)
#   3. Excepción pendiente por nombre (excepcion_pendiente, resuelta=0)
#   4. Regla general de marca       (id_modelo IS NULL, sin excepciones)
#   5. Sin clasificación            → No Asegurable
# =============================================================================

NO_ASEGURABLE = {
    'asegurable':     False,
    'tipo_riesgo':    'No Asegurable',
    'id_tipo_riesgo': None,
    'detalle':        'El vehículo no tiene clasificación para esta empresa.',
}


def _año_en_rango(anio_fabricacion: int, anio_inicio, anio_fin) -> bool:
    if anio_inicio is not None and anio_fabricacion < anio_inicio:
        return False
    if anio_fin is not None and anio_fabricacion > anio_fin:
        return False
    return True


def clasificar_vehiculo(cur, id_empresa: int, id_modelo: int, anio_fabricacion: int) -> dict:
    """
    Determina el tipo de riesgo de un vehículo para una empresa específica.
    """
    # ── Obtener marca del modelo ───────────────────────────────────────────────
    cur.execute("""
        SELECT mo.id_marca, mo.nombre_modelo
        FROM modelo mo WHERE mo.id_modelo = %s
    """, (id_modelo,))
    row = cur.fetchone()
    if not row:
        return {**NO_ASEGURABLE, 'detalle': 'Modelo no encontrado en la base de datos.'}
    id_marca, nombre_modelo = row

    # ── PASO 1: Regla específica por modelo ───────────────────────────────────
    cur.execute("""
        SELECT rc.id_regla_clasificacion,
               rc.id_tipo_riesgo,
               tr.nombre_riesgo,
               rc.anio_inicio,
               rc.anio_fin,
               rc.nota_regla
        FROM regla_clasificacion rc
        JOIN tipo_riesgo tr ON rc.id_tipo_riesgo = tr.id_tipo_riesgo
        WHERE rc.id_empresa  = %s
          AND rc.id_marca    = %s
          AND rc.id_modelo   = %s
          AND rc.activo      = 1
        ORDER BY rc.id_regla_clasificacion DESC
    """, (id_empresa, id_marca, id_modelo))

    for id_rc, id_tr, nombre_tr, a_ini, a_fin, nota in cur.fetchall():
        if not _año_en_rango(anio_fabricacion, a_ini, a_fin):
            continue
        return {
            'asegurable':     True,
            'tipo_riesgo':    nombre_tr,
            'id_tipo_riesgo': id_tr,
            'detalle':        f'Regla específica por modelo. {nota or ""}',
        }

    # ── PASO 2 y 3: Regla general de marca + excepciones ─────────────────────
    cur.execute("""
        SELECT rc.id_regla_clasificacion,
               rc.id_tipo_riesgo,
               tr.nombre_riesgo,
               rc.anio_inicio,
               rc.anio_fin,
               rc.nota_regla
        FROM regla_clasificacion rc
        JOIN tipo_riesgo tr ON rc.id_tipo_riesgo = tr.id_tipo_riesgo
        WHERE rc.id_empresa   = %s
          AND rc.id_marca     = %s
          AND rc.id_modelo IS NULL
          AND rc.activo       = 1
        ORDER BY rc.id_regla_clasificacion DESC
    """, (id_empresa, id_marca))

    for id_rc, id_tr, nombre_tr, a_ini, a_fin, nota in cur.fetchall():
        if not _año_en_rango(anio_fabricacion, a_ini, a_fin):
            continue

        # ── PASO 2: Excepción confirmada ──────────────────────────────────
        cur.execute("""
            SELECT ec.tipo_excepcion,
                   ec.id_tipo_riesgo_alternativo,
                   tr2.nombre_riesgo,
                   ec.nota_excepcion
            FROM excepcion_confirmada ec
            LEFT JOIN tipo_riesgo tr2
                   ON ec.id_tipo_riesgo_alternativo = tr2.id_tipo_riesgo
            WHERE ec.id_regla_clasificacion = %s
              AND ec.id_modelo              = %s
        """, (id_rc, id_modelo))
        exc = cur.fetchone()

        if exc:
            tipo_exc, id_tr_alt, nombre_tr_alt, nota_exc = exc
            if tipo_exc == 'EXCLUIR':
                if id_tr_alt is not None:
                    return {
                        'asegurable':     True,
                        'tipo_riesgo':    nombre_tr_alt,
                        'id_tipo_riesgo': id_tr_alt,
                        'detalle':        f'Excluido de regla general → {nota_exc or nombre_tr_alt}',
                    }
                else:
                    return {
                        **NO_ASEGURABLE,
                        'detalle': f'Excluido de regla general sin cobertura alternativa. {nota_exc or ""}',
                    }
            elif tipo_exc == 'INCLUIR_SOLO':
                return {
                    'asegurable':     True,
                    'tipo_riesgo':    nombre_tr,
                    'id_tipo_riesgo': id_tr,
                    'detalle':        f'Incluido explícitamente. {nota_exc or ""}',
                }

        else:
            # ── PASO 3: Excepción pendiente por nombre ────────────────────
            cur.execute("""
                SELECT ep.tipo_excepcion,
                       ep.id_tipo_riesgo_alt,
                       COALESCE(tr3.nombre_riesgo, 'No Asegurable') AS nombre_alt,
                       ep.nota_excepcion
                FROM excepcion_pendiente ep
                LEFT JOIN tipo_riesgo tr3 ON ep.id_tipo_riesgo_alt = tr3.id_tipo_riesgo
                WHERE ep.id_regla_clasificacion = %s
                  AND ep.resuelta               = 0
                  AND %s LIKE CONCAT(ep.nombre_modelo_pendiente, '%%')
                LIMIT 1
            """, (id_rc, nombre_modelo))
            exc_p = cur.fetchone()

            if exc_p:
                tipo_exc_p, id_tr_alt_p, nombre_alt_p, nota_exc_p = exc_p
                if tipo_exc_p == 'EXCLUIR':
                    if id_tr_alt_p is not None:
                        return {
                            'asegurable':     True,
                            'tipo_riesgo':    nombre_alt_p,
                            'id_tipo_riesgo': id_tr_alt_p,
                            'detalle':        f'Excepción pendiente aplicada → {nombre_alt_p}. {nota_exc_p or ""}',
                        }
                    else:
                        return {
                            **NO_ASEGURABLE,
                            'detalle': f'Excepción pendiente: excluido sin cobertura. {nota_exc_p or ""}',
                        }
                elif tipo_exc_p == 'INCLUIR_SOLO':
                    return {
                        'asegurable':     True,
                        'tipo_riesgo':    nombre_tr,
                        'id_tipo_riesgo': id_tr,
                        'detalle':        f'Excepción pendiente: incluido. {nota_exc_p or ""}',
                    }

            # ── PASO 4: Verificar si la regla es lista blanca ─────────────
            cur.execute("""
                SELECT COUNT(*) FROM excepcion_confirmada
                WHERE id_regla_clasificacion = %s
                  AND tipo_excepcion         = 'INCLUIR_SOLO'
            """, (id_rc,))
            tiene_incluir_solo = cur.fetchone()[0] > 0

            if tiene_incluir_solo:
                return {
                    **NO_ASEGURABLE,
                    'detalle': 'El modelo no está en la lista de modelos incluidos.',
                }

            # Regla general aplica
            return {
                'asegurable':     True,
                'tipo_riesgo':    nombre_tr,
                'id_tipo_riesgo': id_tr,
                'detalle':        f'Aplica regla general de marca. {nota or ""}',
            }

    # ── PASO 5: Sin regla → No Asegurable ────────────────────────────────────
    return NO_ASEGURABLE