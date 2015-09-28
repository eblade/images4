import shutil, os
from bottle import request

from images import api, scanner, location, entry, tag, user, import_job, delete, export_job

from images.setup import Setup
from images.entry import delete_entry_by_id
from images.tag import delete_tag_by_id
from images.location import delete_location_by_id

def before_all(context):
    try:
        shutil.rmtree('/tmp/images_behave')
    except:
        pass
    os.mkdir('/tmp/images_behave')
    context.setup = Setup('features/images.ini', debug=True)
    context.setup.create_database_tables()
    context.setup.add_users()
    context.setup.add_locations()
    context.setup.add_tags()

def after_all(context):
    shutil.rmtree('/tmp/images_behave')

def before_tag(context, tag):
    if tag == 'entries':
        context.entries = {}
    if tag == 'tags':
        context.tags_ = []
    if tag == 'locations':
        context.locations = []

def after_tag(context, tag):
    if tag == 'entries':
        for entry in context.entries.values():
            delete_entry_by_id(entry.id, system=True)
    if tag == 'tags':
        for tag_ in context.tags_:
            delete_tag_by_id(tag_)
    if tag == 'locations':
        for location in context.locations:
            delete_location_by_id(location.id)

def after_scenario(context, scenario):
    request.user = None
