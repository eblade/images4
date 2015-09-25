
from images.setup import Setup


def before_all(context):
    context.setup = Setup('features/images.ini', debug=True)
    context.setup.create_database_tables()
    context.setup.add_users()
    context.setup.add_locations()
    context.setup.add_tags()

def after_all(context):
    pass
