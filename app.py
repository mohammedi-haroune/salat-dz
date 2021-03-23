from flask import Flask
from flask_cors import CORS

from salat_dz.apiv1 import blueprint as apiv1
from salat_dz.apiv2 import blueprint as apiv2
from salat_dz.base import blueprint as base


def register_blueprints(app):
    app.register_blueprint(apiv1)
    app.register_blueprint(apiv2)
    app.register_blueprint(base)
    return app


def register_extensions(app):
    CORS(app)
    return app


def create_app():
    app = Flask(__name__)
    app = register_blueprints(app)
    app = register_extensions(app)
    return app

app = create_app()
