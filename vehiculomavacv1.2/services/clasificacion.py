# =============================================================================
# services/clasificacion.py
# Lógica de clasificación de riesgo vehicular
#
# REGLAS DE PRIORIDAD (de mayor a menor):
#   1. Regla específica por modelo  (id_modelo IS NOT NULL)
#   2. Excepción sobre regla general (id_modelo IS NULL + excepción)
#   3. Regla general de marca       (id_modelo IS NULL, sin excepción)
#   4. Sin clasificación            → No Asegurable
#
# En cada nivel se valida que el año de fabricación esté dentro del rango
# definido en la regla (anio_inicio / anio_fin). Si hay rango y el año
# no entra, esa regla NO aplica.
# =============================================================================

NO_ASEGURABLE = {
    'asegurable':     False,
    'tipo_riesgo':    'No Asegurable',
    'id_tipo_riesgo': None,
    'detalle':        'El vehículo no tiene clasificación para esta empresa.',
}


def _año_en_rango(anio_fabricacion: int, anio_inicio, anio_fin) -> bool:
    """
    Valida que el año de fabricación esté dentro del rango de la regla.
    Si ambos campos son NULL, la regla aplica a cualquier año.
    Si solo uno tiene valor, se aplica como límite abierto en el otro extremo.
    """
    if anio_inicio is not None and anio_fabricacion < anio_inicio:
        return False
    if anio_fin is not None and anio_fabricacion > anio_fin:
        return False
    return True


def clasificar_vehiculo(cur, id_empresa: int, id_modelo: int, anio_fabricacion: int) -> dict:
    """
    Determina el tipo de riesgo de un vehículo para una empresa específica.

    Parámetros
    ----------
    cur              : cursor MySQL activo
    id_empresa       : ID de la empresa aseguradora
    id_modelo        : ID del modelo del vehículo
    anio_fabricacion : Año de fabricación del vehículo

    Retorna
    -------
    dict con claves:
        asegurable      (bool)
        tipo_riesgo     (str)   nombre del tipo de riesgo o 'No Asegurable'
        id_tipo_riesgo  (int|None)
        detalle         (str)   descripción de la regla que aplicó
    """

    # ------------------------------------------------------------------
    # Paso 1: Obtener la marca del modelo
    # ------------------------------------------------------------------
    cur.execute("SELECT id_marca FROM modelo WHERE id_modelo = %s", (id_modelo,))
    row = cur.fetchone()
    if not row:
        return {**NO_ASEGURABLE, 'detalle': 'Modelo no encontrado en la base de datos.'}

    id_marca = row[0]

    # ------------------------------------------------------------------
    # Paso 2: Buscar regla ESPECÍFICA para este modelo exacto
    #         (id_modelo IS NOT NULL, misma empresa y marca)
    # ------------------------------------------------------------------
    cur.execute("""
        SELECT rv.id_riesgo_vehiculo,
               rv.id_tipo_riesgo,
               tr.nombre_riesgo,
               rv.anio_inicio,
               rv.anio_fin,
               rv.nota_regla
        FROM riesgo_vehiculo rv
        JOIN tipo_riesgo tr ON rv.id_tipo_riesgo = tr.id_tipo_riesgo
        WHERE rv.id_empresa    = %s
          AND rv.id_marca      = %s
          AND rv.id_modelo     = %s
          AND rv.activo        = 1
        ORDER BY rv.id_riesgo_vehiculo DESC
    """, (id_empresa, id_marca, id_modelo))
    reglas_especificas = cur.fetchall()

    for regla in reglas_especificas:
        id_rv, id_tr, nombre_tr, a_ini, a_fin, nota = regla

        if not _año_en_rango(anio_fabricacion, a_ini, a_fin):
            continue  # Esta regla no aplica por año → probar la siguiente

        return {
            'asegurable':     True,
            'tipo_riesgo':    nombre_tr,
            'id_tipo_riesgo': id_tr,
            'detalle':        f'Regla específica por modelo. {nota or ""}',
        }

    # ------------------------------------------------------------------
    # Paso 3: Buscar regla GENERAL de la marca (id_modelo IS NULL)
    # ------------------------------------------------------------------
    cur.execute("""
        SELECT rv.id_riesgo_vehiculo,
               rv.id_tipo_riesgo,
               tr.nombre_riesgo,
               rv.anio_inicio,
               rv.anio_fin,
               rv.nota_regla
        FROM riesgo_vehiculo rv
        JOIN tipo_riesgo tr ON rv.id_tipo_riesgo = tr.id_tipo_riesgo
        WHERE rv.id_empresa  = %s
          AND rv.id_marca    = %s
          AND rv.id_modelo IS NULL
          AND rv.activo      = 1
        ORDER BY rv.id_riesgo_vehiculo DESC
    """, (id_empresa, id_marca))
    reglas_generales = cur.fetchall()

    for regla in reglas_generales:
        id_rv, id_tr, nombre_tr, a_ini, a_fin, nota = regla

        if not _año_en_rango(anio_fabricacion, a_ini, a_fin):
            continue  # Esta regla no aplica por año

        # --------------------------------------------------------------
        # Paso 3a: Verificar si este modelo tiene una EXCEPCIÓN
        #          dentro de esta regla general
        # --------------------------------------------------------------
        cur.execute("""
            SELECT rme.tipo_excepcion,
                   rme.id_tipo_riesgo_alternativo,
                   tr2.nombre_riesgo,
                   rme.nota_excepcion
            FROM riesgo_modelo_excepcion rme
            LEFT JOIN tipo_riesgo tr2
                   ON rme.id_tipo_riesgo_alternativo = tr2.id_tipo_riesgo
            WHERE rme.id_riesgo_vehiculo = %s
              AND rme.id_modelo          = %s
        """, (id_rv, id_modelo))
        excepcion = cur.fetchone()

        if excepcion:
            tipo_exc, id_tr_alt, nombre_tr_alt, nota_exc = excepcion

            if tipo_exc == 'EXCLUIR':
                # El modelo está excluido de la regla general.
                # Si tiene riesgo alternativo → usar ese.
                # Si no tiene (NULL) → No Asegurable.
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
                # La regla general solo aplica a modelos INCLUIR_SOLO.
                # Este modelo SÍ está en la lista → usar el riesgo de la regla general.
                return {
                    'asegurable':     True,
                    'tipo_riesgo':    nombre_tr,
                    'id_tipo_riesgo': id_tr,
                    'detalle':        f'Incluido explícitamente en regla general. {nota_exc or ""}',
                }

        else:
            # Sin excepción → verificar si la regla usa INCLUIR_SOLO
            # Si la regla tiene excepciones de tipo INCLUIR_SOLO para otros modelos,
            # este modelo NO está en la lista → No Asegurable.
            cur.execute("""
                SELECT COUNT(*) FROM riesgo_modelo_excepcion
                WHERE id_riesgo_vehiculo = %s
                  AND tipo_excepcion     = 'INCLUIR_SOLO'
            """, (id_rv,))
            tiene_incluir_solo = cur.fetchone()[0] > 0

            if tiene_incluir_solo:
                # La regla es de tipo lista blanca y este modelo no está en ella
                return {
                    **NO_ASEGURABLE,
                    'detalle': 'El modelo no está en la lista de modelos incluidos para esta regla.',
                }
            else:
                # Regla general con EXCLUIR (o sin excepciones) → aplica a todos los demás
                return {
                    'asegurable':     True,
                    'tipo_riesgo':    nombre_tr,
                    'id_tipo_riesgo': id_tr,
                    'detalle':        f'Aplica regla general de marca. {nota or ""}',
                }

    # ------------------------------------------------------------------
    # Paso 4: No se encontró ninguna regla aplicable → No Asegurable
    # ------------------------------------------------------------------
    return NO_ASEGURABLE
