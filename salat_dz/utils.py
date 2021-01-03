import os

from flask_restx.fields import MarshallingError, Raw
from datetime import time

import pandas as pd

def read_mawaqit_for_wilayas(directory):
    mawaqit_for_wilayas = {}
    for f in os.listdir(directory):
        [wilaya, _] = f.split('.')
        path = os.path.join(directory, f)
        mawaqit_for_wilayas[wilaya] = pd.read_csv(path, index_col=False)

    return mawaqit_for_wilayas


def append_wilaya_column(mawaqit_for_wilayas, wilaya_column_name):
    dfs = []
    for wilaya, mawaqit in mawaqit_for_wilayas.items():
        mawaqit[wilaya_column_name] = wilaya
        dfs.append(mawaqit)

    mawaqits = pd.concat(dfs)
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
