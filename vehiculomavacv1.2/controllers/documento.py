# =============================================================================
# controllers/documento.py
# Rutas: /documento
# =============================================================================

from flask import Blueprint, render_template, request, jsonify
from database import get_cursor, commit, rollback
import models.cotizacion as cotizacion_model
import models.cobertura as cobertura_model

bp = Blueprint('documento', __name__)


@bp.route('/documento/cotizacion/<int:id_cotizacion>')
def ver_documento(id_cotizacion):
    cur = get_cursor()

    cot = cotizacion_model.get_cotizacion_completa(cur, id_cotizacion)
    if not cot:
        cur.close()
        return "Cotización no encontrada", 404

    (id_cot, numero, fecha, nombre_cliente, dni_ruc, placa, email,
     suma_asegurada, editado, observaciones,
     nombre_modelo, nombre_marca, anio_fabricacion) = cot

    detalles = []
    for row in cotizacion_model.get_detalles_cotizacion(cur, id_cot):
        id_emp, nombre_emp, tipo_riesgo, tasa, prima, prima_editada, asegurable = row

        coberturas = cobertura_model.get_coberturas_empresa(cur, id_emp)
        deducibles = cobertura_model.get_deducibles_por_empresa(cur, id_emp, tipo_riesgo) \
                     if asegurable else None

        detalles.append({
            'id_empresa':    id_emp,
            'empresa':       nombre_emp,
            'tipo_riesgo':   tipo_riesgo or 'No Asegurable',
            'tasa':          float(tasa)  if tasa  else None,
            'prima':         float(prima) if prima else None,
            'prima_editada': prima_editada,
            'asegurable':    bool(asegurable),
            'coberturas':    coberturas,
            'deducibles':    deducibles,
        })

    cur.close()

    return render_template('documento_cotizacion.html',
        numero=numero,
        fecha=fecha.strftime('%d/%m/%Y') if fecha else '',
        nombre_cliente=nombre_cliente or '',
        dni_ruc=dni_ruc or '',
        placa=placa or '',
        email=email or '',
        suma_asegurada=float(suma_asegurada),
        nombre_modelo=nombre_modelo,
        nombre_marca=nombre_marca,
        anio_fabricacion=anio_fabricacion,
        editado=editado,
        observaciones=observaciones or '',
        detalles=detalles,
        id_cotizacion=id_cot,
    )


@bp.route('/api/guardar_cotizacion', methods=['POST'])
def guardar_cotizacion():
    data = request.get_json()

    id_modelo        = data.get('id_modelo')
    anio_fabricacion = data.get('anio_fabricacion')
    suma_asegurada   = data.get('suma_asegurada')
    resultados       = data.get('resultados', [])

    if not id_modelo or not anio_fabricacion or not suma_asegurada:
        return jsonify({'error': 'Faltan datos obligatorios'}), 400

    cur = get_cursor()
    try:
        numero = cotizacion_model.generar_numero_cotizacion(cur)

        cotizacion_model.insert_cotizacion(
            cur, numero,
            data.get('nombre_cliente', ''),
            data.get('dni_ruc', ''),
            data.get('placa', ''),
            data.get('email', ''),
            id_modelo, anio_fabricacion, suma_asegurada
        )
        commit()

        cur.execute("SELECT LAST_INSERT_ID()")
        id_cot = cur.fetchone()[0]

        for r in resultados:
            cotizacion_model.insert_detalle_cotizacion(
                cur, id_cot, r['id_empresa'],
                r.get('tipo_riesgo'), r.get('tasa'), r.get('prima'),
                r.get('asegurable')
            )
        commit()
        cur.close()
        return jsonify({'ok': True, 'id_cotizacion': id_cot, 'numero': numero})

    except Exception as e:
        rollback()
        cur.close()
        return jsonify({'error': str(e)}), 500


@bp.route('/api/guardar_edicion/<int:id_cotizacion>', methods=['POST'])
def guardar_edicion(id_cotizacion):
    data = request.get_json()
    cur  = get_cursor()
    try:
        cotizacion_model.update_cotizacion_edicion(
            cur, id_cotizacion,
            data.get('nombre_cliente'),
            data.get('dni_ruc'),
            data.get('placa'),
            data.get('email'),
            data.get('suma_asegurada'),
            data.get('observaciones'),
        )
        for item in data.get('primas', []):
            cotizacion_model.update_prima_detalle(
                cur, id_cotizacion, item['id_empresa'], item['prima']
            )
        commit()
        cur.close()
        return jsonify({'ok': True})

    except Exception as e:
        rollback()
        cur.close()
        return jsonify({'error': str(e)}), 500
