import json
import urllib.request
from google.transit import gtfs_realtime_pb2

URL = 'https://data.calgary.ca/download/jhgn-ynqj/alerts.pb'
data = urllib.request.urlopen(URL).read()

feed = gtfs_realtime_pb2.FeedMessage()
feed.ParseFromString(data)

filtered = []
for entity in feed.entity:
    if not entity.HasField('alert'):
        continue
    alert = entity.alert
    for ie in alert.informed_entity:
        if ie.route_id in ('201', '202'):
            filtered.append({
                'entity_id': entity.id,
                'route_id': ie.route_id,
                'header_text': alert.header_text.translation[0].text if alert.header_text.translation else "",
                'description': alert.description_text.translation[0].text if alert.description_text.translation else "",
                'start': getattr(alert.active_period[0], 'start', None) if alert.active_period else None,
                'end': getattr(alert.active_period[0], 'end', None) if alert.active_period else None
            })
            break

# Prepare a list with only route_id and description
output = []
for item in filtered:
    output.append({
        'route_id': item['route_id'],
        'description': item['description']
    })

# Write the list to current_alerts.json
with open('current_alerts.json', 'w') as f:
    json.dump(output, f, indent=2)

# Build HTML output
output_html = "<ul>"
for item in filtered:
    output_html += f"<li><b>Route {item['route_id']}:</b> {item['description']}</li>"
output_html += "</ul>"

with open('current_alerts.html', 'w') as f:
    f.write(output_html)

print(output_html)

# Print the JSON to the console for local debugging
#with open('current_alerts.json', 'r') as f:
#    print(f.read())

