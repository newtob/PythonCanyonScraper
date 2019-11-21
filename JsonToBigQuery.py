import base64, datetime, json
from google.cloud import bigquery

#jsonMsg = '{"insertId":"h8hcjy68u5iox4j4c","jsonPayload":{"logday":"58771","logseconds":"76328.418","offset":"-0.000019108"},"labels":{"compute.googleapis.com/resource_name":"sd-instance-222"},"logName":"projects/stackdriverloggingtest-99/logs/NTP-loopstats","receiveTimestamp":"2019-10-15T21:12:13.962417681Z","resource":{"labels":{"instance_id":"3053653949303827937","project_id":"stackdriverloggingtest-99","zone":"us-central1-a"},"type":"gce_instance"},"timestamp":"2019-10-15T21:12:08.418672557Z"}'
#jsonDict = json.loads(jsonMsg)
#print (f"The jasn dict is {jsonDict}")


def hello_pubsub(event, context):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    client = bigquery.Client()
    #client = bigquery.Client.from_service_account_json('/Users/newtob/PycharmProjects/gcp_cloudFunctions/benscreatedGCP.json')
    table_id = "stackdriverloggingtest-99.Offset_bigquery_dataset.Offset_table"
    Timestamp = datetime.datetime.now()

    # pubsub_message = base64.b64decode(event['jsonPayload']['offset']).decode('utf-8')

    table = client.get_table(table_id)  # Make an API request.
    rows_to_insert = [(Timestamp, event['jsonPayload']['offset'], event['labels']['compute.googleapis.com/resource_name'])]

    errors = client.insert_rows(table, rows_to_insert)  # Make an API request.
    if errors != []:
        print("New rows have not been added, errors.")