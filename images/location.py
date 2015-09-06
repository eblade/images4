
import logging, datetime, os

from . import api, Location
from bottle import Bottle, auth_basic, static_file
from .types import PropertySet, Property
from .user import authenticate
from .database import get_db
from .metadata import wrap_raw_json


################################################################################
# Location BASE


BASE = '/location'
app = Bottle()
api.register(BASE, app)


@app.get('/')
@auth_basic(authenticate)
def rest_get_locations():
    json = get_locations().to_json()
    logging.info("Import Job feed\n%s", json)
    return json


@app.get('/<location_id>/dl/<path:path>')
@auth_basic(authenticate)
def rest_download(location_id, path):
    location = get_location_by_id(location_id)
    return static_file(path, root=location.metadata.folder)


def get_download_url(location_id, path):
    """
    Return a physical download url for a file on a location.
    """
    return "%s/%i/dl/%s" % (BASE, location_id, path)

api.url().location += get_download_url


################################################################################
# Location Descriptor


class LocationDescriptor(PropertySet):

    type = Property(enum=Location.Type)
    id = Property()
    name = Property()
    metadata = Property(wrap=True)

    trig_scan_url = Property()
    trig_import_url = Property()

    def __repr__(self):
        if self.id:
            return '<LocationDescriptor %i %s [%s]>' % (self.id or 0, self.name, self.type.name)
        else:
            return '<LocationDescriptor>'

    def suggest_folder(self, **hints):
        folder = self.metadata.folder
        if 'date' not in hints:
            hints['date'] = datetime.date.today().isoformat()
        subfolder = self.metadata.subfolder.format(**hints)
        return os.path.join(folder, subfolder)

    def get_root(self):
        return self.metadata.folder

    def calculate_urls(self):
        self.self_url = '%s/%i' % (BASE, self.id)
        if self.type is Location.Type.drop_folder:
            self.trig_scan_url = api.url().scanner.get_trig_url(self.id)
        if self.type in (Location.Type.drop_folder, Location.Type.upload):
            self.trig_import_url = api.url().import_job.get_trig_url(self.id)

    @classmethod
    def map_in(self, location):
        ld = LocationDescriptor( 
            id=location.id,
            type=Location.Type(location.type),
            name=location.name,
            metadata=wrap_raw_json(location.data),
        )
        ld.calculate_urls()
        return ld


class LocationDescriptorFeed(PropertySet):
    count = Property(int)
    entries = Property(list)


################################################################################
# Location Internal API


def get_location_by_id(id):
    with get_db().transaction() as t:
        location = t.query(Location).filter(Location.id==id).one()
        return LocationDescriptor.map_in(location)


def get_locations_by_type(*types):
    with get_db().transaction() as t:
        locations = t.query(Location).filter(Location.type.in_(types)).all()
        return LocationDescriptorFeed(
            count=len(locations),
            entries=[LocationDescriptor.map_in(location) for location in locations]
        )


def get_location_by_type(type):
    locations = get_locations_by_type(type)
    return locations.entries[0]


def get_locations():
    with get_db().transaction() as t:
        locations = t.query(Location).all()

        return LocationDescriptorFeed(
            count=len(locations),
            entries=[LocationDescriptor.map_in(location) for location in locations]
        )
