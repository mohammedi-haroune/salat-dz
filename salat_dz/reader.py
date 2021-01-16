from collections import defaultdict
import re
import os
import logging
from datetime import date, time, datetime, timedelta
from typing import Dict, Iterable, Tuple, TypeVar, Union

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
    if s == '03-09-2020':
        s = '2020-09-03'
    return date.fromisoformat(s.replace('/', '-'))


def preprocess_mawaqit(mawaqit: pd.DataFrame) -> pd.DataFrame:
    logger.debug('Preprocessing mawaqit')
    assert mawaqit.shape == (29, 8) or mawaqit.shape == (30, 8), f'Mawaqit DataFrame should be of shape (29, 8) or (30, 8) not {mawaqit.shape}\n{mawaqit}'
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


def timedelta_from_minutes(minutes: Union[int, str]) -> timedelta:
    return timedelta(minutes=int(minutes))


def preprocess_diffs(diffs: pd.DataFrame) -> pd.DataFrame:
    logger.debug('Preprocessing diffs')
    [diff_column] = [c for c in diffs.columns if settings.column_names.diff in c]
    salawat_names = diffs[diff_column].values.tolist()
    diffs = diffs.drop(diff_column, axis=1)
    diffs.index = salawat_names
    diffs = diffs.applymap(timedelta_from_minutes)
    diffs = diffs.reindex(settings.salawat_names, axis=0)
    return diffs


def preprocess_diffs_adrar(diffs: pd.DataFrame) -> Dict[tuple, pd.DataFrame]:
    """Addrar's diffs tables is splitted to two tables"""
    def fix_column_name(c1: str, c2: str) -> str:
        """Remove Unamed: number and number. added by pd.DataFrame when reading the pdf"""
        if 'Unnamed:' in c1:
            c1 = ''
        if re.match(r'.*\.\d+', c1):
            c1 = re.sub(r'\.\d+', '', c1)

        if c1 != '':
            return c1 + ' ' + c2
        else:
            return c2

    assert diffs.shape == (7, 35) or diffs.shape == (7, 34), f'Diffs DataFrame should be of shape (7, 35) or (7, 34) not {diffs.shape}\nfirst_row={diffs.iloc[0].values.tolist()}\ncolumns{diffs.columns.values.tolist()}\n{diffs}'

    fixed_columns = []
    columns = diffs.columns[:17]
    first_row = diffs.iloc[0][:17]
    for c1, c2 in zip(columns, first_row):
        fixed_columns.append(fix_column_name(c1, c2))
    
    diffs = diffs.iloc[1:]

    part1 = diffs[diffs.columns[:17]]
    if diffs.shape[1] == 35:
        part2 = diffs[diffs.columns[18:]]
    else:
        part2 = diffs[diffs.columns[17:]]

    part1.columns = fixed_columns
    part2.columns = fixed_columns

    part1 = preprocess_diffs(part1)
    part2 = preprocess_diffs(part2)
    diffs_map = {
        (0, 15): part1,
        (15, 30): part2,
    }
    return diffs_map


def preprocess_diffs_default(diffs: pd.DataFrame) -> Dict[tuple, pd.DataFrame]:
    return { (0, 30): preprocess_diffs(diffs) }


DIFFS_PREPROCESSORS = {
    settings.regions.djelfa: preprocess_diffs_default,
    settings.regions.alger: preprocess_diffs_default,
    settings.regions.adrar: preprocess_diffs_adrar,
}


def add_region_to_diffs(diffs: pd.DataFrame, region: str) -> pd.DataFrame:
    diffs[region] = [timedelta()] * 6
    return diffs

def construct_mawaqit_for_wilayas(tables: list, region: str) -> dict:
    mawaqit_for_wilayas = {}
    for mawaqit, diffs in grouped(tables, 2):
        mawaqit = preprocess_mawaqit(mawaqit)
        diffs_preprocessor = DIFFS_PREPROCESSORS[region]
        diffs_map = diffs_preprocessor(diffs)
        for (from_, to), diffs in diffs_map.items():
            mawaqit_from_to = mawaqit.iloc[from_: to]
            diffs = add_region_to_diffs(diffs, region)
            for wilaya, diff in diffs.iteritems():
                logger.debug(f'Processing wilaya {wilaya:12s} from {mawaqit_from_to.index.min()} to {mawaqit_from_to.index.max()}')
                mawaqit_wilaya = mawaqit_from_to.apply(lambda row: row.combine(diff, time_plus_timedelta), axis=1)
                if wilaya in mawaqit_for_wilayas:
                    mawaqit_for_wilayas[wilaya] = pd.concat((mawaqit_for_wilayas[wilaya], mawaqit_wilaya))
                else:
                    mawaqit_for_wilayas[wilaya] = mawaqit_wilaya

    return mawaqit_for_wilayas




def export_mawaqit_for_wilayas(mawaqit_for_wilayas):
    for wilaya, mawaqit_for_wilaya in mawaqit_for_wilayas.items():
        path = os.path.join(settings.mawaqit_for_wilayas_dir, f'{wilaya}.csv')
        mawaqit_for_wilaya.to_csv(path)

def check_dates(dates):
    # TODO: check len(dates) = 356 which means the data contains the whole year
    for i in range(len(dates)-1):
        oneday = timedelta(days=1)
        td = dates[i+1] - dates[i]
        if td != oneday :
            logger.error(f'{dates[i]} and {dates[i+1]} are not consecutif ({td})')
            

def run(region, pdf, template):
    logger.debug(f'Start reading for region {region} from {pdf} with template {template}')
    tables = tabula.read_pdf_with_template(pdf, template, stream=True)
    mawaqit_for_wilayas = construct_mawaqit_for_wilayas(tables, region=region)
    for wilaya, mawaqit in mawaqit_for_wilayas.items():
        logger.debug(f'Checking dates for {wilaya}')
        check_dates(mawaqit.index)
    logger.debug(f'Exporting wilayas {list(mawaqit_for_wilayas.keys())} to {settings.mawaqit_for_wilayas_dir}')

    export_mawaqit_for_wilayas(mawaqit_for_wilayas)
    logger.debug(f'Reading from {pdf} finished succesfully')


def main():
    logging.basicConfig(level=logging.DEBUG)
    run(settings.regions.djelfa, settings.pdf_paths.djelfa, settings.tabula_templates.djelfa)
    run(settings.regions.alger, settings.pdf_paths.alger, settings.tabula_templates.alger)
    run(settings.regions.adrar, settings.pdf_paths.adrar, settings.tabula_templates.adrar)

if __name__ == '__main__':
    main()
