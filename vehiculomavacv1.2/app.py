from flask import Flask
from config import Config
from database import mysql

from controllers.index        import bp as bp_index
from controllers.vehiculos    import bp as bp_vehiculos
from controllers.tasas        import bp as bp_tasas
from controllers.clasificador import bp as bp_clasificador
from controllers.cotizador    import bp as bp_cotizador
from controllers.carga        import bp as bp_carga
from controllers.coberturas   import bp as bp_coberturas
from controllers.documento    import bp as bp_documento
from controllers.historial    import bp as bp_historial


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    mysql.init_app(app)

    app.register_blueprint(bp_index)
    app.register_blueprint(bp_vehiculos)
    app.register_blueprint(bp_tasas)
    app.register_blueprint(bp_clasificador)
    app.register_blueprint(bp_cotizador)
    app.register_blueprint(bp_carga)
    app.register_blueprint(bp_coberturas)
    app.register_blueprint(bp_documento)
    app.register_blueprint(bp_historial)

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
