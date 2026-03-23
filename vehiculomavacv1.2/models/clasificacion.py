# =============================================================================
# models/clasificacion.py
# Queries de: regla_clasificacion, excepcion_confirmada,
#             excepcion_pendiente, regla_pendiente
# =============================================================================


# ── regla_clasificacion ───────────────────────────────────────────────────────

def get_reglas(cur, empresa_id=None, tipo_riesgo_id=None, marca_id=None):
    query = """
        SELECT rc.id_regla_clasificacion,
               e.nombre_empresa, e.id_empresa,
               tr.nombre_riesgo,
               m.nombre_marca,
               COALESCE(mo.nombre_modelo, 'Toda la marca'),
               rc.anio_inicio, rc.anio_fin,
               rc.suma_min, rc.suma_max,
               rc.nota_regla
        FROM regla_clasificacion rc
        JOIN empresa e      ON rc.id_empresa     = e.id_empresa
        JOIN tipo_riesgo tr ON rc.id_tipo_riesgo = tr.id_tipo_riesgo
        JOIN marca m        ON rc.id_marca       = m.id_marca
        LEFT JOIN modelo mo ON rc.id_modelo      = mo.id_modelo
        WHERE 1=1
    """
    params = []
    if empresa_id:
        query += " AND rc.id_empresa=%s"
        params.append(empresa_id)
    if tipo_riesgo_id:
        query += " AND rc.id_tipo_riesgo=%s"
        params.append(tipo_riesgo_id)
    if marca_id:
        query += " AND rc.id_marca=%s"
        params.append(marca_id)
    query += " ORDER BY rc.id_regla_clasificacion DESC"
    cur.execute(query, params)
    return cur.fetchall()


def insert_regla(cur, id_empresa, id_tipo_riesgo, id_marca, id_modelo,
                 anio_inicio, anio_fin, suma_min, suma_max, nota_regla):
    cur.execute("""
        INSERT INTO regla_clasificacion
            (id_empresa, id_tipo_riesgo, id_marca, id_modelo,
             anio_inicio, anio_fin, suma_min, suma_max, nota_regla)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (id_empresa, id_tipo_riesgo, id_marca, id_modelo,
          anio_inicio, anio_fin, suma_min, suma_max, nota_regla))


def delete_regla(cur, id_regla):
    cur.execute("DELETE FROM regla_clasificacion WHERE id_regla_clasificacion=%s", (id_regla,))


def get_id_marca_de_regla(cur, id_regla):
    cur.execute(
        "SELECT id_marca FROM regla_clasificacion WHERE id_regla_clasificacion=%s",
        (id_regla,)
    )
    row = cur.fetchone()
    return row[0] if row else None


# ── excepcion_confirmada ──────────────────────────────────────────────────────

def get_excepciones_confirmadas_por_regla(cur, id_regla):
    cur.execute("""
        SELECT ec.id_excepcion, m.nombre_modelo, ec.tipo_excepcion,
               COALESCE(tr.nombre_riesgo, 'No Asegurable'), ec.nota_excepcion
        FROM excepcion_confirmada ec
        JOIN modelo m ON ec.id_modelo = m.id_modelo
        LEFT JOIN tipo_riesgo tr ON ec.id_tipo_riesgo_alternativo = tr.id_tipo_riesgo
        WHERE ec.id_regla_clasificacion = %s
        ORDER BY m.nombre_modelo
    """, (id_regla,))
    return cur.fetchall()


def upsert_excepcion_confirmada(cur, id_regla, id_modelo, tipo_excepcion,
                                 id_tipo_riesgo_alternativo, nota_excepcion):
    cur.execute("""
        INSERT INTO excepcion_confirmada
            (id_regla_clasificacion, id_modelo, tipo_excepcion,
             id_tipo_riesgo_alternativo, nota_excepcion)
        VALUES (%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
            tipo_excepcion             = VALUES(tipo_excepcion),
            id_tipo_riesgo_alternativo = VALUES(id_tipo_riesgo_alternativo),
            nota_excepcion             = VALUES(nota_excepcion)
    """, (id_regla, id_modelo, tipo_excepcion,
          id_tipo_riesgo_alternativo, nota_excepcion))


def delete_excepcion_confirmada(cur, id_excepcion):
    cur.execute("DELETE FROM excepcion_confirmada WHERE id_excepcion=%s", (id_excepcion,))


def get_modelos_existentes_para_excepcion(cur, id_marca, texto):
    """Busca modelos cuyo nombre comience con 'texto' para la marca dada."""
    cur.execute(
        "SELECT id_modelo FROM modelo WHERE id_marca=%s AND nombre_modelo LIKE %s",
        (id_marca, f"{texto}%")
    )
    return [row[0] for row in cur.fetchall()]


def count_excepcion_incluir_solo(cur, id_regla):
    """Cuenta cuántas excepciones INCLUIR_SOLO tiene una regla (lista blanca)."""
    cur.execute("""
        SELECT COUNT(*) FROM excepcion_confirmada
        WHERE id_regla_clasificacion = %s AND tipo_excepcion = 'INCLUIR_SOLO'
    """, (id_regla,))
    return cur.fetchone()[0]


# ── excepcion_pendiente ───────────────────────────────────────────────────────

def get_excepciones_pendientes_por_regla(cur, id_regla):
    cur.execute("""
        SELECT ep.id_excepcion_pendiente,
               ep.nombre_modelo_pendiente,
               ep.tipo_excepcion,
               COALESCE(tr.nombre_riesgo, 'No Asegurable'),
               ep.nota_excepcion
        FROM excepcion_pendiente ep
        LEFT JOIN tipo_riesgo tr ON ep.id_tipo_riesgo_alt = tr.id_tipo_riesgo
        WHERE ep.id_regla_clasificacion = %s AND ep.resuelta = 0
        ORDER BY ep.nombre_modelo_pendiente
    """, (id_regla,))
    return cur.fetchall()


def insert_excepcion_pendiente(cur, id_regla, nombre_modelo, tipo_excepcion,
                                id_tipo_riesgo_alt, nota_excepcion):
    cur.execute("""
        INSERT INTO excepcion_pendiente
            (id_regla_clasificacion, nombre_modelo_pendiente,
             tipo_excepcion, id_tipo_riesgo_alt, nota_excepcion)
        VALUES (%s,%s,%s,%s,%s)
    """, (id_regla, nombre_modelo, tipo_excepcion,
          id_tipo_riesgo_alt, nota_excepcion))


def insert_excepcion_pendiente_ignore(cur, id_regla, nombre_modelo,
                                       tipo_excepcion, id_tipo_riesgo_alt, nota):
    """INSERT IGNORE — no duplica si ya existe."""
    cur.execute("""
        INSERT IGNORE INTO excepcion_pendiente
            (id_regla_clasificacion, nombre_modelo_pendiente,
             tipo_excepcion, id_tipo_riesgo_alt, nota_excepcion)
        VALUES (%s,%s,%s,%s,%s)
    """, (id_regla, nombre_modelo, tipo_excepcion, id_tipo_riesgo_alt, nota))


def count_excepcion_pendiente_existente(cur, id_regla, texto):
    """Verifica si ya hay una excepción pendiente con ese patrón para no duplicar."""
    cur.execute("""
        SELECT COUNT(*) FROM excepcion_pendiente
        WHERE id_regla_clasificacion=%s AND nombre_modelo_pendiente=%s AND resuelta=0
    """, (id_regla, texto))
    return cur.fetchone()[0]


def marcar_excepcion_pendiente_resuelta(cur, id_pendiente):
    cur.execute(
        "UPDATE excepcion_pendiente SET resuelta=1 WHERE id_excepcion_pendiente=%s",
        (id_pendiente,)
    )


def delete_excepcion_pendiente(cur, id_pendiente):
    cur.execute(
        "DELETE FROM excepcion_pendiente WHERE id_excepcion_pendiente=%s",
        (id_pendiente,)
    )


def get_excepcion_pendiente_by_id(cur, id_pendiente):
    cur.execute("""
        SELECT id_regla_clasificacion, tipo_excepcion,
               id_tipo_riesgo_alt, nota_excepcion
        FROM excepcion_pendiente
        WHERE id_excepcion_pendiente=%s AND resuelta=0
    """, (id_pendiente,))
    return cur.fetchone()


def get_excepciones_pendientes_para_modelo(cur, id_marca, nombre_modelo):
    """
    Busca excepciones pendientes que coincidan con un modelo recién creado
    (para mostrar el modal de confirmación en vehiculos).
    """
    cur.execute("""
        SELECT ep.id_excepcion_pendiente,
               ep.id_regla_clasificacion,
               ep.nombre_modelo_pendiente,
               ep.tipo_excepcion,
               ep.id_tipo_riesgo_alt,
               COALESCE(tr.nombre_riesgo, 'No Asegurable') AS nombre_riesgo_alt,
               e.nombre_empresa,
               rv.nota_regla
        FROM excepcion_pendiente ep
        JOIN regla_clasificacion rv  ON ep.id_regla_clasificacion = rv.id_regla_clasificacion
        JOIN empresa e               ON rv.id_empresa = e.id_empresa
        LEFT JOIN tipo_riesgo tr     ON ep.id_tipo_riesgo_alt = tr.id_tipo_riesgo
        WHERE rv.id_marca = %s
          AND ep.resuelta = 0
          AND %s LIKE CONCAT(ep.nombre_modelo_pendiente, '%%')
    """, (id_marca, nombre_modelo))
    return cur.fetchall()


def get_excepciones_pendientes_masivo(cur, id_marca, nombre_modelo):
    """
    Igual que la anterior pero devuelve solo los campos necesarios
    para la resolución automática en carga masiva.
    """
    cur.execute("""
        SELECT ep.id_excepcion_pendiente,
               ep.id_regla_clasificacion,
               ep.tipo_excepcion,
               ep.id_tipo_riesgo_alt,
               ep.nota_excepcion
        FROM excepcion_pendiente ep
        JOIN regla_clasificacion rc ON ep.id_regla_clasificacion = rc.id_regla_clasificacion
        WHERE rc.id_marca = %s
          AND ep.resuelta = 0
          AND %s LIKE CONCAT(ep.nombre_modelo_pendiente, '%%')
    """, (id_marca, nombre_modelo))
    return cur.fetchall()


# ── regla_pendiente ───────────────────────────────────────────────────────────

def get_reglas_pendientes(cur, empresa_id=None):
    query = """
        SELECT rp.id_regla_pendiente,
               e.nombre_empresa,
               tr.nombre_riesgo,
               rp.nombre_marca_pendiente,
               COALESCE(rp.nombre_modelo_pendiente, 'Toda la marca'),
               rp.anio_inicio, rp.anio_fin,
               rp.suma_min, rp.suma_max,
               rp.nota_regla
        FROM regla_pendiente rp
        JOIN empresa e      ON rp.id_empresa     = e.id_empresa
        JOIN tipo_riesgo tr ON rp.id_tipo_riesgo = tr.id_tipo_riesgo
        WHERE rp.resuelta = 0
    """
    params = []
    if empresa_id:
        query += " AND rp.id_empresa=%s"
        params.append(empresa_id)
    query += " ORDER BY e.nombre_empresa, rp.nombre_marca_pendiente"
    cur.execute(query, params)
    return cur.fetchall()


def get_reglas_pendientes_por_marca(cur, nombre_marca):
    """Busca reglas pendientes que esperan una marca específica."""
    cur.execute("""
        SELECT rp.id_regla_pendiente,
               rp.id_empresa, e.nombre_empresa,
               rp.id_tipo_riesgo, tr.nombre_riesgo,
               rp.nombre_modelo_pendiente,
               rp.anio_inicio, rp.anio_fin,
               rp.suma_min, rp.suma_max, rp.nota_regla
        FROM regla_pendiente rp
        JOIN empresa e      ON rp.id_empresa     = e.id_empresa
        JOIN tipo_riesgo tr ON rp.id_tipo_riesgo = tr.id_tipo_riesgo
        WHERE rp.nombre_marca_pendiente = %s AND rp.resuelta = 0
    """, (nombre_marca,))
    return cur.fetchall()


def insert_regla_pendiente(cur, id_empresa, id_tipo_riesgo, nombre_marca,
                            nombre_modelo, anio_inicio, anio_fin,
                            suma_min, suma_max, nota_regla):
    cur.execute("""
        INSERT INTO regla_pendiente
            (id_empresa, id_tipo_riesgo, nombre_marca_pendiente,
             nombre_modelo_pendiente, anio_inicio, anio_fin,
             suma_min, suma_max, nota_regla)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (id_empresa, id_tipo_riesgo, nombre_marca,
          nombre_modelo or None,
          anio_inicio, anio_fin, suma_min, suma_max, nota_regla))


def get_regla_pendiente_by_id(cur, id_pendiente):
    cur.execute("""
        SELECT id_empresa, id_tipo_riesgo,
               nombre_modelo_pendiente,
               anio_inicio, anio_fin,
               suma_min, suma_max, nota_regla
        FROM regla_pendiente
        WHERE id_regla_pendiente=%s AND resuelta=0
    """, (id_pendiente,))
    return cur.fetchone()


def marcar_regla_pendiente_resuelta(cur, id_pendiente):
    cur.execute(
        "UPDATE regla_pendiente SET resuelta=1 WHERE id_regla_pendiente=%s",
        (id_pendiente,)
    )


def delete_regla_pendiente(cur, id_pendiente):
    cur.execute(
        "DELETE FROM regla_pendiente WHERE id_regla_pendiente=%s",
        (id_pendiente,)
    )


def count_reglas_pendientes_por_marca(cur, nombre_marca):
    cur.execute(
        "SELECT COUNT(*) FROM regla_pendiente WHERE nombre_marca_pendiente=%s AND resuelta=0",
        (nombre_marca,)
    )
    return cur.fetchone()[0]


def count_pendientes_globales(cur):
    """Para el badge de pendientes en el sidebar."""
    cur.execute("SELECT COUNT(*) FROM excepcion_pendiente WHERE resuelta=0")
    exc = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM regla_pendiente WHERE resuelta=0")
    reg = cur.fetchone()[0]
    return exc, reg
