

import logging, json


metadata_schemas = {}


def register_metadata_schema(metadata_class):
    metadata_schemas[metadata_class.__name__] = metadata_class


def get_metadata_schema(schema):
    return metadata_schemas.get(schema)


def wrap_raw_json(json_string):
    if json_string is None:
        return None
    data = json.loads(json_string)
    schema = data.get('*schema')
    metadata_class = get_metadata_schema(schema)
    if metadata_class is None:
        raise NameError("No such metadata schema '%s'" % schema)
    return metadata_class(data)
