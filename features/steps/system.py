from behave import *
import os, shutil
from bottle import request

from images import api, scanner, location, entry, tag, user, import_job, delete, export_job
from images.setup import Setup

@given('a system specified by "{ini_file}"')
def step_impl(context, ini_file):
    try:
        shutil.rmtree('/tmp/images_behave')
    except:
        pass
    os.mkdir('/tmp/images_behave')
    context.setup = Setup(os.path.join('features', ini_file))
    context.setup.create_database_tables()
    context.setup.add_users()
    context.setup.add_locations()
    context.setup.add_tags()
    
    def tear_down(context):
        context.setup = None
        request.user = None
        shutil.rmtree('/tmp/images_behave')

    context.tear_down_scenario.append(tear_down)
