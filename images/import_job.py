"""Take care of import jobs and copying files. Keep track of import modules"""

import logging, mimetypes, os
from threading import Thread, Event

from bottle import Bottle, auth_basic
from sqlalchemy.orm.exc import NoResultFound

from . import ImportJob, Location, Entry
from .database import get_db
from .types import PropertySet, Property
from .user import authenticate, no_guests
from .location import LocationDescriptor, get_locations_by_type
from .metadata import wrap_raw_json
from .entry import create_entry


################################################################################
# Import API


API = '/import'
api = Bottle()


@api.get('/')
@auth_basic(authenticate)
@no_guests()
def rest_get_importers():
    entries = []
    for location in get_locations_by_type(Location.Type.drop_folder).entries:
        entries.append({
            'location_id': location.id,
            'location_name': location.name,
            'trig_url': API + 'trig/%i' % location.id,
        })

    return {
        '*schema': 'ImporterFeed',
        'count': len(entries),
        'entries': entries,
    }


@api.get('/trig/<location_id:int>')
@auth_basic(authenticate)
@no_guests()
def rest_trig_import(location_id):
    manager = rest_trig_import.manager
    manager.trig(location_id)
    return {'result': 'ok'}


@api.get('/job')
@auth_basic(authenticate)
def rest_get_import_jobs():
    json = get_import_jobs().to_json()
    logging.info("Import Job feed\n%s", json)
    return json


################################################################################
# Import Module Handling

mime_map = {}

def register_import_module(mime_type, module):
    mime_map[mime_type] = module


def get_import_module(job_descriptor):
    import_module = mime_map.get(job_descriptor.mime_type, None)
    return import_module(job_descriptor) if import_module is not None else None


class GenericImportModule(object):
    def __init__(self, job_descriptor):
        self.job_descriptor = job_descriptor


################################################################################
# Import Job Descriptor


class ImportJobDescriptor(PropertySet):
    id = Property(int)
    path = Property()
    metadata = Property(ImportJob.DefaultImportJobMetadata)
    user_id = Property(int)
    location = Property(LocationDescriptor)

    mime_type = Property()

    @property
    def full_path(self):
        return os.path.join(self.location.get_root(), self.path)

    @property
    def filename(self):
        return os.path.basename(self.path)

    def analyse(self):
        self.mime_type = mimetypes.guess_type(self.full_path)[0]
        logging.debug("Guessed MIME Type '%s' for '%s'", self.mime_type, self.full_path)

    @classmethod
    def map_in(self, import_job):
        return ImportJobDescriptor(
            id=import_job.id,
            path=import_job.path,
            metadata=wrap_raw_json(import_job.data),
            user_id=import_job.user_id,
            location=LocationDescriptor.map_in(import_job.location),
        )

    def map_out(self, import_job):
        if self.id is not None: import_job.id = self.id
        import_job.path = self.path
        import_job.data = self.metadata.to_json() if self.metadata is not None else None
        import_job.user_id = self.user_id
        import_job.location_id = self.location.id if self.location is not None else None


class ImportJobDescriptorFeed(PropertySet):
    count = Property(int)
    entries = Property(list)


################################################################################
# Standard File Copyer Class


class FileCopy(object):
    def __init__(self, source, source_path, destination, dest_filename, link=False, keep_original=True, dest_folder=None):
        self.source = source
        self.source_path = source_path
        self.destination = destination
        self.link = link
        self.dest_filename = dest_filename
        self.keep_original = keep_original
        self.dest_folder = dest_folder
        self.destination_rel_path = None
        self.destination_full_path = None

    def run(self):
        if self.source:
            src = os.path.join(self.source.get_root(), self.source_path)
        else:
            src = self.source_path
        dst_folder = self.dest_folder or self.destination.suggest_folder()
        dst = os.path.join(dst_folder, self.dest_filename)
        try:
            os.makedirs(dst_folder)
        except FileExistsError as e:
            pass
        c = 0
        while True:
            try:
                if c:
                    postfix = '%i_' % c
                    dst_path, dst_ext = os.path.splitext(dst)
                    fixed_dst = ''.join([dst_path, '_%i' % c, dst_ext])
                else:
                    fixed_dst = dst
                if self.link:
                    logging.debug("Linking %s -> %s", src, fixed_dst)
                    os.link(src, fixed_dst)
                    self.destination_rel_path = os.path.relpath(fixed_dst, self.destination.get_root())
                    self.destination_full_path = fixed_dst
                else:
                    import shutil
                    logging.debug("Copying %s -> %s", src, fixed_dst)
                    shutil.copyfile(src, fixed_dst)
                    self.destination_rel_path = os.path.relpath(fixed_dst, self.destination.get_root())
                    self.destination_full_path = fixed_dst
                break
            except FileExistsError:
                c += 1

        if not self.keep_original:
            logging.debug("Removing original %s", src)
            os.remove(src)


################################################################################
# Internal Import API


def get_import_job_by_id(id):
    with get_db().transaction() as t:
        import_job = t.query(ImportJob).filter(
            ImportJob.id==id
        ).one()
        return ImportJobDescriptor.map_in(import_job)


def get_import_jobs():
    with get_db().transaction() as t:
        import_jobs = t.query(ImportJob).all()
        return ImportJobDescriptorFeed(
            count=len(import_jobs),
            entries=[ImportJobDescriptor.map_in(import_job) for import_job in import_jobs]
        )


def create_import_job(jd): # ImportJobDescriptor
    with get_db().transaction() as t:
        try:
            t.query(ImportJob).filter(
                ImportJob.location_id == jd.location.id,
                ImportJob.path == jd.path,
            ).one()
        except NoResultFound:
            logging.info("Creating Import Job for %i://%s",
                         jd.location.id,
                         jd.path
            )
            import_job = ImportJob()
            jd.map_out(import_job)
            t.add(import_job)


def pick_up_import_job(location_id):
    with get_db().transaction() as t:
        try:
            import_job = t.query(ImportJob).filter(
                ImportJob.location_id==location_id,
                ImportJob.state==ImportJob.State.new
            ).order_by(ImportJob.create_ts).first()
            if import_job is None:
                return None

            import_job.state = ImportJob.State.active
            return ImportJobDescriptor.map_in(import_job)

        except NoResultFound:
            return None


def fail_import_job(import_job_descriptor, reason):
    logging.error(reason)
    with get_db().transaction() as t:
        import_job = t.query(ImportJob).get(import_job_descriptor.id)
        import_job.state = ImportJob.State.failed
        metadata = wrap_raw_json(import_job.data) or ImportJob.DefaultImportJobMetadata()
        metadata.error = reason
        import_job.data = metadata.to_json()


def update_import_job_by_id(id, jd):
    with get_db().transaction() as t:
        import_job = t.query(ImportJob).filter(
            ImportJob.id==id
        ).one()
        jd.map_out(import_job)
    
    return get_import_job_by_id(id)

        

################################################################################
# Threaded Import Manager (Singleton)


class ImportManager(object):
    """
    A Thread+Event based Import Manager that keeps one thread per folder
    and trigs a new import round upon the trig method being called.

    There should only be one of these.
    """
    def __init__(self):
        self.events = {}
        rest_trig_import.manager = self

        for location in get_locations_by_type(Location.Type.drop_folder).entries:
            event = Event()
            self.events[location.id] = (event, location)
            thread = Thread(
                target=importing_loop,
                name="importer_%i" % (location.id),
                args=(event, location)
            )
            thread.daemon = True
            thread.start()

    def trig(self, location_id):
        event, _ = self.events.get(location_id, (None, None))
        if event is None:
            return
        event.set()
                

def importing_loop(import_event, location):
    """
    An import loop that will wait for import_event to be set
    each iteration.
    """
    metadata = location.metadata
    logging.info("Started importer thread for %i:%s", location.id, metadata.folder)
    while True:
        import_event.wait(30)
        import_event.clear()

        while True:
            jd = pick_up_import_job(location.id)

            if jd is None:
                break

            logging.debug("ImportJobDescriptor:\n%s", jd.to_json())

            jd.analyse()
            import_module = get_import_module(jd)

            if import_module is None:
                fail_import_job(jd, 
                    "Could not find a suitable import module for MIME Type %s" % jd.mime_type
                )
                continue

            try:
                import_module.run()
            except Exception as e:
                fail_import_job(jd, 
                    "Import failed %s" % str(e)
                )
                continue

            ed = import_module.entry
            logging.debug("EntryDescriptor:\n%s", ed.to_json())
            
            ed.state = Entry.State.online
            create_entry(ed)

            jd.state = ImportJob.State.done
            update_import_job_by_id(jd.id, jd)
            logging.info("Import Job Done %s", jd.path)
