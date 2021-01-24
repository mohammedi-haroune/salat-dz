import logging
import warnings
from flask import Blueprint, render_template, request, make_response
from datetime import datetime, timedelta
from webargs.flaskparser import parser
from webargs import fields, validate
from marshmallow import Schema, pre_load


from .apiv1 import wilayas_values


blueprint = Blueprint('base', __name__)

logger = logging.getLogger(__name__)


class WilayaArg(Schema):
    wilaya = fields.Str(validate=validate.OneOf(wilayas_values))
    @pre_load
    def handle_multi_word_wilaya(self, in_data, **kwargs):
        out_data = {**in_data}
        warnings.warn('Hacking ..., check why multi word wilayas have two spaces')
        out_data['wilaya'] = out_data['wilaya'].replace(' ', '  ')
        return out_data


@blueprint.route('/')
def index():
    saved_wilaya = request.cookies.get('wilaya')
    return render_template('index.html', wilayas=wilayas_values, saved_wilaya=saved_wilaya)


@blueprint.route('/save')
@parser.use_kwargs(WilayaArg, location="query")
def save_wilaya(wilaya):
    logger.debug(f'Saving wilaya {wilaya}')
    response = make_response()
    experies = datetime.now() + timedelta(days=365)
    response.set_cookie('wilaya', wilaya, expires=experies)
    return response
