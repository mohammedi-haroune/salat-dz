from flask import Flask, render_template

from salat_dz.apiv1 import blueprint as apiv1

def create_app():
    app = Flask(__name__)
    app.add_url_rule('/', 'index', lambda : render_template('index.html'))
    app.register_blueprint(apiv1)
    return app

app = create_app()
