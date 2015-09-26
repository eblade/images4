import logging
from behave import *

from images.tag import TagDescriptor, add_tag, ensure_tag, get_tag_by_id
from images.entry import EntryDescriptor, create_entry, update_entry_by_id, delete_entry_by_id, EntryQuery, get_entries

@given('a tag name "{tagname}"')
def step_impl(context, tagname):
    context.tagname = tagname

@given('a color number {color_number}')
def step_impl(context, color_number):
    context.color_number = int(color_number)

@given('no color number')
def step_impl(context):
    context.color_number = None

@given('the tag is already added')
def step_impl(context):
    add_tag(TagDescriptor(id=context.tagname, color_id=context.color_number))
    context.tags_.append(context.tagname)


@when('the new tag is added')
def step_impl(context):
    add_tag(TagDescriptor(id=context.tagname, color_id=context.color_number))
    context.tags_.append(context.tagname)

@when('the tag is ensured')
def step_impl(context):
    ensure_tag(context.tagname)
    if context.tagname not in context.tags_: context.tags_.append(context.tagname)

@then('the tag should be there')
def step_impl(context):
    assert get_tag_by_id(context.tagname)


@then('the color should be as specified')
def step_impl(context):
    assert get_tag_by_id(context.tagname).color_id == context.color_number

@then('the color should be set')
def step_impl(context):
    assert get_tag_by_id(context.tagname).color_id is not None


# Tagging Entries

@given('a new entry called {entry_name}')
def step_impl(context, entry_name):
    ed = EntryDescriptor(original_filename=entry_name)
    context.entries[entry_name] = create_entry(ed, system=True)

@when('the tag "{tag_name}" is added to the entry {entry_name}')
def step_impl(context, tag_name, entry_name):
    ed = context.entries[entry_name]
    ed.tags.append(tag_name)

@when('the entry {entry_name} is updated')
def step_impl(context, entry_name):
    ed = context.entries[entry_name]
    context.entries[entry_name] = update_entry_by_id(ed.id, ed, system=True)

@then('the entry {entry_name} should have the tag "{tag_name}"')
def step_impl(context, entry_name, tag_name):
    ed = context.entries[entry_name]
    assert tag_name in ed.tags

@then('the entry {entry_name} should not have the tag "{tag_name}"')
def step_impl(context, entry_name, tag_name):
    ed = context.entries[entry_name]
    assert not tag_name in ed.tags

@then('a search for the tag "{tag_name}" should give {hits} hit')
@then('a search for the tag "{tag_name}" should give {hits} hits')
def step_impl(context, tag_name, hits):
    q = EntryQuery(include_tags=[tag_name])
    result = get_entries(q, system=True)
    logging.info("Gave %i results", result.total_count)
    assert result.total_count == int(hits)
