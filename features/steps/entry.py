from behave import *

from images.entry import EntryDescriptor, create_entry, update_entry_by_id, delete_entry_by_id, EntryQuery, get_entries

@given('an entry called {entry_name}')
def step_impl(context, entry_name):
    ed = EntryDescriptor(original_filename=entry_name, source='test')
    ed = create_entry(ed, system=True)
    context.entry = ed
