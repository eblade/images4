
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
        drop_folder = 0
        image = 1
        video = 2 
        audio = 3
        other = 4
        proxy = 5
        thumb = 6
        upload = 7
        export = 8

    class DefaultLocationMetadata(PropertySet):
        server = Property()
        folder = Property()
        subfolder = Property(default='{date}')
        auto_tag = Property(bool, default=False)
        auto_user = Property(bool, default=False)
        user_id = Property()
        keep_original = Property(bool, default=False)

    id = Column(Integer, primary_key=True)
    type = Column(Integer, nullable=False)
    name = Column(String(128), nullable=False)
    data = Column(String(512))


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
        hold = 4

    class DefaultImportJobMetadata(PropertySet):
        tags = Property(list)
        metadata = Property() # just a string, don't open it
        error = Property()
        hidden = Property(bool, default=False)
        access = Property(int, default=0)  # Private
        delete_ts = Property()

    id = Column(Integer, primary_key=True)
    create_ts = Column(DateTime(timezone=True), default=func.now())
    update_ts = Column(DateTime(timezone=True), onupdate=func.now())
    path = Column(String(256), nullable=False)
    state = Column(Integer, nullable=False, default=State.new)
    data = Column(String(8192))
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    location_id = Column(Integer, ForeignKey('location.id'), nullable=False)

    user = relationship(User)
    location = relationship(Location, backref=backref('import_jobs', lazy='dynamic'))


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


register_metadata_schema(Location.DefaultLocationMetadata)
register_metadata_schema(ImportJob.DefaultImportJobMetadata)
register_metadata_schema(Entry.DefaultMetadata)
register_metadata_schema(Entry.DefaultPhysicalMetadata)
register_metadata_schema(User.DefaultConfig)
