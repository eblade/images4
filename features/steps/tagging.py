import logging
from behave import *

from images.tag import TagDescriptor, add_tag, ensure_tag, get_tag_by_id
from images.entry import EntryQuery, get_entries, update_entry_by_id, get_entry_by_source

@given('a tag name "{tag_name}"')
def step_impl(context, tag_name):
    context.tag_name = tag_name

@given('a color number {color_number}')
def step_impl(context, color_number):
    context.color_number = int(color_number)

@given('no color number')
def step_impl(context):
    context.color_number = None

@given('the tag is already added')
def step_impl(context):
    add_tag(TagDescriptor(id=context.tag_name, color_id=context.color_number))


@when('the new tag is added')
def step_impl(context):
    add_tag(TagDescriptor(id=context.tag_name, color_id=context.color_number))

@when('the tag is ensured')
def step_impl(context):
    ensure_tag(context.tag_name)

@then('the tag should be there')
def step_impl(context):
    assert get_tag_by_id(context.tag_name)


@then('the color should be as specified')
def step_impl(context):
    assert get_tag_by_id(context.tag_name).color_id == context.color_number

@then('the color should be set')
def step_impl(context):
    assert get_tag_by_id(context.tag_name).color_id is not None


# Tagging Entries

@given('the entry {entry_name} has the tag "{tag_name}"')
@when('the tag "{tag_name}" is added to the entry {entry_name}')
def step_impl(context, tag_name, entry_name):
    ed = get_entry_by_source('test', entry_name, system=True)
    ed.tags.append(tag_name)
    update_entry_by_id(ed.id, ed, system=True)

@when('the tag "{tag_name}" is removed from the entry {entry_name}')
def step_impl(context, tag_name, entry_name):
    ed = get_entry_by_source('test', entry_name, system=True)
    ed.tags.remove(tag_name)
    update_entry_by_id(ed.id, ed, system=True)


@then('the entry {entry_name} should have the tag "{tag_name}"')
def step_impl(context, entry_name, tag_name):
    ed = get_entry_by_source('test', entry_name, system=True)
    assert tag_name in ed.tags

@then('the entry {entry_name} should not have the tag "{tag_name}"')
def step_impl(context, entry_name, tag_name):
    ed = get_entry_by_source('test', entry_name, system=True)
    assert not tag_name in ed.tags

@then('a search for the tag "{tag_name}" should give {hits} hit')
@then('a search for the tag "{tag_name}" should give {hits} hits')
def step_impl(context, tag_name, hits):
    q = EntryQuery(include_tags=[tag_name])
    result = get_entries(q, system=True)
    logging.info("Gave %i results", result.total_count)
    assert result.total_count == int(hits)
