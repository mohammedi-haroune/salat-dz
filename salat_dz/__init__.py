from flask import Flask, url_for, redirect

from .apiv1 import blueprint as apiv1

def create_app():
    app = Flask(__name__)
    app.add_url_rule('/', 'index', lambda : redirect(url_for('apiv1.root')))
    app.register_blueprint(apiv1)
    return app
