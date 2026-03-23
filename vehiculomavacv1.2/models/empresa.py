# =============================================================================
# models/empresa.py
# Queries de: empresa, tipo_riesgo, empresa_tipo_riesgo
# =============================================================================


# ── Empresas ──────────────────────────────────────────────────────────────────

def get_all_empresas(cur):
    cur.execute(
        "SELECT id_empresa, nombre_empresa, activo, fecha_creacion FROM empresa ORDER BY id_empresa"
    )
    return cur.fetchall()


def get_empresas_activas(cur):
    cur.execute(
        "SELECT id_empresa, nombre_empresa FROM empresa WHERE activo=1 ORDER BY id_empresa"
    )
    return cur.fetchall()


def insert_empresa(cur, nombre, activo):
    cur.execute(
        "INSERT INTO empresa (nombre_empresa, activo) VALUES (%s, %s)",
        (nombre, activo)
    )


def update_empresa(cur, id_empresa, nombre, activo):
    cur.execute(
        "UPDATE empresa SET nombre_empresa=%s, activo=%s WHERE id_empresa=%s",
        (nombre, activo, id_empresa)
    )


# ── Tipos de riesgo ───────────────────────────────────────────────────────────

def get_all_tipos_riesgo(cur):
    cur.execute(
        "SELECT id_tipo_riesgo, nombre_riesgo, codigo_interno FROM tipo_riesgo ORDER BY id_tipo_riesgo"
    )
    return cur.fetchall()


def get_tipos_riesgo_por_empresa(cur, id_empresa):
    cur.execute("""
        SELECT tr.id_tipo_riesgo, tr.nombre_riesgo, tr.codigo_interno
        FROM empresa_tipo_riesgo etr
        JOIN tipo_riesgo tr ON etr.id_tipo_riesgo = tr.id_tipo_riesgo
        WHERE etr.id_empresa = %s AND etr.activo = 1
        ORDER BY tr.id_tipo_riesgo
    """, (id_empresa,))
    return cur.fetchall()


def insert_tipo_riesgo(cur, nombre, codigo):
    cur.execute(
        "INSERT INTO tipo_riesgo (nombre_riesgo, codigo_interno) VALUES (%s, %s)",
        (nombre, codigo)
    )


def update_tipo_riesgo(cur, id_tipo_riesgo, nombre, codigo):
    cur.execute(
        "UPDATE tipo_riesgo SET nombre_riesgo=%s, codigo_interno=%s WHERE id_tipo_riesgo=%s",
        (nombre, codigo, id_tipo_riesgo)
    )


def delete_tipo_riesgo(cur, id_tipo_riesgo):
    cur.execute("DELETE FROM tipo_riesgo WHERE id_tipo_riesgo=%s", (id_tipo_riesgo,))


# ── Asignaciones empresa↔tipo_riesgo ─────────────────────────────────────────

def get_all_asignaciones(cur):
    cur.execute("""
        SELECT
            e.id_empresa, e.nombre_empresa,
            tr.id_tipo_riesgo, tr.nombre_riesgo, tr.codigo_interno,
            etr.activo
        FROM empresa_tipo_riesgo etr
        JOIN empresa e ON etr.id_empresa = e.id_empresa
        JOIN tipo_riesgo tr ON etr.id_tipo_riesgo = tr.id_tipo_riesgo
        ORDER BY e.id_empresa, tr.id_tipo_riesgo
    """)
    return cur.fetchall()


def insert_asignacion(cur, id_empresa, id_tipo_riesgo, activo):
    cur.execute(
        "INSERT INTO empresa_tipo_riesgo (id_empresa, id_tipo_riesgo, activo) VALUES (%s,%s,%s)",
        (id_empresa, id_tipo_riesgo, activo)
    )


def update_asignacion(cur, id_empresa, id_tipo_riesgo, activo):
    cur.execute(
        "UPDATE empresa_tipo_riesgo SET activo=%s WHERE id_empresa=%s AND id_tipo_riesgo=%s",
        (activo, id_empresa, id_tipo_riesgo)
    )


def delete_asignacion(cur, id_empresa, id_tipo_riesgo):
    cur.execute(
        "DELETE FROM empresa_tipo_riesgo WHERE id_empresa=%s AND id_tipo_riesgo=%s",
        (id_empresa, id_tipo_riesgo)
    )