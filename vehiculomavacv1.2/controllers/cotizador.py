# =============================================================================
# controllers/cotizador.py
# Rutas: /cotizador
# =============================================================================

from flask import Blueprint, render_template, request, jsonify
from database import get_cursor
import models.vehiculo as vehiculo_model
from services.depreciacion import calcular_valor_vehiculo, AÑO_ACTUAL
from services.cotizacion import calcular_cotizacion

bp = Blueprint('cotizador', __name__)


@bp.route('/cotizador')
def cotizador():
    cur = get_cursor()
    marcas = vehiculo_model.get_all_marcas(cur)
    cur.close()
    return render_template('cotizador.html', marcas=marcas, AÑO_ACTUAL=AÑO_ACTUAL)


@bp.route('/api/valor_vehiculo', methods=['GET'])
def api_valor_vehiculo():
    id_modelo        = request.args.get('id_modelo', type=int)
    anio_fabricacion = request.args.get('anio', type=int)

    if not id_modelo or not anio_fabricacion:
        return jsonify({'error': 'Faltan parámetros'}), 400

    cur = get_cursor()
    resultado = calcular_valor_vehiculo(cur, id_modelo, anio_fabricacion)
    cur.close()
    return jsonify(resultado)


@bp.route('/api/cotizar', methods=['POST'])
def api_cotizar():
    data             = request.get_json()
    id_modelo        = data.get('id_modelo')
    anio_fabricacion = data.get('anio_fabricacion')
    suma_asegurada   = data.get('suma_asegurada')

    if not id_modelo or not anio_fabricacion:
        return jsonify({'error': 'Faltan datos obligatorios'}), 400
    if not suma_asegurada or float(suma_asegurada) <= 0:
        return jsonify({'error': 'La suma asegurada debe ser mayor a 0'}), 400

    cur = get_cursor()
    resultado = calcular_cotizacion(cur, id_modelo, anio_fabricacion, float(suma_asegurada))
    cur.close()
    return jsonify(resultado)
