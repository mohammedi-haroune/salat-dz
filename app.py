from flask import Flask, render_template
from flask_cors import CORS

from salat_dz.apiv1 import blueprint as apiv1
from salat_dz.apiv1 import wilayas_values

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.add_url_rule('/', 'index', lambda : render_template('index.html', wilayas=wilayas_values))
    app.register_blueprint(apiv1)
    return app

app = create_app()
