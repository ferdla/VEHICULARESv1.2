# =============================================================================
# models/cobertura.py
# Queries de: cobertura_empresa, cobertura_deducibles
# =============================================================================

CAMPOS_COBERTURA = [
    'rc_terceros', 'rc_ocupantes',
    'acc_muerte', 'acc_invalidez', 'acc_curacion', 'acc_sepelio', 'acc_estetica',
    'gps', 'defensa_juridica', 'auxilio_mecanico',
    'veh_reemplazo', 'chofer_reemplazo',
    'alcoholemia',
]

CAMPOS_DEDUCIBLES = [
    'deducible_evento', 'deducible_taller', 'deducible_robo',
    'deducible_musicales', 'deducible_veh_reemplazo',
    'deducible_lunas', 'deducible_conductores',
]


# ── cobertura_empresa ─────────────────────────────────────────────────────────

def get_coberturas_empresa(cur, id_empresa):
    """
    Devuelve un dict con los campos de cobertura_empresa para la empresa dada.
    Retorna {} si no existe registro.
    """
    cur.execute("SELECT * FROM cobertura_empresa WHERE id_empresa=%s", (id_empresa,))
    cols = [d[0] for d in cur.description]
    row  = cur.fetchone()
    if not row:
        return {}
    return dict(zip(cols, row))


def get_todas_coberturas(cur):
    """
    Devuelve un dict {id_empresa: dict_campos} con todas las empresas.
    """
    cur.execute("SELECT * FROM cobertura_empresa")
    cols = [d[0] for d in cur.description]
    resultado = {}
    for row in cur.fetchall():
        registro = dict(zip(cols, row))
        resultado[registro['id_empresa']] = registro
    return resultado


def upsert_coberturas_empresa(cur, id_empresa, valores):
    """
    INSERT o UPDATE en cobertura_empresa.
    valores: dict {campo: valor} con exactamente los campos de CAMPOS_COBERTURA.
    """
    cur.execute("SELECT id_cobertura FROM cobertura_empresa WHERE id_empresa=%s", (id_empresa,))
    existe = cur.fetchone()

    if existe:
        set_clause = ', '.join([f"{c} = %s" for c in CAMPOS_COBERTURA])
        cur.execute(
            f"UPDATE cobertura_empresa SET {set_clause} WHERE id_empresa = %s",
            [valores[c] for c in CAMPOS_COBERTURA] + [id_empresa]
        )
    else:
        cols_str     = ', '.join(['id_empresa'] + CAMPOS_COBERTURA)
        placeholders = ', '.join(['%s'] * (len(CAMPOS_COBERTURA) + 1))
        cur.execute(
            f"INSERT INTO cobertura_empresa ({cols_str}) VALUES ({placeholders})",
            [id_empresa] + [valores[c] for c in CAMPOS_COBERTURA]
        )


# ── cobertura_deducibles ──────────────────────────────────────────────────────

def get_deducibles_por_empresa(cur, id_empresa, nombre_tipo_riesgo):
    """
    Busca deducibles cruzando por nombre de tipo_riesgo.
    Retorna dict con los campos de deducibles, o None si no existe.
    """
    if not nombre_tipo_riesgo:
        return None
    cur.execute("""
        SELECT cd.deducible_evento,
               cd.deducible_taller,
               cd.deducible_robo,
               cd.deducible_musicales,
               cd.deducible_veh_reemplazo,
               cd.deducible_lunas,
               cd.deducible_conductores
        FROM cobertura_deducibles cd
        JOIN tipo_riesgo tr ON cd.id_tipo_riesgo = tr.id_tipo_riesgo
        WHERE cd.id_empresa = %s AND tr.nombre_riesgo = %s
    """, (id_empresa, nombre_tipo_riesgo))
    row = cur.fetchone()
    if not row:
        return None
    return {
        'evento':        row[0],
        'taller':        row[1],
        'robo':          row[2],
        'musicales':     row[3],
        'veh_reemplazo': row[4],
        'lunas':         row[5],
        'conductores':   row[6],
    }


def get_todos_deducibles(cur):
    """
    Devuelve dict {id_empresa: [lista de deducibles]} para todas las empresas.
    """
    cur.execute("""
        SELECT cd.id_deducible, cd.id_empresa, cd.id_tipo_riesgo,
               tr.nombre_riesgo,
               cd.deducible_evento, cd.deducible_taller, cd.deducible_robo,
               cd.deducible_musicales, cd.deducible_veh_reemplazo,
               cd.deducible_lunas, cd.deducible_conductores
        FROM cobertura_deducibles cd
        JOIN tipo_riesgo tr ON cd.id_tipo_riesgo = tr.id_tipo_riesgo
        ORDER BY cd.id_empresa, cd.id_tipo_riesgo
    """)
    resultado = {}
    for row in cur.fetchall():
        id_emp = row[1]
        if id_emp not in resultado:
            resultado[id_emp] = []
        resultado[id_emp].append({
            'id_deducible':            row[0],
            'id_tipo_riesgo':          row[2],
            'nombre_riesgo':           row[3],
            'deducible_evento':        row[4],
            'deducible_taller':        row[5],
            'deducible_robo':          row[6],
            'deducible_musicales':     row[7],
            'deducible_veh_reemplazo': row[8],
            'deducible_lunas':         row[9],
            'deducible_conductores':   row[10],
        })
    return resultado


def upsert_deducibles(cur, id_empresa, id_tipo_riesgo, valores):
    """
    INSERT o UPDATE en cobertura_deducibles para empresa + tipo_riesgo.
    valores: dict {campo: valor} con exactamente los campos de CAMPOS_DEDUCIBLES.
    """
    cur.execute("""
        SELECT id_deducible FROM cobertura_deducibles
        WHERE id_empresa=%s AND id_tipo_riesgo=%s
    """, (id_empresa, id_tipo_riesgo))
    existe = cur.fetchone()

    if existe:
        set_clause = ', '.join([f"{c} = %s" for c in CAMPOS_DEDUCIBLES])
        cur.execute(
            f"UPDATE cobertura_deducibles SET {set_clause} "
            f"WHERE id_empresa=%s AND id_tipo_riesgo=%s",
            [valores[c] for c in CAMPOS_DEDUCIBLES] + [id_empresa, id_tipo_riesgo]
        )
    else:
        cols_str     = ', '.join(['id_empresa', 'id_tipo_riesgo'] + CAMPOS_DEDUCIBLES)
        placeholders = ', '.join(['%s'] * (len(CAMPOS_DEDUCIBLES) + 2))
        cur.execute(
            f"INSERT INTO cobertura_deducibles ({cols_str}) VALUES ({placeholders})",
            [id_empresa, id_tipo_riesgo] + [valores[c] for c in CAMPOS_DEDUCIBLES]
        )
