from datetime import timedelta
from flask import Flask, session, redirect, url_for, request
from config import Config
from database import mysql

from controllers.auth         import bp as bp_auth
from controllers.index        import bp as bp_index
from controllers.vehiculos    import bp as bp_vehiculos
from controllers.tasas        import bp as bp_tasas
from controllers.clasificador import bp as bp_clasificador
from controllers.cotizador    import bp as bp_cotizador
from controllers.carga        import bp as bp_carga
from controllers.coberturas   import bp as bp_coberturas
from controllers.documento    import bp as bp_documento
from controllers.historial    import bp as bp_historial


# Rutas públicas que NO requieren login
RUTAS_PUBLICAS = {'auth.login', 'auth.logout', 'static'}

# Rutas que requieren rol admin (trabajador no puede acceder)
RUTAS_SOLO_ADMIN = {
    'index.index',
    'index.agregar_empresa',
    'index.editar_empresa',
    'index.agregar_tipo_riesgo',
    'index.editar_tipo_riesgo',
    'index.eliminar_tipo_riesgo',
    'index.agregar_asignacion',
    'index.editar_asignacion',
    'index.eliminar_asignacion',
    'vehiculos.agregar_modelo',
    'vehiculos.editar_modelo',
    'vehiculos.eliminar_modelo',
    'vehiculos.api_guardar_valores_modelo',
    'vehiculos.api_eliminar_valor',
    'tasas.tasas',
    'clasificador.clasificador_riesgos',
    'clasificador.agregar_regla',
    'clasificador.agregar_excepcion',
    'clasificador.eliminar_regla',
    'clasificador.eliminar_excepcion',
    'clasificador.eliminar_excepcion_pendiente',
    'clasificador.eliminar_regla_pendiente',
    'carga.carga',
    'carga.previsualizar',
    'carga.ejecutar',
    'coberturas.coberturas',
    'coberturas.guardar_coberturas',
    'coberturas.guardar_deducibles',
    'auth.admin_usuarios',
    'auth.crear_usuario',
    'auth.editar_usuario',
    'auth.cambiar_password',
    'auth.eliminar_usuario',
}


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Sesiones permanentes por 8 horas
    app.permanent_session_lifetime = timedelta(hours=8)

    mysql.init_app(app)

    # ── Registrar blueprints ──────────────────────────────────────────────────
    app.register_blueprint(bp_auth)
    app.register_blueprint(bp_index)
    app.register_blueprint(bp_vehiculos)
    app.register_blueprint(bp_tasas)
    app.register_blueprint(bp_clasificador)
    app.register_blueprint(bp_cotizador)
    app.register_blueprint(bp_carga)
    app.register_blueprint(bp_coberturas)
    app.register_blueprint(bp_documento)
    app.register_blueprint(bp_historial)

    # ── Protección global de rutas ────────────────────────────────────────────
    @app.before_request
    def verificar_acceso():
        endpoint = request.endpoint

        # Rutas públicas: siempre permitidas
        if not endpoint or endpoint in RUTAS_PUBLICAS:
            return

        # No logueado → redirigir al login
        if 'id_usuario' not in session:
            return redirect(url_for('auth.login', next=request.url))

        # Trabajador intentando acceder a ruta solo-admin
        if session.get('rol') == 'trabajador' and endpoint in RUTAS_SOLO_ADMIN:
            from flask import abort
            abort(403)

    # ── Página 403 personalizada ──────────────────────────────────────────────
    @app.errorhandler(403)
    def forbidden(e):
        from flask import render_template
        return render_template('403.html'), 403

    # ── Inyectar datos de sesión en todos los templates ───────────────────────
    @app.context_processor
    def inject_session():
        return {
            'session_username': session.get('username', ''),
            'session_rol':      session.get('rol', ''),
            'session_id':       session.get('id_usuario'),
        }

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
