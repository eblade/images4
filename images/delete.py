#!/usr/bin/env python3

import os, logging
from threading import Thread, Event
from bottle import Bottle, auth_basic
from datetime import datetime, timedelta
from sqlalchemy.orm.exc import NoResultFound

from . import api, Entry, Location
from .database import get_db
from .types import PropertySet, Property
from .location import get_locations, delete_file_on_location
from .entry import EntryDescriptor, delete_entry_by_id
from .user import authenticate, no_guests


# If a file has undeletable files, postpone the the delete_ts
POSTPONE = timedelta(hours=24)


################################################################################
# Delete API


BASE = '/delete'
app = Bottle()
api.register(BASE, app)


@app.get('/')
@auth_basic(authenticate)
@no_guests()
def rest_delete_info():
    return get_delete_info().to_json()


@app.post('/trig')
@auth_basic(authenticate)
@no_guests()
def rest_trig_delete():
    manager = rest_trig_delete.manager
    manager.trig()
    return {'result': 'ok'}


def get_trig_url():
    return '%s/trig' % (BASE, )

api.url().delete += get_trig_url


################################################################################
# Internal Delete API


def get_delete_info():
    di = DeleteInfo(trig_url=get_trig_url())

    with get_db().transaction() as t:
        di.marked = t.query(Entry).filter(
            Entry.delete_ts != None
        ).count()
        di.delayed = t.query(Entry).filter(
            Entry.delete_ts <= datetime.utcnow()
        ).count()
    
    return di
    


def pick_up_deletion():
    with get_db().transaction() as t:
        try:
            entry = t.query(Entry).filter(
                Entry.delete_ts <= datetime.utcnow()
            ).order_by(Entry.delete_ts).first()
            if entry is None:
                return None

            entry.delete_ts += POSTPONE
            return EntryDescriptor.map_in(entry)

        except NoResultFound:
            return None


################################################################################
# Deletion Info


class DeleteInfo(PropertySet):
    trig_url = Property()
    marked = Property(int)
    delayed = Property(int)


################################################################################
# Threaded Deletion Manager (Singleton)


class DeleteManager(object):
    """
    A Thread+Event based Delete Manager that keeps one thread
    and trigs a new deletion upon the trig method being called.

    There should only be one of these.
    """
    def __init__(self):
        self.events = {}
        rest_trig_delete.manager = self

        logging.info("Setting up deletion thread [Deleter]")

        locations = {l.id: l for l in get_locations().entries}

        event = Event()
        self.event = event
        thread = Thread(
            target=delete_loop,
            name="Deleter",
            args=(event, locations)
        )
        thread.daemon = True
        thread.start()

    def trig(self):
        logging.info("Trigging deletion event.")
        self.event.set()
                

def delete_loop(event, locations):
    """
    A scanning loop using FolderScanner. Will wait for event to be set
    each iteration or a certain amount of time.
    """
    logging.info("Started deletion thread.")
    while True:
        event.wait(1440)
        event.clear()

        while True:
            entry = pick_up_deletion()
            if entry is None:
                break
        
            logging.info("Deleting entry %i %s." % (entry.id, entry.original_filename))

            skip = False
            for f in entry.files:
                location = locations[f.location_id]
                if location.metadata.read_only:
                    logging.warning("Entry has a file on read_only location %i. Skipping.", location.id)
                    skip = True
                else:
                    logging.info("Will delete %i:%s.", location.id, f.path)

            if skip:
                logging.error("Entry %i cannot be deleted.", entry.id)
                continue

            for f in entry.files:
                location = locations[f.location_id]
                logging.info("Deleting file %i:%s.", location.id, f.path)

                delete_file_on_location(location, f.path)

            delete_entry_by_id(entry.id, system=True)
            logging.info("Deleted entry %i.", entry.id)
