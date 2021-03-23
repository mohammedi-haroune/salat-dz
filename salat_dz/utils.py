from operator import itemgetter
import os
import json
import logging
from datetime import datetime
from typing import Iterable, List
from marshmallow.fields import Field
from pytz import timezone
from pathlib import Path

from flask_restx.fields import MarshallingError, Raw
from datetime import datetime, time
from webargs.core import ArgMap, Parser
from werkzeug.routing import BaseConverter, ValidationError
from geopy.geocoders import Nominatim
import pandas as pd
import Levenshtein as lev

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


def read_wilayas():
    with open(settings.wilayas_file) as f:
        return json.load(f)


def get_wilaya(code_or_name: str, wilayas: Iterable[dict] = None):
    if wilayas is None:
        wilayas = read_wilayas()

    # convert the names found in the ministry PDFs to the ones found on wikipedia
    if code_or_name in settings.rename:
        code_or_name = settings.rename.get(code_or_name)

    for wilaya in wilayas:
        # TODO: don't stric compare, use a less rigirous way to handle the naming
        # diffrences between data got from marw.dz and the one got from wikipedia.com
        if code_or_name in wilaya.values():
            return wilaya

    return {
        'code': code_or_name,
        'arabic_name': code_or_name,
        'english_name': code_or_name,
    }


def look_for_rename(old_names: List[str], wilayas: Iterable[dict], path: str):
    rename = {}
    for old_name in old_names:
        closest_name, _ = best_match(old_name, [wilaya['arabic_name'] for wilaya in wilayas])
        rename[old_name] = closest_name

    with open(path, 'w') as f:
        output = 'rename:\n'
        for x1, x2 in rename.items():
            output = output + f"  '{x1}': '{x2}'\n"
        f.write(output)


def best_match(name: str, names: Iterable[str]):
    distances = []
    for other_name in names:
        distance = lev.distance(name, other_name)
        distances.append((other_name, distance))

    best, minimum_distance = min(distances, key=itemgetter(1))
    return best, minimum_distance



def read_mawaqit_for_wilayas_v2(directory):
    mawaqit_for_wilayas = []
    for f in os.listdir(directory):
        path = os.path.join(directory, f)
        arabic_name = Path(path).stem

        wilaya = get_wilaya(arabic_name)

        mawaqit_for_wilayas.append((wilaya, pd.read_csv(path, index_col=False)))
       
    return mawaqit_for_wilayas


def get_wilayas_values(wilayas):
    arabic_names = [w['arabic_name'] for w in wilayas]
    french_names = [w['english_name'] for w in wilayas]
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


def create_mawaqits_v2(mawaqit_for_wilayas, wilaya_column_name):
    dfs = []
    for wilaya, mawaqit in mawaqit_for_wilayas:
        mawaqit[wilaya_column_name] = [wilaya]*len(mawaqit)
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
