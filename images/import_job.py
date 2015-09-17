"""Take care of import jobs and copying files. Keep track of import modules"""

import logging, mimetypes, os, re, base64
from threading import Thread, Event
from datetime import datetime, timedelta

from bottle import Bottle, auth_basic, request
from sqlalchemy.orm.exc import NoResultFound

from . import api, ImportJob, Location, Entry, IMPORTABLE
from .database import get_db
from .types import PropertySet, Property
from .user import authenticate, no_guests, current_user_id
from .location import LocationDescriptor, get_locations_by_type, get_location_by_type
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
    for location in get_locations_by_type(*IMPORTABLE).entries:
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
@no_guests()
def rest_get_import_jobs():
    json = get_import_jobs().to_json()
    logging.debug("Import Job feed\n%s", json)
    return json


@app.get('/job/<import_job_id:int>')
@auth_basic(authenticate)
@no_guests()
def rest_get_import_job_by_id(import_job_id):
    json = get_import_job_by_id(import_job_id).to_json()
    logging.debug("Import Job\n%s", json)
    return json


@app.delete('/job/<import_job_id:int>')
@auth_basic(authenticate)
@no_guests()
def rest_delete_import_job_by_id(import_job_id):
    n = delete_import_job_by_id(import_job_id)
    return {"result": "ok" if n else "nothing deleted"}


@app.post('/job/<import_job_id:int>/reset')
@auth_basic(authenticate)
@no_guests()
def rest_reset_import_job(import_job_id):
    json = reset_import_job(import_job_id).to_json()
    logging.debug("Reset Import Job\n%s", json)
    return json


@app.post('/job')
@auth_basic(authenticate)
@no_guests()
def rest_create_import_job():
    jd = ImportJobDescriptor(request.json)
    logging.debug("Incoming Import Job\n%s", jd.to_json())
    json = create_import_job(jd).to_json()
    logging.debug("Created Import Job\n%s", json)
    rest_trig_import(jd.location.id)
    return json


@app.post('/upload/<source>/<filename>')
@auth_basic(authenticate)
@no_guests()
def rest_upload(source, filename):
    location = get_location_by_type(Location.Type.upload)
    folder = location.suggest_folder(source=source)
    try:
        os.makedirs(folder)
    except FileExistsError:
        pass
    destination = os.path.join(folder, filename)
    logging.info("Storing file at %s.", destination)
    with open(destination, 'w+b') as disk:
        data = request.body.read()
        logging.info(request.headers['Content-Type'])
        if request.headers['Content-Type'].startswith('base64'):
            data = base64.b64decode(data[22:])
            logging.info("Writing %i bytes after base64 decode", len(data))
        else:
            logging.info("Writing %i bytes without decode", len(data))
        disk.write(data)
    request.body.close()

    # Create an Import Job for this
    jd = create_import_job(ImportJobDescriptor(
        path = os.path.relpath(destination, location.get_root()),
        user_id = current_user_id(),
        location = location,
        metadata = ImportJob.DefaultImportJobMetadata(
            source = source,
        ),
    ))
    rest_trig_import(jd.location.id)

    json = jd.to_json()
    return json


def get_job_url(location_id):
    return '%s/job/%i' % (BASE, location_id)


def get_trig_url(location_id):
    return '%s/trig/%i' % (BASE, location_id)


def get_reset_url(import_job_id):
    return '%s/job/%i/reset' % (BASE, import_job_id)


api.url().import_job += get_job_url
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
    entry_id = Property(int)

    mime_type = Property()
    self_url = Property()
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
        self.self_url = get_job_url(self.id)
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
            entry_id = import_job.entry_id
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
        import_job.entry_id = self.entry_id


class ImportJobDescriptorFeed(PropertySet):
    count = Property(int)
    entries = Property(list)


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
        import_jobs = t.query(ImportJob).order_by(ImportJob.update_ts.desc()).limit(100).all()
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


def delete_old_import_jobs():
    logging.debug("Deleting old Import Jobs.")
    with get_db().transaction() as t:
        n = t.query(ImportJob).filter(
            ImportJob.state == ImportJob.State.done,
            ImportJob.update_ts < (datetime.utcnow()-timedelta(hours=1))
        ).delete(synchronize_session=False)
        logging.debug("Deleted %i old Import Jobs.", n)
        return n


def delete_import_job_by_id(import_job_id):
    logging.info("Deleting Import Job %i.", import_job_id)
    with get_db().transaction() as t:
        n = t.query(ImportJob).filter(
            ImportJob.id == import_job_id
        ).delete()
        logging.info("Deleted %s.", "one job" if n else "no jobs")
        return n


################################################################################
# Threaded Import Manager (Singleton)


class ImportManager(object):
    """
    A Thread+Event based Import Manager that keeps one thread per location
    and trigs a new import round upon the trig method being called.

    There should only be one of these.
    """
    def __init__(self):
        self.events = {}
        rest_trig_import.manager = self

        for location in get_locations_by_type(*IMPORTABLE).entries:
            logging.debug("Setting up import thread [Importer%i].", location.id)
            event = Event()
            self.events[location.id] = event
            thread = Thread(
                target=importing_loop,
                name="Importer%i" % (location.id),
                args=(event, location)
            )
            thread.daemon = True
            thread.start()

        logging.debug("Setting up import job cleaning thread [ImportCleaner].")
        event = Event()
        self.events['clean'] = event
        thread = Thread(
            target=cleaning_loop,
            name="ImportCleaner",
            args=(event,)
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

            if not jd.metadata:
                jd.metadata = ImportJob.DefaultImportJobMetadata()

            if jd.metadata.tags:
                ed.tags = jd.metadata.tags
            elif metadata.tags:
                ed.tags = metadata.tags
            ed.hidden = jd.metadata.hidden or metadata.hidden
            ed.delete_ts = jd.metadata.delete_ts
            ed.access = jd.metadata.access or metadata.access
            ed.metadata = jd.metadata.metadata
            ed.source = jd.metadata.source or metadata.source

            logging.debug("EntryDescriptor:\n%s", ed.to_json())
            
            ed.state = Entry.State.online
            ed = create_entry(ed, system=True)

            if metadata.keep_original:
                jd.state = ImportJob.State.keep
            else:
                jd.state = ImportJob.State.done

            jd.entry_id = ed.id
            update_import_job_by_id(jd.id, jd)
            logging.info("Import Job Done %s", jd.path)

def cleaning_loop(clean_event):
    """
    A cleaning loop that will wait for clean_event to be set
    each iteration.
    """
    logging.info("Started import job cleaning thread")
    while True:
        clean_event.wait(720)
        clean_event.clear()

        delete_old_import_jobs()
