
from enum import IntEnum

from sqlalchemy import Column, DateTime, String, Integer, Boolean, Float, ForeignKey, func
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base

from .database import Base
from .types import PropertySet, Property
from .metadata import register_metadata_schema


PROXY_SIZE = 1280
THUMB_SIZE = 200


class Location(Base):
    __tablename__ = 'location'

    class Type(IntEnum):
        drop_folder = 0  # Import location that is scanned
        image = 1        # Storage location for original high resolution image
        video = 2        # Storage location for original high resolution video
        audio = 3        # Storage location for original high resolution audio
        other = 4        # Storage location for other original files
        proxy = 5        # Storage location for low resolution proxy copy
        thumb = 6        # Storage location for thumbnail image
        upload = 7       # Import location for web upload which is not scanned
        export = 8       # Export location "fire and forget"
        archive = 9      # Export location where copies are remembered as remote copies
        mobile = 10      # Storage location synced with external device, scanned and imported
        legacy = 11      # Storage location that can be imported

    class DefaultLocationMetadata(PropertySet):
        server = Property()
        folder = Property()
        subfolder = Property(default='{date}')
        auto_tag = Property(bool, default=False)
        auto_user = Property(bool, default=False)
        user_id = Property(int)
        keep_original = Property(bool, default=False)
        source = Property()
        hidden = Property(bool)
        access = Property(int)
        tags = Property(list)
        read_only = Property(bool)
        wants = Property(list)  # FileDescriptor.Purpose

    id = Column(Integer, primary_key=True)
    type = Column(Integer, nullable=False)
    name = Column(String(128), nullable=False)
    data = Column(String(512))


# Location Groups
IMPORTABLE = (
    Location.Type.drop_folder,
    Location.Type.upload,
    Location.Type.legacy,
    Location.Type.mobile,
)
SCANNABLE = (
    Location.Type.drop_folder,
    Location.Type.mobile,
)
EXPORTABLE = (
    Location.Type.export,
)


class User(Base):
    __tablename__ = 'user'

    class Status(IntEnum):
        disabled = 0
        enabled = 1

    class Class(IntEnum):
        normal = 0
        admin = 1
        guest = 2

    class DefaultConfig(PropertySet):
        pass

    id = Column(Integer, primary_key=True)
    status = Column(Integer, nullable=False, default=Status.enabled)
    name = Column(String(128), nullable=False)
    fullname = Column(String(128), nullable=False)
    password = Column(String(128), nullable=False)
    user_class = Column(Integer, nullable=False, default=Class.normal)
    config = Column(String(16332))


class ImportJob(Base):
    __tablename__ = 'import_job'

    class State(IntEnum):
        new = 0
        active = 1
        done = 2 
        failed = 3
        hold = 4  # don't start yet
        keep = 5  # don't clean this

    class DefaultImportJobMetadata(PropertySet):
        tags = Property(list)
        metadata = Property() # just a string, don't open it
        error = Property()
        hidden = Property(bool, default=False)
        access = Property(int, default=0)  # Private
        delete_ts = Property()
        source = Property()

    id = Column(Integer, primary_key=True)
    create_ts = Column(DateTime(timezone=True), default=func.now())
    update_ts = Column(DateTime(timezone=True), onupdate=func.now())
    path = Column(String(256), nullable=False)
    state = Column(Integer, nullable=False, default=State.new)
    data = Column(String(8192))
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    location_id = Column(Integer, ForeignKey('location.id'), nullable=False)
    entry_id = Column(Integer, ForeignKey('entry.id'))

    user = relationship(User)
    location = relationship(Location)


class ExportJob(Base):
    __tablename__ = 'export_job'

    class State(IntEnum):
        new = 0
        active = 1
        done = 2 
        failed = 3

    class DefaultExportJobMetadata(PropertySet):
        path = Property()
        want = Property(int)  # FileDescriptor.Purpose

    id = Column(Integer, primary_key=True)
    create_ts = Column(DateTime(timezone=True), default=func.now())
    update_ts = Column(DateTime(timezone=True), onupdate=func.now())
    deliver_ts = Column(DateTime(timezone=True))
    state = Column(Integer, nullable=False, default=State.new)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    location_id = Column(Integer, ForeignKey('location.id'), nullable=False)
    entry_id = Column(Integer, ForeignKey('entry.id'))
    data = Column(String(8192))

    location = relationship(Location)
    entry = relationship('Entry')
    user = relationship(User)


class Entry(Base):
    __tablename__ = 'entry'

    class State(IntEnum):
        new = 0
        online = 1 
        offline = 2 
        failed = 3
        delete = 4
        deleted = 5

    class DefaultMetadata(PropertySet):
        title = Property()
        creator = Property()
        comment = Property()

    class DefaultPhysicalMetadata(PropertySet):
        pass

    class Access(IntEnum):
        private = 0
        users = 1
        common = 2
        public = 3

    class Type(IntEnum):
        image = 0
        video = 1
        audio = 2
        other = 3

    id = Column(Integer, primary_key=True)
    original_filename = Column(String(256))
    export_filename = Column(String(256))
    source = Column(String(64))
    type = Column(Integer, nullable=False, default=Type.image)
    state = Column(Integer, nullable=False, default=State.new)
    hidden = Column(Boolean, nullable=False, default=False)
    delete_ts = Column(DateTime(timezone=True))
    access = Column(Integer, nullable=False, default=Access.private)
    create_ts = Column(DateTime(timezone=True), default=func.now())
    update_ts = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    taken_ts = Column(DateTime(timezone=True), default=func.now())
    latitude = Column(Float)
    longitude = Column(Float)

    data = Column(String(32768))
    physical_data = Column(String(32768))
    files = Column(String(4096))
    tags = Column(String(4096))

    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    parent_entry_id = Column(Integer, ForeignKey('entry.id'))

    user = relationship(User)
    parent_entry = relationship('Entry')


class Tag(Base):
    __tablename__ = 'tag'

    id = Column(String(128), primary_key=True)
    color = Column(Integer, default=0)


class RemoteCopy(Base):
    __tablename__ = 'remote_copy'

    id = Column(Integer, primary_key=True)
    entry_id = Column(Integer, ForeignKey('entry.id'), nullable=False)
    location_id = Column(Integer, ForeignKey('location.id'), nullable=False)
    path = Column(String(256), nullable=False)
    deliver_ts = Column(DateTime(timezone=True))


register_metadata_schema(Location.DefaultLocationMetadata)
register_metadata_schema(ImportJob.DefaultImportJobMetadata)
register_metadata_schema(Entry.DefaultMetadata)
register_metadata_schema(Entry.DefaultPhysicalMetadata)
register_metadata_schema(User.DefaultConfig)
