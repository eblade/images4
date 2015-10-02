#!/usr/bin/env python3

from enum import IntEnum
import os, datetime, logging, urllib
from bottle import Bottle, auth_basic, request

from . import Entry, api
from .database import get_db
from .types import PropertySet, Property
from .location import LocationDescriptor, get_download_url
from .user import require_user_id, current_user_id, authenticate, no_guests, current_is_user
from .metadata import wrap_raw_json
from .tag import ensure_tag


DELETE_AFTER = 24  # hours


################################################################################
# Entry API

BASE = '/entry'
app = Bottle()
api.register(BASE, app)


@app.get('/')
@auth_basic(authenticate)
def rest_get_entries():
    query = EntryQuery.map_in_from_request()
    json = get_entries(query=query).to_json()
    logging.debug("Entry feed\n%s", json)
    return json


@app.get('/<id:int>')
@auth_basic(authenticate)
def rest_get_entry_by_id(id):
    json = get_entry_by_id(id).to_json()
    logging.debug("Entry\n%s", json)
    return json


@app.put('/<id:int>')
@auth_basic(authenticate)
@no_guests()
def rest_update_entry_by_id(id):
    entry = EntryDescriptor(request.json)
    logging.debug("Incoming Entry\n%s", entry.to_json())
    json = update_entry_by_id(id, entry).to_json()
    logging.debug("Outgoing Entry\n%s", json)
    return json


@app.delete('/<id:int>')
@auth_basic(authenticate)
@no_guests()
def rest_delete_entry_by_id(id):
    logging.debug("Deleting Entry %i", id)
    delete_entry_by_id(id)


@app.post('/source/<source>/<filename>')
@auth_basic(authenticate)
@no_guests()
def rest_get_entry_by_source(source, filename):
    json = get_entry_by_source(source, filename).to_json()
    logging.debug("Entry\n%s", json)
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
    source = Property()
    state = Property(enum=Entry.State)
    hidden = Property(bool, default=False)
    delete_ts = Property()
    deleted = Property(bool, default=False)
    access = Property(enum=Entry.Access, default=Entry.Access.private)
    files = Property(list)
    tags = Property(list)
    
    create_ts = Property()
    update_ts = Property()
    taken_ts = Property()

    user_id = Property(default=1)
    parent_entry_id = Property()

    metadata = Property(wrap=True)
    physical_metadata = Property(wrap=True)

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
        return ','.join(sorted([("~%s~" % tag.lower()) for tag in self.tags if tag]))

    def calculate_urls(self):
        self.self_url = '%s/%i' % (BASE, self.id)
        for fd in self.files:
            if fd.purpose == FileDescriptor.Purpose.primary:
                self.primary_url = api.url().location.get_download_url(fd.location_id, fd.path)
            if fd.purpose == FileDescriptor.Purpose.proxy:
                self.proxy_url = api.url().location.get_download_url(fd.location_id, fd.path)
            if fd.purpose == FileDescriptor.Purpose.thumb:
                self.thumb_url = api.url().location.get_download_url(fd.location_id, fd.path)

    @classmethod
    def map_in(self, entry):
        ed = EntryDescriptor( 
            id=entry.id,
            user_id=entry.user_id,
            state=Entry.State(entry.state),
            access=Entry.Access(entry.access),
            original_filename=entry.original_filename,
            source=entry.source,
            create_ts=entry.create_ts.strftime('%Y-%m-%d %H:%M:%S'),
            update_ts=entry.update_ts.strftime('%Y-%m-%d %H:%M:%S') if entry.update_ts else None,
            taken_ts=entry.taken_ts.strftime('%Y-%m-%d %H:%M:%S') if entry.taken_ts else None,
            delete_ts=entry.delete_ts.strftime('%Y-%m-%d %H:%M:%S') if entry.delete_ts else None,
            deleted=entry.delete_ts is not None,
            hidden=entry.hidden,
            files=[FileDescriptor.FromJSON(f) for f in entry.files.split('\n')] if entry.files else [],
            tags=sorted([tag.replace('~', '') for tag in entry.tags.split(',') if tag]),
            metadata=wrap_raw_json(entry.data),
            physical_metadata=wrap_raw_json(entry.physical_data),
        )
        ed.calculate_urls()
        return ed

    def map_out(self, entry, system=False):
        entry.original_filename = self.original_filename
        entry.export_filename = self.export_filename
        entry.source = self.source
        entry.state = self.state
        entry.hidden = self.hidden
        entry.taken_ts = (datetime.datetime.strptime(
            self.taken_ts, '%Y-%m-%d %H:%M:%S').replace(microsecond = 0)
            if self.taken_ts else None
        )
        if self.deleted and self.delete_ts is None:
            self.delete_ts = ((datetime.datetime.utcnow() + datetime.timedelta(hours=DELETE_AFTER))
                .strftime('%Y-%m-%d %H:%M:%S'))
        elif self.deleted is False and self.delete_ts is not None:
            self.delete_ts = None
        entry.delete_ts = (datetime.datetime.strptime(
            self.delete_ts, '%Y-%m-%d %H:%M:%S').replace(microsecond = 0)
            if self.delete_ts else None
        )
        entry.access = self.access
        entry.data = self.metadata.to_json() if self.metadata else None
        entry.physical_data = self.physical_metadata.to_json() if self.physical_metadata else None
        entry.user_id = self.user_id
        entry.parent_entry_id = self.parent_entry_id
        entry.latitude = self.latitude
        entry.longitude = self.longitude
        entry.tags = self.tags_as_string
        if system:
            entry.files = '\n'.join([f.to_json(pretty=False) for f in self.files])


class EntryDescriptorFeed(PropertySet):
    count = Property(int)
    total_count = Property(int)
    prev_link = Property()
    next_link = Property()
    offset = Property(int)
    entries = Property(list)


class EntryQuery(PropertySet):
    start_ts = Property(none='')
    end_ts = Property(none='')
    image = Property(bool, default=True)
    video = Property(bool, default=False)
    audio = Property(bool, default=False)
    other = Property(bool, default=False)
    show_hidden = Property(bool, default=False)
    only_hidden = Property(bool, default=False)
    show_deleted = Property(bool, default=False)
    only_deleted = Property(bool, default=False)
    include_tags = Property(list)
    exclude_tags = Property(list)
    source = Property()

    next_ts = Property(none='')
    prev_offset = Property(int)
    page_size = Property(int, default=25, required=True)
    order = Property(default='desc', required=True)

    @classmethod
    def map_in_from_request(self):
        eq = EntryQuery()

        eq.start_ts = request.query.start_ts
        eq.end_ts = request.query.end_ts

        eq.next_ts = request.query.next_ts
        if not request.query.prev_offset in (None, ''):
            eq.prev_offset = request.query.prev_offset
        if not request.query.page_size in (None, ''):
            eq.page_size = request.query.page_size
        if not request.query.order in (None, ''):
            eq.order = request.query.order

        eq.image = request.query.image == 'yes'
        eq.video = request.query.video == 'yes'
        eq.audio = request.query.audio == 'yes'
        eq.other = request.query.other == 'yes'

        eq.source = request.query.source
        
        eq.show_hidden = request.query.show_hidden == 'yes'
        eq.show_deleted = request.query.show_deleted == 'yes'
        eq.only_hidden = request.query.only_hidden == 'yes'
        eq.only_deleted = request.query.only_deleted == 'yes'

        eq.include_tags = [t.strip() for t in (request.query.include_tags or '').split(',') if t.strip()]
        eq.exclude_tags = [t.strip() for t in (request.query.exclude_tags or '').split(',') if t.strip()]
        return eq
    
    def to_query_string(self):
        return urllib.parse.urlencode((
            ('start_ts', self.start_ts),
            ('end_ts', self.end_ts),
            ('next_ts', self.next_ts),
            ('prev_offset', self.prev_offset or ''),
            ('page_size', self.page_size),
            ('order', self.order),
            ('image', 'yes' if self.image else 'no'),
            ('video', 'yes' if self.video else 'no'),
            ('audio', 'yes' if self.audio else 'no'),
            ('other', 'yes' if self.other else 'no'),
            ('source', self.source),
            ('show_hidden', 'yes' if self.show_hidden else 'no'),
            ('show_deleted', 'yes' if self.show_deleted else 'no'),
            ('only_hidden', 'yes' if self.only_hidden else 'no'),
            ('only_deleted', 'yes' if self.only_deleted else 'no'),
            ('include_tag', ','.join(self.include_tags)),
            ('exclude_tag', ','.join(self.exclude_tags)),
        ))

################################################################################
# Entry Internal BASE


def get_entries(query=None, system=False):
    with get_db().transaction() as t:
        q = (t.query(Entry)
              .order_by(Entry.taken_ts.desc(), Entry.create_ts.desc())
        )
        if not system:
            q = q.filter(
                  (Entry.user_id == current_user_id())
                | (Entry.access >= Entry.Access.users)
            )

            if not current_is_user():
                q = q.filter(Entry.access >= Entry.Access.public)

        if query is not None:
            logging.info("Query: %s", query.to_json())
            
            if query.start_ts:
                start_ts = (datetime.datetime.strptime(
                    query.start_ts, '%Y-%m-%d')
                    .replace(hour=0, minute=0, second=0, microsecond=0))
                q = q.filter(Entry.taken_ts >= start_ts)

            if query.end_ts:
                end_ts = (datetime.datetime.strptime(
                    query.end_ts, '%Y-%m-%d')
                    .replace(hour=0, minute=0, second=0, microsecond=0))
                q = q.filter(Entry.taken_ts < end_ts)
            
            types = [t.value for t in Entry.Type if getattr(query, t.name)]
            if types:
                q = q.filter(Entry.type.in_(types))

            if not query.show_hidden:
                q = q.filter(Entry.hidden == False)
            if not query.show_deleted:
                q = q.filter(Entry.delete_ts == None)
            if query.only_hidden:
                q = q.filter(Entry.hidden == True)
            if query.only_deleted:
                q = q.filter(Entry.delete_ts != None)

            for tag in query.include_tags:
                q = q.filter(Entry.tags.like('%~' + tag + '~%'))
            for tag in query.exclude_tags:
                q = q.filter(~Entry.tags.like('%~' + tag + '~%'))

            if query.source:
                q = q.filter(Entry.source == query.source)

        total_count = q.count()

        # Default values for when no paging occurs
        offset = 0
        total_count_paged = total_count

        # Paging
        if query is not None:
            if query.next_ts:
                end_ts = (datetime.datetime.strptime(
                    query.next_ts, '%Y-%m-%d %H:%M:%S').replace(microsecond=0))
                q = q.filter(Entry.taken_ts < end_ts)
                total_count_paged = q.count()
                offset = total_count - total_count_paged

            elif query.prev_offset:
                q = q.offset(query.prev_offset)
                total_count_paged = total_count
                offset = query.prev_offset

            logging.info(q)
            page_size = query.page_size
            entries = q.limit(page_size).all()

        else:
            entries = q.all()

        count = len(entries)

        result = EntryDescriptorFeed(
            count=count,
            total_count=total_count,
            offset=offset,
            entries = [EntryDescriptor.map_in(entry) for entry in entries])
        
        # Paging
        if query is not None:
            if total_count > count:
                query.next_ts = result.entries[-1].taken_ts
                result.next_link = BASE + '?' + query.to_query_string()

            if count > 0 and offset > 0:
                query.next_ts = ''
                query.prev_offset = max(offset - page_size, 0)
                result.prev_link = BASE + '?' + query.to_query_string()

        return result


def get_entry_by_id(id):
    with get_db().transaction() as t:
        entry = t.query(Entry).filter(Entry.id==id).one()
        return EntryDescriptor.map_in(entry) 


def get_entry_by_source(source, filename, system=False):
    with get_db().transaction() as t:
        q = t.query(Entry).filter(
            Entry.source == source,
            Entry.original_filename == filename
        )
        if not system:
            q = q.filter((Entry.user_id == current_user_id()) 
                       | (Entry.access >= Entry.Access.public))
        entry = q.one()
        return EntryDescriptor.map_in(entry) 


def update_entry_by_id(id, ed, system=False):
    with get_db().transaction() as t:
        q = t.query(Entry).filter(Entry.id==id)
        if not system:
            q = q.filter(
                (Entry.user_id == current_user_id()) | (Entry.access >= Entry.Access.common)
            )
        entry = q.one()
        ed.map_out(entry)

    return get_entry_by_id(id)


def create_entry(ed, system=False):
    with get_db().transaction() as t:
        entry = Entry()

        for tag in ed.tags:
            ensure_tag(tag)

        ed.map_out(entry, system=system)
        t.add(entry)
        t.commit()
        id = entry.id

    return get_entry_by_id(id)


def delete_entry_by_id(id, system=False):
    with get_db().transaction() as t:
        q = t.query(Entry).filter(Entry.id==id)
        if not system:
            q = q.filter(
                (Entry.user_id == current_user_id()) | (Entry.access >= Entry.Access.common)
            )
        q.delete()
