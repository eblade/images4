import logging
from behave import *

from images import Location, Entry
from images.location import LocationDescriptor, create_location, get_locations_by_type


@given('a specific set of locations')
def step_impl(context):
    for row in context.table:
        md = Location.DefaultLocationMetadata(
            folder = row['path'],
            user_id = int(row['user id']),
            keep_original = (row['keep original'] == 'yes'),
            access = getattr(Entry.Access, row['access']),
        )
        ld = LocationDescriptor(
            name = row['name'],
            type = getattr(Location.Type, row['type']),
            metadata = md,
        )
        create_location(ld)

@then(u'there should be a "{type}" location named "{name}"')
def step_impl(context, type, name):
    lds = get_locations_by_type(getattr(Location.Type, type))
    by_name = {ld.name: ld for ld in lds.entries}
    assert name in by_name.keys()
    context.that_location = by_name[name]

@then(u'that location should be mounted at "{path}"')
def step_impl(context, path):
    assert context.that_location.metadata.folder == path

@then(u'that location should have {access} access')
def step_impl(context, access):
    assert context.that_location.metadata.access == getattr(Entry.Access, access)

@then(u'that location should belong to user {user_id}')
def step_impl(context, user_id):
    assert context.that_location.metadata.user_id == int(user_id)

@then(u'that location should keep originals')
def step_impl(context):
    assert context.that_location.metadata.keep_original

@then(u'that location should not keep originals')
def step_impl(context):
    assert not context.that_location.metadata.keep_original

