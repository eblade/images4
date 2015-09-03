#!/usr/bin/env python3

import os, logging
from threading import Thread, Event
from bottle import Bottle, auth_basic

from . import Location
from .database import get_db
from .location import LocationDescriptor, get_locations_by_type
from .import_job import ImportJobDescriptor, create_import_job
from .metadata import wrap_raw_json
from .user import authenticate, no_guests


################################################################################
# Scenner API


API = '/scanner'
api = Bottle()


@api.get('/')
@auth_basic(authenticate)
@no_guests()
def rest_get_scanners():
    entries = []
    for location in get_locations_by_type(Location.Type.drop_folder).entries:
        entries.append({
            'location_id': location.id,
            'location_name': location.name,
            'trig_url': API + 'trig/%i' % location.id,
        })

    return {
        '*schema': 'ScannerFeed',
        'count': len(entries),
        'entries': entries,
    }
        
    
@api.get('/trig/<location_id:int>')
@auth_basic(authenticate)
@no_guests()
def rest_trig_scan(location_id):
    manager = rest_trig_scan.manager
    manager.trig(location_id)
    return {'result': 'ok'}


################################################################################
# Default Folder Scanner


class FolderScanner(object):
    """
    A simple recursive folder scanner.
    """
    def __init__(self, basepath, ext=None):
        self.basepath = basepath
        self.ext = ext

    def scan(self):
        for r, ds, fs in os.walk(self.basepath):
            for f in fs:
                if not self.ext or f.split('.')[-1].lower() in self.ext:
                    p = os.path.relpath(os.path.join(r, f), self.basepath)
                    if not p.startswith('.'):
                        yield p


################################################################################
# Threaded Scanner Manager (Singleton)


class ScannerManager(object):
    """
    A Thread+Event based Scanner Manager that keeps one thread per folder
    and trigs a new scan upon the trig method being called.

    There should only be one of these.
    """
    def __init__(self):
        self.events = {}
        rest_trig_scan.manager = self

        for location in get_locations_by_type(Location.Type.drop_folder).entries:
            event = Event()
            self.events[location.id] = (event, location)
            thread = Thread(
                target=scanning_loop,
                name="scanner_%i" % (location.id),
                args=(event, location)
            )
            thread.daemon = True
            thread.start()

    def trig(self, location_id):
        event, _ = self.events.get(location_id, (None, None))
        if event is None:
            return
        event.set()
                

def scanning_loop(scan_event, location):
    """
    A scanning loop using FolderScanner. Will wait for scan_event to be set
    each iteration.
    """
    metadata = location.metadata
    logging.info("Started scanner thread for %i:%s", location.id, metadata.folder)
    while True:
        scanner = FolderScanner(metadata.folder, ext=None)

        scan_event.wait(30)
        scan_event.clear()

        for filepath in scanner.scan():
            jd = ImportJobDescriptor(
                path=filepath,
                location=LocationDescriptor(id=location.id),
                user_id=metadata.user_id
            )
            create_import_job(jd)
