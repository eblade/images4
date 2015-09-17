"""Take care of export jobs and copying files. Keep track of export modules"""

import logging, os, errno
from threading import Thread, Event
from datetime import datetime, timedelta
from bottle import Bottle, auth_basic

from . import api, ExportJob, Location, Entry, User, EXPORTABLE
from .database import get_db
from .localfile import FileCopy
from .user import authenticate, no_guests, current_user_id
from .types import PropertySet, Property
from .location import LocationDescriptor, get_locations_by_type, get_location_by_type
from .entry import EntryDescriptor, create_entry


################################################################################
# Export API


BASE = '/export'
app = Bottle()
api.register(BASE, app)


@app.get('/')
@auth_basic(authenticate)
@no_guests()
def rest_get_exporters():
    entries = []
    for location in get_locations_by_type(*EXPORTABLE).entries:
        entries.append({
            'location_id': location.id,
            'location_name': location.name,
            'trig_url': get_trig_url(location.id),
        })

    return {
        '*schema': 'ExporterFeed',
        'count': len(entries),
        'entries': entries,
    }


@app.post('/trig/<location_id:int>')
@auth_basic(authenticate)
@no_guests()
def rest_trig(location_id):
    manager = rest_trig.manager
    manager.trig(location_id)
    return {'result': 'ok'}


@app.get('/job')
@auth_basic(authenticate)
@no_guests()
def rest_get_export_jobs():
    json = get_export_jobs().to_json()
    logging.info("Export Job feed\n%s", json)
    return json


@app.get('/job/<export_job_id:int>')
@auth_basic(authenticate)
@no_guests()
def rest_get_export_job_by_id(export_job_id):
    json = get_export_job_by_id(export_job_id).to_json()
    logging.info("Export Job\n%s", json)
    return json


@app.delete('/job/<export_job_id:int>')
@auth_basic(authenticate)
@no_guests()
def rest_delete_export_job_by_id(export_job_id):
    n = delete_export_job_by_id(export_job_id)
    return {"result": "ok" if n else "nothing deleted"}


@app.post('/job/<export_job_id:int>/reset')
@auth_basic(authenticate)
@no_guests()
def rest_reset_export_job(export_job_id):
    json = reset_export_job(export_job_id).to_json()
    logging.info("Reset Export Job\n%s", json)
    return json


@app.post('/job')
@auth_basic(authenticate)
@no_guests()
def rest_create_export_job():
    jd = ExportJobDescriptor(request.json)
    logging.info("Incoming Export Job\n%s", jd.to_json())
    json = create_export_job(jd).to_json()
    logging.info("Created Export Job\n%s", json)
    rest_trig(jd.location.id)
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
# Export Module Handling

protocol_map = {}

def register_export_module(protocol, module):
    protocol_map[protocol] = module


def get_export_module(job_descriptor):
    export_module = protocol_map.get(job_descriptor.get_protocol(), None)
    return export_module(job_descriptor) if export_module is not None else None


class GenericExportModule(object):
    def __init__(self, job_descriptor):
        self.job_descriptor = job_descriptor


################################################################################
# Export Job Descriptor


class ExportJobDescriptor(PropertySet):
    id = Property(int)
    metadata = Property(wrap=True)
    user_id = Property(int)
    location = Property(LocationDescriptor)
    entry = Property(EntryDescriptor)
    state = Property(enum=ExportJob.State)
    create_ts = Property()
    update_ts = Property()
    deliver_ts = Property()

    self_url = Property()
    trig_reset_url = Property()

    @property
    def full_path(self):
        return os.path.join(self.location.get_root(), self.metadata.path)

    @property
    def filename(self):
        return os.path.basename(self.metadata.path)

    def get_protocol(self):
        if self.location.metadata.server is None:
            return None
        return self.location.metadata.server.split(':')[0]

    def calculate_urls(self):
        self.self_url = get_job_url(self.id)
        if self.state is not ExportJob.State.new:
            self.trig_reset_url = get_reset_url(self.id)

    @classmethod
    def map_in(self, export_job):
        jd = ExportJobDescriptor(
            id = export_job.id,
            metadata = wrap_raw_json(export_job.data),
            user = User.map_in(export_job.user),
            location = LocationDescriptor.map_in(export_job.location),
            entry = Entry.map_in(export_job.entry),
            state = ExportJob.State(export_job.state),
            create_ts = (export_job.create_ts.strftime('%Y-%m-%d %H:%M:%S')
                       if export_job.create_ts is not None else None),
            update_ts = (export_job.update_ts.strftime('%Y-%m-%d %H:%M:%S')
                       if export_job.update_ts is not None else None),
            deliver_ts = (export_job.deliver_ts.strftime('%Y-%m-%d %H:%M:%S')
                       if export_job.deliver_ts is not None else None),
        )
        jd.calculate_urls()
        return jd

    def map_out(self, export_job):
        if self.id is not None: export_job.id = self.id
        export_job.data = self.metadata.to_json() if self.metadata is not None else None
        export_job.user_id = self.user.id if self.user is not None else None
        export_job.location_id = self.location.id if self.location is not None else None
        export_job.state = self.state
        export_job.entry_id = self.entry.id if self.entry is not None else None
        export_job.deliver_ts = (datetime.datetime.strptime(
            self.deliver_ts, '%Y-%m-%d %H:%M:%S').replace(microsecond = 0)
            if self.deliver_ts else None
        )


class ExportJobDescriptorFeed(PropertySet):
    count = Property(int)
    entries = Property(list)


################################################################################
# Internal Export API


def get_export_job_by_id(id):
    with get_db().transaction() as t:
        export_job = t.query(ExportJob).filter(
            ExportJob.id==id
        ).one()
        return ExportJobDescriptor.map_in(export_job)


def get_export_jobs():
    with get_db().transaction() as t:
        export_jobs = t.query(ExportJob).order_by(ExportJob.update_ts.desc()).limit(100).all()
        return ExportJobDescriptorFeed(
            count=len(export_jobs),
            entries=[ExportJobDescriptor.map_in(export_job) for export_job in export_jobs]
        )


def create_export_job(jd): # ExportJobDescriptor
    with get_db().transaction() as t:
        try:
            export_job = t.query(ExportJob).filter(
                ExportJob.location_id == jd.location.id,
                ExportJob.path == jd.path,
            ).one()

            return ExportJobDescriptor.map_in(export_job)
        except NoResultFound:
            logging.info("Creating Export Job for %i://%s",
                         jd.location.id,
                         jd.path
            )
            export_job = ExportJob()
            jd.map_out(export_job)
            t.add(export_job)
            t.commit()
            id = export_job.id
    
    jd = get_export_job_by_id(id)
    return jd


def pick_up_export_job(location_id):
    with get_db().transaction() as t:
        try:
            export_job = t.query(ExportJob).filter(
                ExportJob.location_id==location_id,
                ExportJob.state==ExportJob.State.new
            ).order_by(ExportJob.create_ts).first()
            if export_job is None:
                return None

            export_job.state = ExportJob.State.active
            return ExportJobDescriptor.map_in(export_job)

        except NoResultFound:
            return None


def fail_export_job(export_job_descriptor, reason):
    logging.error(reason)
    with get_db().transaction() as t:
        export_job = t.query(ExportJob).get(export_job_descriptor.id)
        export_job.state = ExportJob.State.failed
        metadata = wrap_raw_json(export_job.data) or ExportJob.DefaultExportJobMetadata()
        metadata.error = reason
        export_job.data = metadata.to_json()


def update_export_job_by_id(id, jd):
    with get_db().transaction() as t:
        export_job = t.query(ExportJob).filter(
            ExportJob.id==id
        ).one()
        jd.map_out(export_job)
    
    return get_export_job_by_id(id)

        
def reset_export_job(export_job_id):
    logging.info("Resetting Export Job %i.", export_job_id)
    with get_db().transaction() as t:
        export_job = t.query(ExportJob).get(export_job_id)
        export_job.state = ExportJob.State.new
        metadata = wrap_raw_json(export_job.data) or ExportJob.DefaultExportJobMetadata()
        metadata.error = "This Export Job was reset by %s." % request.user.name
        export_job.data = metadata.to_json()

    jd = get_export_job_by_id(export_job_id)
    rest_trig_export(jd.location.id)
    return jd


def delete_old_export_jobs():
    logging.info("Deleting old Export Jobs.")
    with get_db().transaction() as t:
        n = t.query(ExportJob).filter(
            ExportJob.state == ExportJob.State.done,
            ExportJob.update_ts < (datetime.utcnow()-timedelta(hours=1))
        ).delete(synchronize_session=False)
        logging.info("Deleted %i old Export Jobs.", n)
        return n


def delete_export_job_by_id(export_job_id):
    logging.info("Deleting Export Job %i.", export_job_id)
    with get_db().transaction() as t:
        n = t.query(ExportJob).filter(
            ExportJob.id == export_job_id
        ).delete()
        logging.info("Deleted %s.", "one job" if n else "no jobs")
        return n


################################################################################
# Threaded Export Manager (Singleton)


class ExportManager(object):
    """
    A Thread+Event based Export Manager that keeps one thread per location
    and trigs a new export round upon the trig method being called.

    There should only be one of these.
    """
    def __init__(self):
        self.events = {}
        rest_trig_export.manager = self

        for location in get_locations_by_type(*EXPORTABLE).entries:
            logging.debug("Setting up export thread [Exporter%i].", location.id)
            event = Event()
            self.events[location.id] = event
            thread = Thread(
                target=exporting_loop,
                name="Exporter%i" % (location.id),
                args=(event, location)
            )
            thread.daemon = True
            thread.start()

        logging.debug("Setting up export job cleaning thread [ExportCleaner].")
        event = Event()
        self.events['clean'] = event
        thread = Thread(
            target=cleaning_loop,
            name="ExportCleaner",
            args=(event,)
        )
        thread.daemon = True
        thread.start()

    def trig(self, location_id):
        event = self.events.get(location_id)
        if event is None:
            raise NameError("No thread for location %i", location_id)
        logging.info("Trigging export event for location %i", location_id)
        event.set()
                

def exporting_loop(export_event, location):
    """
    An export loop that will wait for export_event to be set
    each iteration.
    """
    metadata = location.metadata
    logging.info("Started exporter thread for %i:%s", location.id, metadata.folder)
    while True:
        export_event.wait(30)
        export_event.clear()

        while True:
            jd = pick_up_export_job(location.id)

            if jd is None:
                break

            logging.debug("ExportJobDescriptor:\n%s", jd.to_json())

            jd.analyse()
            export_module = get_export_module(jd)

            if export_module is None:
                fail_export_job(jd, 
                    "Could not find a suitable export module for MIME Type %s" % jd.mime_type
                )
                continue

            try:
                export_module.run()
            except Exception as e:
                fail_export_job(jd, 
                    "Export failed %s" % str(e)
                )
                continue

            ed = export_module.entry
            ed.user_id = jd.user_id or export_module.user_id

            if not jd.metadata:
                jd.metadata = ExportJob.DefaultExportJobMetadata()

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
                jd.state = ExportJob.State.keep
            else:
                jd.state = ExportJob.State.done

            jd.entry_id = ed.id
            update_export_job_by_id(jd.id, jd)
            logging.info("Export Job Done %s", jd.path)


def cleaning_loop(clean_event):
    """
    A cleaning loop that will wait for clean_event to be set
    each iteration.
    """
    logging.info("Started export job cleaning thread")
    while True:
        clean_event.wait(720)
        clean_event.clear()

        delete_old_export_jobs()
