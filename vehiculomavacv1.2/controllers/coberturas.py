# =============================================================================
# controllers/coberturas.py
# Rutas: /coberturas
# =============================================================================

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from database import get_cursor, commit
import models.empresa as empresa_model
import models.cobertura as cobertura_model

bp = Blueprint('coberturas', __name__)

# Metadatos de campos (para labels y placeholders en el template)
CAMPOS_COBERTURA = [
    ('rc_terceros',       'RC frente a terceros',          'Ej: US$ 200,000.00'),
    ('rc_ocupantes',      'RC de ocupantes',               'Ej: US$ 100,000.00 Máximo por vehículo'),
    ('acc_muerte',        'Muerte c/u',                    'Ej: US$ 25,000.00'),
    ('acc_invalidez',     'Invalidez permanente c/u',      'Ej: US$ 25,000.00'),
    ('acc_curacion',      'Gastos de curación c/u',        'Ej: US$ 6,000.00'),
    ('acc_sepelio',       'Gastos de sepelio c/u',         'Ej: US$ 2,000.00'),
    ('acc_estetica',      'Cirugía estética c/u',          'Ej: No aplica / US$ 3,000.00'),
    ('gps',               'Requiere GPS',                  'Ej: SI / NO'),
    ('defensa_juridica',  'Defensa jurídica penal',        'Ej: SI'),
    ('auxilio_mecanico',  'Auxilio mecánico',              'Ej: SI - Ilimitado'),
    ('veh_reemplazo',     'Vehículo de reemplazo',         'Ej: SI (15 Pérdida / 30 Robo)'),
    ('chofer_reemplazo',  'Chofer de reemplazo',           'Ej: SI (5 eventos anuales)'),
    ('alcoholemia',       'Resultado alcoholemia',         'Ej: No exceda de 0.5 gr./lt'),
]

GRUPOS = [
    ('Responsabilidad Civil',           ['rc_terceros', 'rc_ocupantes']),
    ('Accidentes Personales Ocupantes', ['acc_muerte', 'acc_invalidez', 'acc_curacion',
                                         'acc_sepelio', 'acc_estetica']),
    ('Servicios',                       ['gps', 'defensa_juridica', 'auxilio_mecanico',
                                         'veh_reemplazo', 'chofer_reemplazo']),
    ('Otros',                           ['alcoholemia']),
]

CAMPOS_DEDUCIBLES = [
    ('deducible_evento',        'Deducible por evento (talleres)',  'Ej: 20% mínimo US$ 200.00'),
    ('deducible_taller',        'Red de talleres afiliados',        'Ej: Multimarca 15% mínimo US$ 150.00'),
    ('deducible_robo',          'Robo parcial',                     'Ej: 20% mínimo US$ 200.00'),
    ('deducible_musicales',     'Accesorios musicales',             'Ej: 10% mínimo US$ 150.00'),
    ('deducible_veh_reemplazo', 'Vehículo de reemplazo',            'Ej: US$ 90.00'),
    ('deducible_lunas',         'Lunas nacionales',                 'Ej: Sin deducible'),
    ('deducible_conductores',   'Conductores menores',              'Ej: No Aplica'),
]


@bp.route('/coberturas')
def coberturas():
    cur = get_cursor()
    empresas        = empresa_model.get_empresas_activas(cur)
    coberturas_dict = cobertura_model.get_todas_coberturas(cur)
    tipos_riesgo    = empresa_model.get_all_tipos_riesgo(cur)
    deducibles_dict = cobertura_model.get_todos_deducibles(cur)
    cur.close()

    return render_template('coberturas.html',
                           empresas=empresas,
                           coberturas_dict=coberturas_dict,
                           campos=CAMPOS_COBERTURA,
                           grupos=GRUPOS,
                           tipos_riesgo=tipos_riesgo,
                           deducibles_dict=deducibles_dict,
                           campos_deducibles=CAMPOS_DEDUCIBLES)


@bp.route('/coberturas/guardar/<int:id_empresa>', methods=['POST'])
def guardar_coberturas(id_empresa):
    cur = get_cursor()
    try:
        campos_nombres = [c[0] for c in CAMPOS_COBERTURA]
        valores = {campo: request.form.get(campo, '').strip() or None
                   for campo in campos_nombres}
        cobertura_model.upsert_coberturas_empresa(cur, id_empresa, valores)
        commit()
        flash('Coberturas actualizadas correctamente.', 'success')
    except Exception as e:
        flash(f'Error al guardar: {e}', 'danger')
    finally:
        cur.close()
    return redirect(url_for('coberturas.coberturas'))


@bp.route('/coberturas/guardar_deducibles/<int:id_empresa>', methods=['POST'])
def guardar_deducibles(id_empresa):
    cur = get_cursor()
    try:
        ids_tipo  = request.form.getlist('id_tipo_riesgo')
        campos_d  = [c[0] for c in CAMPOS_DEDUCIBLES]

        for i, id_tipo_riesgo in enumerate(ids_tipo):
            if not id_tipo_riesgo:
                continue
            valores = {}
            for campo in campos_d:
                val = request.form.getlist(campo)
                valores[campo] = val[i].strip() or None if i < len(val) else None

            cobertura_model.upsert_deducibles(cur, id_empresa, id_tipo_riesgo, valores)

        commit()
        flash('Deducibles actualizados correctamente.', 'success')
    except Exception as e:
        flash(f'Error al guardar deducibles: {e}', 'danger')
    finally:
        cur.close()
    return redirect(url_for('coberturas.coberturas'))


@bp.route('/api/coberturas_empresa/<int:id_empresa>')
def api_coberturas_empresa(id_empresa):
    cur = get_cursor()
    datos = cobertura_model.get_coberturas_empresa(cur, id_empresa)
    cur.close()
    return jsonify(datos)
