# =============================================================================
# models/historial.py
# Queries para el historial de cotizaciones guardadas
# =============================================================================


def get_historial_paginado(cur, filtros, per_page, offset):
    """
    Devuelve la lista de cotizaciones con la prima mínima calculada.
    filtros: dict con claves opcionales: cliente, placa, fecha_desde, fecha_hasta
    """
    query = """
        SELECT
            cg.id_cotizacion_guardada,
            cg.numero_cotizacion,
            cg.fecha_cotizacion,
            cg.nombre_cliente,
            cg.dni_ruc,
            cg.placa,
            ma.nombre_marca,
            mo.nombre_modelo,
            cg.anio_fabricacion,
            cg.suma_asegurada,
            cg.editado_manualmente,
            MIN(CASE WHEN cd.asegurable = 1 THEN cd.prima_anual ELSE NULL END) AS prima_minima
        FROM cotizacion_guardada cg
        JOIN modelo mo ON cg.id_modelo = mo.id_modelo
        JOIN marca  ma ON mo.id_marca  = ma.id_marca
        LEFT JOIN cotizacion_detalle cd ON cd.id_cotizacion = cg.id_cotizacion_guardada
        WHERE 1=1
    """
    params = []
    query, params = _aplicar_filtros(query, params, filtros)
    query += " GROUP BY cg.id_cotizacion_guardada ORDER BY cg.fecha_creacion DESC"
    query += " LIMIT %s OFFSET %s"
    params.extend([per_page, offset])
    cur.execute(query, params)
    return cur.fetchall()


def count_historial(cur, filtros):
    query = """
        SELECT COUNT(DISTINCT cg.id_cotizacion_guardada)
        FROM cotizacion_guardada cg
        JOIN modelo mo ON cg.id_modelo = mo.id_modelo
        JOIN marca  ma ON mo.id_marca  = ma.id_marca
        WHERE 1=1
    """
    params = []
    query, params = _aplicar_filtros(query, params, filtros)
    cur.execute(query, params)
    return cur.fetchone()[0]


def delete_cotizacion(cur, id_cotizacion):
    """
    Elimina la cotización y su detalle (ON DELETE CASCADE lo maneja).
    """
    cur.execute(
        "DELETE FROM cotizacion_guardada WHERE id_cotizacion_guardada = %s",
        (id_cotizacion,)
    )


def _aplicar_filtros(query, params, filtros):
    if filtros.get('cliente'):
        query += " AND (cg.nombre_cliente LIKE %s OR cg.dni_ruc LIKE %s)"
        term = f"%{filtros['cliente']}%"
        params.extend([term, term])
    if filtros.get('placa'):
        query += " AND cg.placa LIKE %s"
        params.append(f"%{filtros['placa']}%")
    if filtros.get('fecha_desde'):
        query += " AND cg.fecha_cotizacion >= %s"
        params.append(filtros['fecha_desde'])
    if filtros.get('fecha_hasta'):
        query += " AND cg.fecha_cotizacion <= %s"
        params.append(filtros['fecha_hasta'])
    return query, params
