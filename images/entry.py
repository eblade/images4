#!/usr/bin/env python3

from enum import IntEnum
import os, datetime, logging
from bottle import Bottle, auth_basic, request

from . import Entry
from .database import get_db
from .types import PropertySet, Property
from .location import LocationDescriptor, get_download_url
from .user import require_user_id, current_user_id, authenticate, no_guests
from .metadata import wrap_raw_json


################################################################################
# Entry API

API = '/entry'
api = Bottle()


@api.get('/')
@auth_basic(authenticate)
def rest_get_entries():
    json = get_entries().to_json()
    logging.debug("Entry feed\n%s", json)
    return json


@api.get('/<id:int>')
@auth_basic(authenticate)
def rest_get_entry_by_id(id):
    json = get_entry_by_id(id).to_json()
    logging.debug("Entry\n%s", json)
    may_see(entry)
    return json


@api.put('/<id:int>')
@auth_basic(authenticate)
@no_guests()
def rest_update_entry_by_id(id):
    entry = EntryDescriptor(request.json)
    logging.debug("Incoming Entry\n%s", entry.to_json())
    json = update_entry_by_id(id, entry).to_json()
    logging.debug("Outgoing Entry\n%s", json)
    return json


################################################################################
# Entry Descriptors


class FileDescriptor(PropertySet):

    class Purpose(IntEnum):
        primary = 0
        proxy = 1
        thumb = 2
        attachment = 3

    path = Property()
    location_id = Property(int)
    size = Property(int, default=0)
    purpose = Property(enum=Purpose, default=Purpose.primary)
    mime = Property()


class EntryDescriptor(PropertySet):

    id = Property(int)
    path = Property()
    original_filename = Property()
    export_filename = Property()
    state = Property(enum=Entry.State)
    hidden = Property(bool, default=False)
    deleted = Property(bool, default=False)
    access = Property(enum=Entry.Access, default=Entry.Access.private)
    files = Property(list)
    tags = Property(list)
    
    create_ts = Property()
    update_ts = Property()
    taken_ts = Property()

    user_id = Property(default=1)
    parent_entry_id = Property()

    metadata = Property(Entry.DefaultMetadata)
    physical_metadata = Property(Entry.DefaultPhysicalMetadata)

    primary_url = Property()
    proxy_url = Property()
    thumb_url = Property()

    self_url = Property()

    @property
    def latitude(self):
        if hasattr(self.physical_metadata, 'Latitude'):
            return self.physical_metadata.Latitude

    @property
    def longitude(self):
        if hasattr(self.physical_metadata, 'Longitude'):
            return self.physical_metadata.Longitude

    @property
    def tags_as_string(self):
        return ','.join([tag.lower() for tag in self.tags if tag])

    def calculate_urls(self):
        self.self_url = '%s/%i' % (API, self.id)
        for fd in self.files:
            if fd.purpose == FileDescriptor.Purpose.primary:
                self.primary_url = get_download_url(fd.location_id, fd.path)
            if fd.purpose == FileDescriptor.Purpose.proxy:
                self.proxy_url = get_download_url(fd.location_id, fd.path)
            if fd.purpose == FileDescriptor.Purpose.thumb:
                self.thumb_url = get_download_url(fd.location_id, fd.path)

    @classmethod
    def map_in(self, entry):
        ed = EntryDescriptor( 
            id=entry.id,
            user_id=entry.user_id,
            state=Entry.State(entry.state),
            access=Entry.Access(entry.access),
            original_filename=entry.original_filename,
            create_ts=entry.create_ts.strftime('%Y-%m-%d %H:%M:%S'),
            update_ts=entry.update_ts.strftime('%Y-%m-%d %H:%M:%S') if entry.update_ts else None,
            taken_ts=entry.taken_ts.strftime('%Y-%m-%d %H:%M:%S') if entry.taken_ts else None,
            hidden=entry.hidden,
            deleted=entry.deleted,
            files=[FileDescriptor.FromJSON(f) for f in entry.files.split('\n')],
            tags=[tag for tag in entry.tags.split(',') if tag],
            metadata=wrap_raw_json(entry.data),
            physical_metadata=wrap_raw_json(entry.physical_data),
        )
        ed.calculate_urls()
        return ed

    def map_out(self, entry):
        entry.original_filename = self.original_filename
        entry.export_filename = self.export_filename
        entry.state = self.state
        entry.hidden = self.hidden
        entry.taken_ts = (datetime.datetime.strptime(
            self.taken_ts, '%Y-%m-%d %H:%M:%S').replace(microsecond = 0)
            if self.taken_ts else None
        )
        entry.access = self.access
        entry.data = self.metadata.to_json() if self.metadata else None
        entry.physical_data = self.physical_metadata.to_json() if self.physical_metadata else None
        entry.user_id = self.user_id
        entry.parent_entry_id = self.parent_entry_id
        entry.latitude = self.latitude
        entry.longitude = self.longitude
        entry.files = '\n'.join([f.to_json(pretty=False) for f in self.files])
        entry.tags = self.tags_as_string


class EntryDescriptorFeed(PropertySet):
    count = Property(int)
    entries = Property(list)


################################################################################
# Entry Internal API


def get_entries():
    with get_db().transaction() as t:
        q = (t.query(Entry)
              .filter((Entry.user_id == current_user_id()) | (Entry.access >= Entry.Access.common))
              .order_by(Entry.taken_ts.desc(), Entry.create_ts.desc())
              .limit(100))

        logging.debug(q)
        entries = q.all()

        result = EntryDescriptorFeed(count=len(entries))
        result.entries = [EntryDescriptor.map_in(entry) for entry in entries]

        return result


def get_entry_by_id(id):
    with get_db().transaction() as t:
        entry = t.query(Entry).filter(Entry.id==id).one()

        return EntryDescriptor.map_in(entry) 


def update_entry_by_id(id, ed):
    with get_db().transaction() as t:
        entry = (t.query(Entry)
                  .filter(Entry.id==id,
                         (Entry.user_id == current_user_id())
                       | (Entry.access >= Entry.Access.common))
                  .one())

        entry.state = ed.state.value
        entry.export_filename = ed.export_filename
        entry.hidden = ed.hidden
        entry.deleted = ed.deleted
        entry.tags = ed.tags_as_string

    return get_entry_by_id(id)


def create_entry(ed):
    with get_db().transaction() as t:
        entry = Entry()
        ed.map_out(entry)
        t.add(entry)
        t.commit()
        id = entry.id

    return get_entry_by_id(id)
