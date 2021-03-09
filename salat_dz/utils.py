import os
import json
import logging
from datetime import datetime
from marshmallow.fields import Field
from pytz import timezone
from pathlib import Path

from flask_restx.fields import MarshallingError, Raw
from datetime import datetime, time
from webargs.core import ArgMap, Parser
from werkzeug.routing import BaseConverter, ValidationError
from geopy.geocoders import Nominatim
import pandas as pd

from .config import settings
from .reader import str_to_date

logger = logging.getLogger(__name__)


DZ = timezone('Africa/Algiers')
def today(tz=DZ):
    dt_now = datetime.now(tz=tz)
    today = dt_now.date()
    return today.isoformat()


def argmap_to_swagger_params(argmap: ArgMap, req=None):
    parser = Parser()
    schema = parser._get_schema(argmap, req)
    params = {}
    for name, field in schema.fields.items():
        params[name] = {
            'description': field.metadata.get('description', name.capitalize()),
            'type': field_to_type(field)
        }

    return params


def field_to_type(field: Field):
    # TODO: improve this by using OBJ_TYPE and num_type when available
    return field.__class__.__name__.lower()



def read_mawaqit_for_wilayas(directory):
    mawaqit_for_wilayas = {}
    for f in os.listdir(directory):
        path = os.path.join(directory, f)
        wilaya = Path(path).stem
        mawaqit_for_wilayas[wilaya] = pd.read_csv(path, index_col=False)

    return mawaqit_for_wilayas


def read_wilayas_values(path):
    # TODO: check names got from the json file and those from the pdfs
    with open(path) as f:
        wilayas = json.load(f)
    arabic_names = [w['arabic_name'] for w in wilayas]
    french_names = [w['french_name'] for w in wilayas]
    codes = [w['code'] for w in wilayas]
    accepted_values = arabic_names + french_names + codes
    return accepted_values
    


def create_mawaqits(mawaqit_for_wilayas, wilaya_column_name):
    dfs = []
    for wilaya, mawaqit in mawaqit_for_wilayas.items():
        mawaqit[wilaya_column_name] = wilaya
        dfs.append(mawaqit)

    mawaqits = pd.concat(dfs)

    mawaqits[settings.column_names.date] = mawaqits[settings.column_names.date].apply(str_to_date)
    mawaqits.index = mawaqits[settings.column_names.date]
    return mawaqits


class Time(Raw):
    """
    Return a formatted time string in %H:%M.
    """

    __schema_type__ = "string"
    __schema_format__ = "time"


    def __init__(self, time_format="%H:%M", **kwargs):
        super(Time, self).__init__(**kwargs)
        self.time_format = time_format


    def format(self, value):
        try:
            value = self.parse(value)
            if self.time_format == "iso":
                return value.isoformat()
            elif self.time_format:
                return value.strftime(self.time_format)
            else:
                raise MarshallingError("Unsupported time format %s" % self.time_format)
        except (AttributeError, ValueError) as e:
            raise MarshallingError(e)

    def parse(self, value):
        if isinstance(value, time):
            return value
        if isinstance(value, str):
            return time.fromisoformat(value)
        else:
            raise ValueError("Unsupported Time format")


def get_wilaya_from_geopos(latitude, longitude):
    geolocator = Nominatim(user_agent=settings.user_agent)
    address = geolocator.reverse(f'{latitude}, {longitude}')
    state = address.raw['address']['state']
    wilaya_ar = state.split()[-1]
    return wilaya_ar


def get_settings(key, language='ar'):
    if language == 'ar':
        language = ''

    if language:
        key = f'{key}_{language}'

    return getattr(settings, key, None)


def translate(name, from_='ar', to='en'):
    if from_ == to:
        return name

    settings_keys = ['column_names', 'salawat']
    translated = None
    for settings_key in settings_keys:
        settings_value = get_settings(settings_key, from_)
        # Make sure the settings_value is a dict
        try:
            dict(settings_value)
        except ValueError:
            logger.warning(f'translate: settings_value of {settings_key} is not dict')
            continue

        value_to_key = {value: key for key, value in settings_value.items()}
        if name in value_to_key:
            key = value_to_key[name]
            translation = get_settings(settings_key, to)
            if translation:
                translated = getattr(translation, key, None)
                break

    if not translated:
        logger.warning(f'Cannot translate {name} from {from_} to {to}')
    else:
        logger.info(f'{name} translated from {from_} to {to}: {translated}')

    return translated
