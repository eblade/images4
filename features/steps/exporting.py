import logging
from behave import *
from hamcrest import *
from hamcrest.library.collection.issequence_containinginanyorder import contains_inanyorder

from images import ExportJob, EXPORTABLE
from images.export_job import ExportJobDescriptor, create_export_job, get_export_jobs_by_entry_id
from images.location import get_location_by_name, get_locations_by_type
from images.user import get_user_by_id
from images.entry import EntryDescriptor, get_entry_by_source

@when('the user creates a specific set of export jobs')
def step_impl(context):
    for row in context.table:
        data = {key: row[key] for key in context.table.headings}
        data['location'] = get_location_by_name(data.pop('location'))
        data['entry'] = EntryDescriptor(id=data.pop('entry_id'))
        ejd = ExportJobDescriptor(**data)
        md = ExportJob.DefaultExportJobMetadata(**data)
        ejd.metadata = md
        create_export_job(ejd)

@then('the entry with id {entry_id:d} should have the following export jobs')
def step_impl(context, entry_id):
    expected_jobs = [
        {key: int(row[key]) if key.endswith('_id') else row[key]
         for key in context.table.headings}
        for row in context.table 
    ]

    actual_jobs = [
        dict(
            entry_id = job.entry.id if job.entry is not None else None,
            location = job.location.name if job.location is not None else None,
            path = job.metadata.path if job.metadata is not None else None,
            user = get_user_by_id(job.user_id).name,
        )
        for job in get_export_jobs_by_entry_id(entry_id).entries
    ]

    print(get_export_jobs_by_entry_id(entry_id).to_json())
    assert_that(actual_jobs, contains_inanyorder(*expected_jobs))

@then('possible export destinations should be as follows')
def step_impl(context):
    expected_locations = [row['name'] for row in context.table]

    feed = get_locations_by_type(*EXPORTABLE)
    actual_locations = [location.name for location in feed.entries]
    
    assert_that(actual_locations, contains_inanyorder(*expected_locations))
