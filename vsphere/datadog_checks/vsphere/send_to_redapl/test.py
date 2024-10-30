import time

import requests
from redapl_pb2 import RedaplEvent
from resource_pb2 import RawResourceV3
from struct_pb2 import Value
from timestamp_pb2 import Timestamp

# Create RawResourceV3 message
raw_resource = RawResourceV3()
raw_resource.org_id = 2
raw_resource.type = "vsphere_vsan_cluster"
raw_resource.name = "example_name"

data = {
    'name': 'John Doe',
    'vcenter_server': '127.0.0.1',
    'tags': ['resource_type:example_tag'],
    'size_used': 1234567890,
    'size_total': 9876543210,
    'latency': 0.123,
    'requests': 1000,
    'cost': 123.45,
    'num_hosts': 5,
}
for i, v in data.items():
    field_value = Value()
    if isinstance(v, str):
        field_value.string_value = v
    elif isinstance(v, (int, float)):  # Handle numbers as double values
        field_value.number_value = v
    raw_resource.fields_by_name[i].CopyFrom(field_value)


now = int(time.time())
seen_at = Timestamp()
seen_at.seconds = now
raw_resource.seen_at.CopyFrom(seen_at)

expire_at = Timestamp()
expire_at.seconds = now + 86400  # Expire after 24 hours
raw_resource.expire_at.CopyFrom(expire_at)

raw_resource.version = 1
raw_resource.tiebreaker = 123
raw_resource.scope = "example_scope"

# Create RedaplEvent message
redapl_event = RedaplEvent()
redapl_event.source = "RawResourceV3"
redapl_event.message = raw_resource.SerializeToString()

# Serialize RedaplEvent message to bytes
serialized_redapl_event = redapl_event.SerializeToString()
# print('serialized_redapl_event:', serialized_redapl_event)

headers = {
    'dd-api-key': '<INSERT API KEY>',
    'Content-Type': 'application/x-protobuf',
}

response = requests.post(
    'https://intake.profile.datad0g.com/api/v2/genresources', headers=headers, data=serialized_redapl_event
)

print(f"Response Code: {response.status_code}")
print(f"Response Body: {response.text}")
