import os
import json
from datetime import datetime
from marshmallow.fields import Field
from pytz import timezone
from pathlib import Path

from flask_restx.fields import MarshallingError, Raw
from datetime import datetime, time
from webargs.core import ArgMap, Parser
from werkzeug.routing import BaseConverter, ValidationError

import pandas as pd

from .config import settings
from .reader import str_to_date


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
