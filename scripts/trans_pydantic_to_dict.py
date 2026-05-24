import jsonref
import json
from pydantic import BaseModel

def trans(src: type[BaseModel]):
    json_schema = jsonref.replace_refs(src.model_json_schema(), proxies=False)
    json_schema = json.loads(json.dumps(json_schema))
    json_schema.pop('$defs', None)
    return json_schema['properties']