from flask import Flask
from flask_restx import Resource, Api
from flask_restx.fields import Date, String

from .utils import Time, read_mawaqit_for_wilayas, append_wilaya_column
from .config import settings

mawaqit_for_wilayas = read_mawaqit_for_wilayas(settings.mawaqit_for_wilayas_dir)
mawaqits = append_wilaya_column(mawaqit_for_wilayas, settings.column_names.wilaya)

app = Flask(__name__)
api = Api(app, version='1.0', title=settings.api.title, description=settings.api.description)


ns = api.namespace('mawaqit', description='Provides Mawaqit')

mawaqit = api.model('Mawaqit', {
    settings.column_names.date: Date(),
    settings.column_names.wilaya: String(),
    settings.salawat.fajr: Time(),
    settings.salawat.chorok: Time(),
    settings.salawat.dhohr: Time(),
    settings.salawat.asr: Time(),
    settings.salawat.maghrib: Time(),
    settings.salawat.icha: Time(),
})

@ns.route('/')
class MawaqitList(Resource):
    '''Shows a list of all mawaqits, and lets you POST to add new tasks'''
    @ns.doc('list_mawaqits')
    @ns.marshal_list_with(mawaqit)
    def get(self):
        '''List all tasks'''
        global mawaqits
        mawaqits = mawaqits.head()
        return mawaqits.to_dict('records')


@ns.route('/<string:wilaya>')
@ns.response(404, 'Mawaqit not found')
@ns.param('wilaya', 'The name of the wilaya')
class Mawaqit(Resource):
    '''Show a single mawaqit item and lets you delete them'''
    @ns.doc('get_mawaqit')
    @ns.marshal_with(mawaqit)
    def get(self, wilaya):
        '''Fetch a given resource'''
        mawaqit = mawaqit_for_wilayas[wilaya]
        mawaqit[settings.column_names.wilaya] = wilaya
        mawaqit = mawaqit.head()
        response = mawaqit.to_dict('records')
        return response


if __name__ == '__main__':
    app.run(debug=True)
