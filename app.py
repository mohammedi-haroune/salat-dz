from flask import Flask

from salat_dz.apiv1 import blueprint as apiv1

app = Flask(__name__)
app.register_blueprint(apiv1)
