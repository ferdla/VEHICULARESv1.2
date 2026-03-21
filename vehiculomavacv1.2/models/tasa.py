# =============================================================================
# models/tasa.py
# Queries de: tasa
# =============================================================================


def get_tasas_por_empresa(cur, id_empresa, id_tipo_riesgo=None):
    query = """
        SELECT id_tipo_riesgo, anio_inicio, anio_fin, es_0km, tasa
        FROM tasa
        WHERE id_empresa=%s
    """
    params = [id_empresa]
    if id_tipo_riesgo:
        query += " AND id_tipo_riesgo=%s"
        params.append(id_tipo_riesgo)
    cur.execute(query, params)
    return cur.fetchall()


def get_tasa(cur, id_empresa, id_tipo_riesgo, anio_fabricacion, es_0km):
    """
    Busca la tasa exacta para empresa + tipo_riesgo + año + flag 0km.
    Devuelve el valor float de la tasa o None si no existe.
    """
    cur.execute("""
        SELECT tasa FROM tasa
        WHERE id_empresa     = %s
          AND id_tipo_riesgo = %s
          AND anio_inicio   <= %s
          AND anio_fin      >= %s
          AND es_0km        = %s
        ORDER BY anio_inicio DESC
        LIMIT 1
    """, (id_empresa, id_tipo_riesgo, anio_fabricacion, anio_fabricacion, es_0km))
    row = cur.fetchone()
    return float(row[0]) if row else None


def get_tasa_fallback(cur, id_empresa, id_tipo_riesgo, anio_fabricacion):
    """
    Fallback cuando es_0km=1 pero no existe tasa 0km:
    busca cualquier tasa para ese año sin importar es_0km.
    """
    cur.execute("""
        SELECT tasa FROM tasa
        WHERE id_empresa     = %s
          AND id_tipo_riesgo = %s
          AND anio_inicio   <= %s
          AND anio_fin      >= %s
        ORDER BY es_0km DESC, anio_inicio DESC
        LIMIT 1
    """, (id_empresa, id_tipo_riesgo, anio_fabricacion, anio_fabricacion))
    row = cur.fetchone()
    return float(row[0]) if row else None
