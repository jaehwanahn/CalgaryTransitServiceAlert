import json
import urllib.request
import gzip
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime
from google.transit import gtfs_realtime_pb2

URL = 'https://data.calgary.ca/download/jhgn-ynqj/alerts.pb'

def send_email(subject: str, body: str):
    smtp_server = os.environ.get('SMTP_SERVER')
    smtp_port = int(os.environ.get('SMTP_PORT', '465'))
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASS')
    mail_from = os.environ.get('MAIL_FROM')
    mail_to = os.environ.get('MAIL_TO')  # comma-separated list

    if not (smtp_server and smtp_user and smtp_pass and mail_from and mail_to):
        print("Email not sent: missing SMTP configuration in environment variables.")
        return

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = mail_from
    msg['To'] = [addr.strip() for addr in mail_to.split(',')]
    msg.set_content(body)

    try:
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as smtp:
                smtp.login(smtp_user, smtp_pass)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(smtp_server, smtp_port) as smtp:
                smtp.starttls()
                smtp.login(smtp_user, smtp_pass)
                smtp.send_message(msg)
        print("Notification email sent.")
    except Exception as e:
        print(f"Failed to send email: {e}")

try:
    request = urllib.request.Request(URL)
    request.add_header('User-Agent', 'Mozilla/5.0')
    
    with urllib.request.urlopen(request) as response:
        data = response.read()
    
    # Debug: Check what we received
    print(f"Data length: {len(data)} bytes")
    
    # Try to decompress if gzip
    if data[:2] == b'\x1f\x8b':
        print("Data is gzip-compressed, decompressing...")
        data = gzip.decompress(data)
        print(f"Decompressed length: {len(data)} bytes")
    
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(data)
    
    print(f"Successfully parsed! Found {len(feed.entity)} entities")
    
    # Debug: Check what routes are in the alerts
    for entity in feed.entity:
        if entity.HasField('alert'):
            alert = entity.alert
            print(f"\nAlert entity: {entity.id}")
            print(f"  Informed entities count: {len(alert.informed_entity)}")
            for ie in alert.informed_entity:
                print(f"    Route ID: {ie.route_id if ie.route_id else 'EMPTY'}")
            print(f"  Header: {alert.header_text.translation[0].text if alert.header_text.translation else 'NO HEADER'}")
    
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

    # If no matching alerts, send notification email
    if not filtered:
        subject = "No alerts found for routes 201, 202"
        body = f"No GTFS-RT alerts containing routes 201 or 202 were found.\nChecked at {datetime.utcnow().isoformat()}Z\n\nURL: {URL}"
        send_email(subject, body)

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

    # Print the JSON to the console for local debugging
    with open('current_alerts.json', 'r') as f:
        print(f.read())
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code}")
    print(f"Response: {e.read().decode()}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")