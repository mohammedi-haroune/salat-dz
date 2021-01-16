
import os
import logging
from datetime import date, time, datetime, timedelta
from typing import Iterable, Tuple, TypeVar

import tabula
import pandas as pd

from .config import settings


T = TypeVar("T")

logger = logging.getLogger('reader')

def grouped(iterable: Iterable[T], n=2) -> Iterable[Tuple[T, ...]]:
    """s -> (s0,s1,s2,...sn-1), (sn,sn+1,sn+2,...s2n-1), ..."""
    return zip(*[iter(iterable)] * n)


def str_to_date(s):
    # in the djelfa.pdf there a typo in this day, see page number 10
    if s == '2020-04-17':
        s = '2021-04-17'
    return date.fromisoformat(s.replace('/', '-'))


def preprocess_mawaqit(mawaqit: pd.DataFrame) -> pd.DataFrame:
    logger.debug('Preprocessing mawaqit')
    mawaqit.index = mawaqit[settings.column_names.date].apply(str_to_date)
    mawaqit = mawaqit.drop(settings.column_names.date, axis=1)
    mawaqit = mawaqit.drop(settings.column_names.qibla, axis=1)
    mawaqit = mawaqit.rename(columns={settings.column_names.zawal: settings.column_names.dhohr})
    mawaqit = mawaqit.applymap(time.fromisoformat)
    mawaqit = mawaqit.reindex(settings.salawat_names, axis=1)
    return mawaqit


def time_plus_timedelta(t: time, td: timedelta) -> timedelta:
    dt = datetime.combine(date.today(), t)
    dt = dt + td
    return dt.time()


def timedelta_from_minutes(minutes: int) -> timedelta:
    return timedelta(minutes=minutes)


def construct_mawaqit_for_wilayas(tables: list) -> dict:
    mawaqit_for_wilayas = {}
    for mawaqit, diffs in grouped(tables, 2):
        diffs = preprocess_diffs(diffs)
        mawaqit = preprocess_mawaqit(mawaqit)
        for wilaya, diff in diffs.iteritems():
            logger.debug(f'Processing wilaya {wilaya:12s} from {mawaqit.index.min()} to {mawaqit.index.max()}')
            mawaqit_wilaya = mawaqit.apply(lambda row: row.combine(diff, time_plus_timedelta), axis=1)
            if wilaya in mawaqit_for_wilayas:
                mawaqit_for_wilayas[wilaya] = pd.concat((mawaqit_for_wilayas[wilaya], mawaqit_wilaya))
            else:
                mawaqit_for_wilayas[wilaya] = mawaqit_wilaya
    return mawaqit_for_wilayas

def preprocess_diffs(diffs: pd.DataFrame) -> pd.DataFrame:
    logger.debug('Preprocessing diffs')
    [diff_column] = [c for c in diffs.columns if settings.column_names.diff in c]
    salawat_names = diffs[diff_column].values.tolist()
    diffs = diffs.drop(diff_column, axis=1)
    diffs.index = salawat_names
    diffs = diffs.applymap(timedelta_from_minutes)
    diffs = diffs.reindex(settings.salawat_names, axis=0)
    return diffs


def export_mawaqit_for_wilayas(mawaqit_for_wilayas):
    for wilaya, mawaqit_for_wilaya in mawaqit_for_wilayas.items():
        path = os.path.join(settings.mawaqit_for_wilayas_dir, f'{wilaya}.csv')
        mawaqit_for_wilaya.to_csv(path)


def main():
    logging.basicConfig(level=logging.DEBUG)
    logger.debug(f'Start reading from {settings.pdf_paths.djelfa} with template {settings.tabula_template}')
    tables = tabula.read_pdf_with_template(settings.pdf_paths.djelfa, settings.tabula_template, stream=True)
    mawaqit_for_wilayas = construct_mawaqit_for_wilayas(tables)
    logger.debug(f'Exporting wilayas {list(mawaqit_for_wilayas.keys())} to {settings.mawaqit_for_wilayas_dir}')
    export_mawaqit_for_wilayas(mawaqit_for_wilayas)
    logger.debug(f'Reading from {settings.pdf_paths.djelfa} finished succesfully')

if __name__ == '__main__':
    main()
