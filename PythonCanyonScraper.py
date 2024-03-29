import datetime
import os, sys
from contextlib import closing

from bs4 import BeautifulSoup
from google.cloud import bigquery
from requests import get
from requests.exceptions import RequestException
from twilio.rest import Client

#OT setup - the second one not importing!? 11/Nov/2021
# from opentelemetry import trace
# from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
# from opentelemetry.sdk.trace import TracerProvider
# from opentelemetry.sdk.trace.export import BatchSpanProcessor
# from opentelemetry.trace import Link


def simple_get(url: str) -> str:
    """Attempts to get the content at `url` by making an HTTP GET request.
    If the content-type of response is some kind of HTML/XML, return the text content, otherwise return None."""
    try:
        with closing(get(url, stream=True)) as resp:
            if is_good_response(resp):
                return resp.text
            else:
                return "none"
    except RequestException as e:
        log_error('Error during requests to {0} : {1}'.format(url, str(e)))
        return "none"


def is_good_response(resp) -> bool:
    """Returns True if the response seems to be HTML, False otherwise."""
    content_type = resp.headers['Content-Type'].lower()
    return (resp.status_code == 200
            and content_type is not None
            and content_type.find('html') > -1)


def log_error(e) -> None:
    """TODO: do something else with a HTML requests error"""
    print(e)


def parseSearch(raw_html: str) -> list:
    """Find three elements in the web page, bike name, orig price and sale price, output them
    data struct is a list of the following:[UID, BikeName, orig price, sale price, date found]"""

    bikeDataListofLists: list = []
    BikeNamelist: list = []
    html: BeautifulSoup
    try:
        html = BeautifulSoup(raw_html, 'html.parser')
    except TypeError as e:
        print("Type Error parsing raw html = " + e)
        exit(-1)

    print('in parseSearch just before the html.select(span) bit')

    #new routine
    #The following two lines have been commented, because i don't understand what they wehre doing, 11.Nov.2021
    divCounterInt = 0

    #html.find_all("div",class="productTile__productSummaryLeft")
    #TODO the above command SHOULD WORK. but does not. please, please make it work.

    for s in html.find_all(itemtype='http://schema.org/Product'):
        print('found something')
        print(s)

    for s in html.find_all('div', itemtype=True, recursive=True):
        print(divCounterInt, end=',')
        divCounterInt+=1

        #print('d', end='')
        #print(type(s))
        #print(s.get('itemtype'))
        #print(s['itemtype'])
        print(s.attrs)
        print(s)
        if s.get('itemtype'):
            print('found an itemtype')
        #if s.get('class') is not None and "http://schema.org/Product" in s.get('itemtype'):
        #    print('i found a schema//product')
        #    print( s.data-pid )

    sys.exit()

    #old routine that doesn't parse the new page
    for s in html.select('span'):
        if s.get('class') is not None and 'productTile__productName' in s.get('class'):
            print('found a productTile')
            bikeDataInfoList: list = []
            BikeName: str
            UID: str
            BikeName = s.text.replace("\\n", "").strip()
            ## this next line is broken by the html. it's pulling ajax from above, incorrectly
            ## doesn't work any more
            UID = str(s.previous_element.previous_element.previous_element['data-url']).split("=")[2]

            bikeDataInfoList.insert(0, UID)
            bikeDataInfoList.insert(1, BikeName)

            BikeNamelist.append(BikeName)
            for i, child in enumerate(s.next_element.next_element.next_element.children):
                if child.name == "span":
                    if i == 1:
                        bikeDataInfoList.insert(2, child.text.replace("\\n", "").strip())
                    elif i == 3:
                        bikeDataInfoList.insert(3, child.text.replace("\\n", "").strip())
            if bikeDataInfoList is not None:
                if bikeDataInfoList[1] is not None and bikeDataInfoList[2] is not None:
                    insertTimeStamp = (datetime.datetime.now())
                    bikeDataInfoList.insert(4, insertTimeStamp)
                    bikeDataListofLists.append(bikeDataInfoList)
                else:
                    print("Error: Found either the orig price or sale price, but not both. Can't parse HTML correctly")
    return bikeDataListofLists


def checkBikeIsntLoadedAlready(bikeData: list, client: bigquery.client.Client) -> list:
    """Gets the UID's from the database and checks the newly scraped UID's, returning only the new ones"""

    QUERY = ('SELECT UID FROM `CanyonOutletBikeSaleData.CanyonOutletBikeSaleDataTable` ')
    query_job = client.query(QUERY)  # API request
    rows = query_job.result()  # Waits for query to finish

    ExistingUID: list = []
    for row in rows:
        ExistingUID.append(row.UID)

    UniqueBikestoAdd: list = []
    for individualBike in bikeData:
        if individualBike[0] not in ExistingUID:
            UniqueBikestoAdd.append(individualBike)
    return UniqueBikestoAdd


def InsertintoDB(Bikelist: list, client: bigquery.client.Client) -> bool:
    """take a list of bike sales, output them into the DB
    Setup DB connection, for loop through insert rows
    """

    table_id = "CanyonOutletBikeSaleData.CanyonOutletBikeSaleDataTable"
    table = client.get_table(table_id)  # Make an API request.
    rows_to_insert = Bikelist

    errors = client.insert_rows(table, rows_to_insert)  # Make an API request.
    if errors != []:
        print("ERROR: New rows have not been added, errors = " + str(errors))
        return False
    else:
        print("rows inserted = " + str(len(Bikelist)))
        return True


def env_vars():
    """for secrets and CICD"""
    # return os.environ.get('twilio_auth_token', 'Specified environment variable, twilio_auth_token, is not set.')
    return os.environ.get('twilio_auth_token', None)


def BikelisttoSMSAdvanced(bikelist: list) -> bool:
    """from this page: https://www.twilio.com/docs/sms/quickstart/python"""

    # Your Account Sid and Auth Token from twilio.com/console
    # DANGER! This is insecure. See http://twil.io/secure
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID', None)
    auth_token = os.environ.get('twilio_auth_token', None)

    if auth_token is None:
        print("auth token f*ed")
        exit(-1)
    SMSclient = Client(account_sid, auth_token)
    message: SMSclient

    for bike in bikelist:
        if bike[1]:
            messageData = "a new " + str(bike[1]) + " has appeared on sale for " + bike[3] + " Size M"

            message = SMSclient.messages \
                .create(
                body=messageData,
                from_='+16506459228',
                to='+447823772665')
            # print(message.sid)
    return True

def setupOT ():
    tracer_provider = TracerProvider()
    cloud_trace_exporter = CloudTraceSpanExporter()
    tracer_provider.add_span_processor(
        # BatchSpanProcessor buffers spans and sends them in batches in a
        # background thread. The default parameters are sensible, but can tweaked
        BatchSpanProcessor(cloud_trace_exporter)
    )
    trace.set_tracer_provider(tracer_provider)

    tracer = trace.get_tracer(__name__)
    return tracer


def main(client: bigquery.Client, test: bool, saveHTML: bool) -> None:
    """main method, checks to see if its an off line 'test' or if it needs to get data from the web.
    Saves a new set of html if it does go out to get it.
    Parses the output and should then save to cloud db."""
    #tracer = setupOT ()
    if test:
        print('im in test loop')
        with open('latestAeroadSizeM2.html', 'r') as file:
            raw_html = str(file.read())
            # with tracer.start_span("html read m2_with_attribute") as current_span:
            #     raw_html = str(file.read())
            #     # Add attributes to the spans
            #     current_span.set_attribute("string_attribute", "read html m2")
            #     current_span.set_attribute("int_attribute_stage", 1)
            #     with tracer.start_as_current_span("html read m2 event") as current_span:
            #         current_span.add_event(name="html read m2 event finished")

        with open('latestAllBikes2.html', 'r') as fileAll:
            raw_max_html = str(fileAll.read())
    else:
        raw_html = simple_get('https://www.canyon.com/en-gb/outlet/road-bikes/?cgid=outlet-road&prefn1=pc_familie&prefn2=pc_rahmengroesse&prefv1=Aeroad&prefv2=M')
        raw_max_html = simple_get('https://www.canyon.com/en-gb/outlet/road-bikes/')
        if raw_html == "none" or raw_max_html == "none":
            print("Critical error: no return from website")
            exit(-1)
        elif saveHTML:
            print('im going to save an html')
            with open("./latestAeroadSizeM2.html", 'w', encoding="utf-8") as out_file:
                out_file.writelines(raw_html)
            with open("./latestAllBikes2.html", 'w', encoding="utf-8") as out_max_file:
                out_max_file.writelines(raw_max_html)

    # Cycle for Aeroad Size M
    AearoadBikelistToCheck = parseSearch(raw_html)
    BikelistToSMS = checkBikeIsntLoadedAlready(AearoadBikelistToCheck, client)
    if checkBikeIsntLoadedAlready:
        BikelisttoSMSAdvanced(BikelistToSMS)

    # Cycle for All bikes
    BikelistToCheck = parseSearch(raw_max_html)
    BikelistToInsert = checkBikeIsntLoadedAlready(BikelistToCheck, client)
    if BikelistToInsert:
        InsertintoDB(BikelistToInsert, client)


if __name__ == "__main__":
    test = True
    #test = False
    myClient = bigquery.Client.from_service_account_json('./canyonscraper-54d54af48066.json')
    main(myClient, test, True)


def PythonCanyonScraper(event, context) -> None:
    """Launch method for Cloud Function"""
    Prod_test = False
    client = bigquery.Client()
    main(client, Prod_test, False)
