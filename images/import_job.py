"""Take care of import jobs and copying files. Keep track of import modules"""

import logging, mimetypes, os, errno, re
from threading import Thread, Event

from bottle import Bottle, auth_basic, request
from sqlalchemy.orm.exc import NoResultFound

from . import api, ImportJob, Location, Entry
from .database import get_db
from .types import PropertySet, Property
from .user import authenticate, no_guests
from .location import LocationDescriptor, get_locations_by_type
from .metadata import wrap_raw_json
from .entry import create_entry


################################################################################
# Import API


BASE = '/import'
app = Bottle()
api.register(BASE, app)


@app.get('/')
@auth_basic(authenticate)
@no_guests()
def rest_get_importers():
    entries = []
    for location in get_locations_by_type(Location.Type.drop_folder).entries:
        entries.append({
            'location_id': location.id,
            'location_name': location.name,
            'trig_url': get_trig_url(location.id),
        })

    return {
        '*schema': 'ImporterFeed',
        'count': len(entries),
        'entries': entries,
    }


@app.post('/trig/<location_id:int>')
@auth_basic(authenticate)
@no_guests()
def rest_trig_import(location_id):
    manager = rest_trig_import.manager
    manager.trig(location_id)
    return {'result': 'ok'}


@app.get('/job')
@auth_basic(authenticate)
def rest_get_import_jobs():
    json = get_import_jobs().to_json()
    logging.info("Import Job feed\n%s", json)
    return json


@app.get('/job/<import_job_id:int>')
@auth_basic(authenticate)
def rest_get_import_job_by_id(import_job_id):
    json = get_import_job_by_id(import_job_id).to_json()
    logging.info("Import Job\n%s", json)
    return json


@app.post('/job/<import_job_id:int>/reset')
@auth_basic(authenticate)
@no_guests()
def rest_reset_import_job(import_job_id):
    json = reset_import_job(import_job_id).to_json()
    logging.info("Reset Import Job\n%s", json)
    return json


@app.post('/job')
@auth_basic(authenticate)
@no_guests()
def rest_create_import_job():
    logging.info(request.headers)
    logging.info(request.json)
    jd = ImportJobDescriptor(request.json)
    logging.info("Incoming Import Job\n%s", jd.to_json())
    json = create_import_job(jd).to_json()
    logging.info("Created Import Job\n%s", json)
    return json


def get_trig_url(location_id):
    return '%s/trig/%i' % (BASE, location_id)


def get_reset_url(import_job_id):
    return '%s/job/%i/reset' % (BASE, import_job_id)


api.url().import_job += get_trig_url
api.url().import_job += get_reset_url

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


re_clean = re.compile(r'[^A-Za-z0-9_\-\.]')


class ImportJobDescriptor(PropertySet):
    id = Property(int)
    path = Property()
    metadata = Property(wrap=True)
    user_id = Property(int)
    location = Property(LocationDescriptor)
    state = Property(enum=ImportJob.State)
    create_ts = Property()
    update_ts = Property()

    mime_type = Property()
    trig_reset_url = Property()

    @property
    def full_path(self):
        return os.path.join(self.location.get_root(), self.path)

    @property
    def filename(self):
        return os.path.basename(self.path)

    @property
    def safe_filename(self):
        return re_clean.sub('_', os.path.basename(self.path))

    def analyse(self):
        self.mime_type = mimetypes.guess_type(self.full_path)[0]
        logging.debug("Guessed MIME Type '%s' for '%s'", self.mime_type, self.full_path)

    def calculate_urls(self):
        if self.state is not ImportJob.State.new:
            self.trig_reset_url = get_reset_url(self.id)

    @classmethod
    def map_in(self, import_job):
        jd = ImportJobDescriptor(
            id=import_job.id,
            path=import_job.path,
            metadata=wrap_raw_json(import_job.data),
            user_id=import_job.user_id,
            location=LocationDescriptor.map_in(import_job.location),
            state=ImportJob.State(import_job.state),
            create_ts=(import_job.create_ts.strftime('%Y-%m-%d %H:%M:%S')
                       if import_job.create_ts is not None else None),
            update_ts=(import_job.update_ts.strftime('%Y-%m-%d %H:%M:%S')
                       if import_job.update_ts is not None else None),
        )
        jd.calculate_urls()
        return jd

    def map_out(self, import_job):
        if self.id is not None: import_job.id = self.id
        import_job.path = self.path
        import_job.data = self.metadata.to_json() if self.metadata is not None else None
        import_job.user_id = self.user_id
        import_job.location_id = self.location.id if self.location is not None else None
        import_job.state = self.state


class ImportJobDescriptorFeed(PropertySet):
    count = Property(int)
    entries = Property(list)


################################################################################
# Standard File Copyer Class


class FileCopy(object):
    def __init__(self, source, source_path, destination, dest_filename, link=False, keep_original=None, dest_folder=None):
        self.source = source
        if source and source.metadata and keep_original is None:
            self.keep_original = source.metadata.keep_original
        elif keep_original is None:
            self.keep_original = True
        else:
            self.keep_original = keep_original
        self.source_path = source_path
        self.destination = destination
        self.link = link
        self.dest_filename = dest_filename
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
            except OSError as e:
                if e.errno == errno.EXDEV:
                    logging.debug("Cross-device link %s -> %s", src, fixed_dst)
                    self.link = False

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
        import_jobs = t.query(ImportJob).order_by(ImportJob.update_ts.desc()).all()
        return ImportJobDescriptorFeed(
            count=len(import_jobs),
            entries=[ImportJobDescriptor.map_in(import_job) for import_job in import_jobs]
        )


def create_import_job(jd): # ImportJobDescriptor
    with get_db().transaction() as t:
        try:
            import_job = t.query(ImportJob).filter(
                ImportJob.location_id == jd.location.id,
                ImportJob.path == jd.path,
            ).one()

            return ImportJobDescriptor.map_in(import_job)
        except NoResultFound:
            logging.info("Creating Import Job for %i://%s",
                         jd.location.id,
                         jd.path
            )
            import_job = ImportJob()
            jd.map_out(import_job)
            t.add(import_job)
            t.commit()
            id = import_job.id
    
    jd = get_import_job_by_id(id)
    rest_trig_import(jd.location.id)
    return jd

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

        
def reset_import_job(import_job_id):
    logging.info("Resetting Import Job %i.", import_job_id)
    with get_db().transaction() as t:
        import_job = t.query(ImportJob).get(import_job_id)
        import_job.state = ImportJob.State.new
        metadata = wrap_raw_json(import_job.data) or ImportJob.DefaultImportJobMetadata()
        metadata.error = "This Import Job was reset by %s." % request.user.name
        import_job.data = metadata.to_json()

    jd = get_import_job_by_id(import_job_id)
    rest_trig_import(jd.location.id)
    return jd



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

        for location in get_locations_by_type(Location.Type.drop_folder, Location.Type.upload).entries:
            logging.info("Setting up import thread importer_%s", location.id)
            event = Event()
            self.events[location.id] = event
            thread = Thread(
                target=importing_loop,
                name="importer_%i" % (location.id),
                args=(event, location)
            )
            thread.daemon = True
            thread.start()

    def trig(self, location_id):
        event = self.events.get(location_id)
        if event is None:
            raise NameError("No thread for location %i", location_id)
        logging.info("Trigging import event for location %i", location_id)
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
            ed.user_id = jd.user_id or import_module.user_id
            if jd.metadata:
                if jd.metadata.tags:
                    ed.tags = jd.metadata.tags
                ed.hidden = jd.metadata.hidden
                ed.delete_ts = jd.metadata.delete_ts
                ed.access = jd.metadata.access

            logging.debug("EntryDescriptor:\n%s", ed.to_json())
            
            ed.state = Entry.State.online
            create_entry(ed, system=True)

            jd.state = ImportJob.State.done
            update_import_job_by_id(jd.id, jd)
            logging.info("Import Job Done %s", jd.path)
