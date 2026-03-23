# =============================================================================
# models/cotizacion.py
# Queries de: cotizacion_guardada, cotizacion_detalle
# =============================================================================
import datetime


def get_cotizacion_completa(cur, id_cotizacion):
    """
    Devuelve la cabecera de una cotización con datos del vehículo.
    Retorna None si no existe.
    """
    cur.execute("""
        SELECT cg.id_cotizacion_guardada,
               cg.numero_cotizacion, cg.fecha_cotizacion,
               cg.nombre_cliente, cg.dni_ruc, cg.placa, cg.email,
               cg.suma_asegurada, cg.editado_manualmente, cg.observaciones,
               mo.nombre_modelo, ma.nombre_marca, cg.anio_fabricacion
        FROM cotizacion_guardada cg
        JOIN modelo mo ON cg.id_modelo = mo.id_modelo
        JOIN marca  ma ON mo.id_marca  = ma.id_marca
        WHERE cg.id_cotizacion_guardada = %s
    """, (id_cotizacion,))
    return cur.fetchone()


def get_detalles_cotizacion(cur, id_cotizacion):
    """
    Devuelve las filas de cotizacion_detalle para una cotización.
    """
    cur.execute("""
        SELECT e.id_empresa, e.nombre_empresa,
               cd.tipo_riesgo, cd.tasa, cd.prima_anual,
               cd.prima_editada, cd.asegurable
        FROM cotizacion_detalle cd
        JOIN empresa e ON cd.id_empresa = e.id_empresa
        WHERE cd.id_cotizacion = %s
        ORDER BY e.id_empresa
    """, (id_cotizacion,))
    return cur.fetchall()


def generar_numero_cotizacion(cur):
    """
    Genera el próximo número de cotización en formato COT-{AÑO}-{N:06d}-VEH.
    El contador reinicia cada año.
    """
    anio = datetime.date.today().year
    cur.execute(
        "SELECT COUNT(*) FROM cotizacion_guardada WHERE YEAR(fecha_cotizacion) = %s",
        (anio,)
    )
    n = cur.fetchone()[0] + 1
    return f"COT-{anio}-{str(n).zfill(6)}-VEH"


def insert_cotizacion(cur, numero, nombre_cliente, dni_ruc, placa, email,
                      id_modelo, anio_fabricacion, suma_asegurada):
    cur.execute("""
        INSERT INTO cotizacion_guardada
            (numero_cotizacion, fecha_cotizacion,
             nombre_cliente, dni_ruc, placa, email,
             id_modelo, anio_fabricacion, suma_asegurada)
        VALUES (%s, CURDATE(), %s, %s, %s, %s, %s, %s, %s)
    """, (numero, nombre_cliente, dni_ruc, placa, email,
          id_modelo, anio_fabricacion, suma_asegurada))


def insert_detalle_cotizacion(cur, id_cotizacion, id_empresa,
                               tipo_riesgo, tasa, prima, asegurable):
    cur.execute("""
        INSERT INTO cotizacion_detalle
            (id_cotizacion, id_empresa, tipo_riesgo, tasa, prima_anual, asegurable)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (id_cotizacion, id_empresa, tipo_riesgo, tasa, prima,
          1 if asegurable else 0))


def update_cotizacion_edicion(cur, id_cotizacion, nombre_cliente, dni_ruc,
                               placa, email, suma_asegurada, observaciones):
    cur.execute("""
        UPDATE cotizacion_guardada
        SET nombre_cliente      = %s,
            dni_ruc             = %s,
            placa               = %s,
            email               = %s,
            suma_asegurada      = %s,
            observaciones       = %s,
            editado_manualmente = 1
        WHERE id_cotizacion_guardada = %s
    """, (nombre_cliente, dni_ruc, placa, email,
          suma_asegurada, observaciones, id_cotizacion))


def update_prima_detalle(cur, id_cotizacion, id_empresa, prima):
    cur.execute("""
        UPDATE cotizacion_detalle
        SET prima_anual = %s, prima_editada = 1
        WHERE id_cotizacion = %s AND id_empresa = %s
    """, (prima, id_cotizacion, id_empresa))