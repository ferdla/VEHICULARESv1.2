# =============================================================================
# controllers/tasas.py
# Rutas: /tasas
# =============================================================================

from flask import Blueprint, render_template, request, jsonify
from database import get_cursor
import models.empresa as empresa_model
import models.tasa as tasa_model

bp = Blueprint('tasas', __name__)


@bp.route('/tasas')
def tasas():
    cur = get_cursor()

    empresa_id     = request.args.get('empresa_id', type=int)
    tipo_riesgo_id = request.args.get('tipo_riesgo_id', type=int)

    empresas     = empresa_model.get_empresas_activas(cur)
    tipos_riesgo = []
    tasas_data   = {}
    años_set     = set()

    if empresa_id:
        tipos_riesgo = empresa_model.get_tipos_riesgo_por_empresa(cur, empresa_id)
        filas = tasa_model.get_tasas_por_empresa(cur, empresa_id, tipo_riesgo_id)
        for tr_id, inicio, fin, es_0km, tasa in filas:
            key = (inicio, fin, es_0km)
            if key not in tasas_data:
                tasas_data[key] = {}
            tasas_data[key][tr_id] = tasa
            años_set.add(key)

    años_ordenados = sorted(años_set, key=lambda x: (-x[0], -x[2], -x[1]))
    años = []
    for inicio, fin, es_0km in años_ordenados:
        if es_0km:
            label = f"{inicio}-0km"
        elif inicio == fin:
            label = str(inicio)
        else:
            label = f"{inicio}-{fin}"
        años.append({'inicio': inicio, 'fin': fin, 'es_0km': es_0km, 'label': label})

    cur.close()
    return render_template('tasas.html',
                           empresas=empresas,
                           empresa_id=empresa_id,
                           tipos_riesgo=tipos_riesgo,
                           años=años,
                           tasas_data=tasas_data)


@bp.route('/api/tipos_riesgo_por_empresa/<int:empresa_id>')
def api_tipos_riesgo_por_empresa(empresa_id):
    cur = get_cursor()
    tipos = empresa_model.get_tipos_riesgo_por_empresa(cur, empresa_id)
    cur.close()
    return jsonify([{'id': r[0], 'nombre': r[1], 'codigo': r[2]} for r in tipos])
