from datetime import date, datetime, time
from functools import partial
import logging

from flask import Blueprint, Flask, abort
from flask_restx import Api, Resource
from flask_restx.fields import Date, String, Nested
import pandas as pd
from pytz import timezone
from webargs import fields, validate
from webargs.flaskparser import parser, use_kwargs

from .config import settings
from .utils import (
    Time,
    argmap_to_swagger_params,
    create_mawaqits_v2,
    get_wilaya,
    read_mawaqit_for_wilayas_v2,
    read_wilayas,
    get_wilayas_values,
    translate,
)

logger = logging.getLogger(__name__)

DZ = timezone('Africa/Algiers')

mawaqit_for_wilayas = read_mawaqit_for_wilayas_v2(settings.mawaqit_for_wilayas_dir)
mawaqits = create_mawaqits_v2(mawaqit_for_wilayas, settings.column_names.wilaya)
# TODO: first check the names scrapped from wikipedia with thoese extracted from the pdfs
# wilayas_values = read_wilayas_values(settings.wilayas_file)
# wilayas_values = list(mawaqit_for_wilayas.keys())
wilayas = read_wilayas()
wilayas_values = get_wilayas_values(wilayas)
salawat_values = settings.salawat_names + settings.salawat_names_en



blueprint = Blueprint('apiv2', __name__, url_prefix='/api/v2')

api = Api(
    blueprint,
    version='2.0',
    title=settings.api.title,
    description=settings.api.description,
)

ns = api.namespace('mawaqit', description='Provides Mawaqit')

mawaqit = api.model('Mawaqit', {
    settings.column_names_en.date: Date(),
    settings.column_names_en.wilaya: Nested(api.model('Wilaya', {
        'code': String(),
        'arabic_name': String(),
        'english_name': String(),
    })),
    settings.salawat_en.fajr: Time(),
    settings.salawat_en.chorok: Time(),
    settings.salawat_en.dhohr: Time(),
    settings.salawat_en.asr: Time(),
    settings.salawat_en.maghrib: Time(),
    settings.salawat_en.icha: Time(),
})

# TODO: add validation to say: day and (from and to) are mutually execlusive
"""
Time filtering: 
* If no time filter is speified, mawaqait of the current date will be returned
* You can filter time in various ways:
    - Interval: use `from` and `to` parameters
    - Specific days: use `days` parameter
    - Number of days starting from a date (today by default): `n_days`
    - Number of weeks starting from a date (today by default): `n_weeks`
        If both `n_days` and `n_weeks` are specified, the duration will be added
"""
args = {
    'from_': fields.Date(data_key='from', metadata={'description': 'Where to start'}, missing=None),
    'to': fields.Date(metadata={'description': 'Where to end'}, missing=None),
    'days': fields.DelimitedList(fields.Date(), missing=None),
    'n_days': fields.TimeDelta(precision='days', missing=None),
    'n_weeks': fields.TimeDelta(precision='weeks', missing=None),
    'wilayas': fields.DelimitedList(fields.Str(validate=validate.OneOf(wilayas_values)), missing=None),
    'salawat': fields.DelimitedList(fields.Str(validate=validate.OneOf(salawat_values)), missing=None),
    # TODO: Add latitude and longitude
    # TODO: add english salawat names
}
# TODO: add the query parameters to the swagger ui, see: 
# - this comment: https://github.com/noirbizarre/flask-restplus/issues/772#issuecomment-579204883
# - @api.expect decorator: https://flask-restx.readthedocs.io/en/latest/swagger.html#the-api-expect-decorator
# - webargs: https://webargs.readthedocs.io/en/latest/
# - webargs flask-restful example: https://github.com/marshmallow-code/webargs/blob/dev/examples/flaskrestful_example.py
# TODO: example is not rendered in the swagger ui
# TODO: What type to use for fields.DelimitedList ?

# def validate_args(from_, to, days, n_days, n_weeks, wilayas, salawat):
#     interval = from_ and (to or n_days or n_weeks)


@parser.error_handler
def handle_request_parsing_error(err, req, schema, *, error_status_code, error_headers):
    logger.error(f'Parsing error: {err.messages} during request={req} with schema={schema}, error_status_code={error_status_code}')
    abort(400, err.messages)


def list_mawaqit(from_, to, days, n_days, n_weeks, wilayas, salawat, language='ar'):
    '''List mawaqits'''
    print(f'Calling with {locals()}')
    query = mawaqits

    today = datetime.now(tz=DZ).date()
    # from_, to, page, limit = parse_common_args(request)
    if not from_:
        from_ = today

    # TODO: Move it! Move it! to postprocess
    if not to:
        if n_days or n_weeks:
            dt_from = datetime.combine(from_, time())
            dt_to = dt_from + n_weeks + n_days
            to = dt_to.date
        else:
            to = today

    # Time Filtering
    if days:
        query = query[query[settings.column_names.date].isin(days)]
    elif from_ == to == today:
        query = query[query[settings.column_names.date] == today]
    elif from_:
        query = query[from_ <= query[settings.column_names.date]]
    elif to:
        query = query[query[settings.column_names.date] <= to]

    # Filter wilayas
    if wilayas:
        queries = []
        for code_or_name in wilayas:
            wilaya = get_wilaya(code_or_name)
            queries.append(query[query[settings.column_names.wilaya] == wilaya])
        query = pd.concat(queries)

    # TODO: paginate result
    query = query.head()

    # Translate the result
    translate_ = partial(translate, to=language)
    query = query.rename(columns=translate_)

    return query.to_dict('records')


@ns.route(f'/')
class MawaqitList(Resource):
    '''Shows a list of all mawaqits'''
    @use_kwargs(args, location='query')
    @ns.doc('list_mawaqits', params=argmap_to_swagger_params(args))
    @ns.marshal_list_with(mawaqit)
    def get(self, from_, to, days, n_days, n_weeks, wilayas, salawat):
        return list_mawaqit(
            from_=from_,
            to=to,
            days=days,
            n_days=n_days,
            n_weeks=n_weeks,
            wilayas=wilayas,
            salawat=salawat,
            language='en',
        )
