# =============================================================================
# models/vehiculo.py
# Queries de: marca, modelo, valor_vehiculo
# =============================================================================


# ── Marcas ────────────────────────────────────────────────────────────────────

def get_all_marcas(cur):
    cur.execute("SELECT id_marca, nombre_marca FROM marca ORDER BY nombre_marca")
    return cur.fetchall()


def get_marca_by_nombre(cur, nombre_marca):
    cur.execute("SELECT id_marca FROM marca WHERE nombre_marca=%s", (nombre_marca,))
    return cur.fetchone()


def insert_marca(cur, nombre_marca):
    cur.execute("INSERT INTO marca (nombre_marca) VALUES (%s)", (nombre_marca,))


# ── Modelos ───────────────────────────────────────────────────────────────────

def get_modelos_paginados(cur, marca_id, modelo_search, per_page, offset):
    query = """
        SELECT mo.id_modelo, ma.nombre_marca, mo.nombre_modelo, mo.comentario, mo.id_marca
        FROM modelo mo
        JOIN marca ma ON mo.id_marca = ma.id_marca
        WHERE 1=1
    """
    params = []
    if marca_id:
        query += " AND mo.id_marca = %s"
        params.append(marca_id)
    if modelo_search:
        query += " AND mo.nombre_modelo LIKE %s"
        params.append(f"%{modelo_search}%")
    query += " ORDER BY ma.nombre_marca, mo.nombre_modelo LIMIT %s OFFSET %s"
    params.extend([per_page, offset])
    cur.execute(query, params)
    return cur.fetchall()


def count_modelos(cur, marca_id, modelo_search):
    query = "SELECT COUNT(*) FROM modelo mo WHERE 1=1"
    params = []
    if marca_id:
        query += " AND mo.id_marca = %s"
        params.append(marca_id)
    if modelo_search:
        query += " AND mo.nombre_modelo LIKE %s"
        params.append(f"%{modelo_search}%")
    cur.execute(query, params)
    return cur.fetchone()[0]


def get_modelos_por_marca(cur, id_marca):
    cur.execute(
        "SELECT id_modelo, nombre_modelo FROM modelo WHERE id_marca=%s ORDER BY nombre_modelo",
        (id_marca,)
    )
    return cur.fetchall()


def get_modelo_by_id(cur, id_modelo):
    cur.execute("""
        SELECT mo.id_modelo, mo.id_marca, mo.nombre_modelo, ma.nombre_marca
        FROM modelo mo
        JOIN marca ma ON mo.id_marca = ma.id_marca
        WHERE mo.id_modelo = %s
    """, (id_modelo,))
    return cur.fetchone()


def get_modelo_by_marca_nombre(cur, id_marca, nombre_modelo):
    cur.execute(
        "SELECT id_modelo FROM modelo WHERE id_marca=%s AND nombre_modelo=%s",
        (id_marca, nombre_modelo)
    )
    return cur.fetchone()


def insert_modelo(cur, id_marca, nombre_modelo, comentario):
    cur.execute(
        "INSERT INTO modelo (id_marca, nombre_modelo, comentario) VALUES (%s,%s,%s)",
        (id_marca, nombre_modelo, comentario or None)
    )


def update_modelo(cur, id_modelo, id_marca, nombre_modelo, comentario):
    cur.execute(
        "UPDATE modelo SET id_marca=%s, nombre_modelo=%s, comentario=%s WHERE id_modelo=%s",
        (id_marca, nombre_modelo, comentario or None, id_modelo)
    )


def delete_modelo(cur, id_modelo):
    cur.execute("DELETE FROM modelo WHERE id_modelo=%s", (id_modelo,))


# ── Valores vehiculares ───────────────────────────────────────────────────────

def get_vrn(cur, id_modelo):
    """Devuelve el valor VRN (0km) del modelo, o None si no existe."""
    cur.execute("""
        SELECT valor FROM valor_vehiculo
        WHERE id_modelo = %s AND anio IS NULL AND tipo_valor = 'VRN'
        LIMIT 1
    """, (id_modelo,))
    row = cur.fetchone()
    return float(row[0]) if row else None


def get_valor_historico(cur, id_modelo, anio):
    """Devuelve el valor histórico exacto para un año, o None si no existe."""
    cur.execute("""
        SELECT valor FROM valor_vehiculo
        WHERE id_modelo = %s AND anio = %s AND tipo_valor = 'HISTORICO'
        LIMIT 1
    """, (id_modelo, anio))
    row = cur.fetchone()
    return float(row[0]) if row else None


def get_valor_by_anio_tipo(cur, id_modelo, anio, tipo_valor):
    """Busca un registro existente de valor_vehiculo para upsert."""
    if anio is None:
        cur.execute(
            "SELECT id_valor FROM valor_vehiculo WHERE id_modelo=%s AND anio IS NULL AND tipo_valor=%s",
            (id_modelo, tipo_valor)
        )
    else:
        cur.execute(
            "SELECT id_valor FROM valor_vehiculo WHERE id_modelo=%s AND anio=%s AND tipo_valor=%s",
            (id_modelo, anio, tipo_valor)
        )
    return cur.fetchone()


def get_todos_valores_modelo(cur, id_modelo):
    """
    Devuelve todos los valores registrados para un modelo:
    primero el VRN, luego los históricos ordenados por año DESC.
    Retorna lista de dicts con: id_valor, tipo_valor, anio, valor
    """
    cur.execute("""
        SELECT id_valor, tipo_valor, anio, valor
        FROM valor_vehiculo
        WHERE id_modelo = %s
        ORDER BY
            CASE tipo_valor WHEN 'VRN' THEN 0 ELSE 1 END,
            anio DESC
    """, (id_modelo,))
    rows = cur.fetchall()
    return [
        {
            'id_valor':   r[0],
            'tipo_valor': r[1],
            'anio':       r[2],
            'valor':      float(r[3]),
        }
        for r in rows
    ]


def insert_valor_vehiculo(cur, id_modelo, anio, valor, tipo_valor):
    if anio is None:
        cur.execute(
            "INSERT INTO valor_vehiculo (id_modelo, anio, valor, tipo_valor) VALUES (%s, NULL, %s, %s)",
            (id_modelo, valor, tipo_valor)
        )
    else:
        cur.execute(
            "INSERT INTO valor_vehiculo (id_modelo, anio, valor, tipo_valor) VALUES (%s, %s, %s, %s)",
            (id_modelo, anio, valor, tipo_valor)
        )


def update_valor_vehiculo(cur, id_valor, valor):
    cur.execute("UPDATE valor_vehiculo SET valor=%s WHERE id_valor=%s", (valor, id_valor))


def delete_valor_vehiculo(cur, id_valor):
    cur.execute("DELETE FROM valor_vehiculo WHERE id_valor=%s", (id_valor,))


def upsert_valor_vehiculo(cur, id_modelo, anio, valor, tipo_valor):
    """
    Inserta o actualiza un valor vehicular.
    Si ya existe un registro para (id_modelo, anio, tipo_valor), lo actualiza.
    Retorna 'inserted' o 'updated'.
    """
    existente = get_valor_by_anio_tipo(cur, id_modelo, anio, tipo_valor)
    if existente:
        update_valor_vehiculo(cur, existente[0], valor)
        return 'updated'
    else:
        insert_valor_vehiculo(cur, id_modelo, anio, valor, tipo_valor)
        return 'inserted'
