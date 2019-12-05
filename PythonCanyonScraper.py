import datetime
import os
from contextlib import closing

from bs4 import BeautifulSoup
from google.cloud import bigquery
from requests import get
from requests.exceptions import RequestException
from twilio.rest import Client


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

    for s in html.select('span'):
        if s.get('class') is not None and 'productTile__productName' in s.get('class'):
            bikeDataInfoList: list = []
            BikeName: str
            UID: str
            BikeName = s.text.replace("\\n", "").strip()
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

def addGBPprices(bikeData: list) -> list:
    """data struct starts of as a list of the following:[UID, BikeName, orig price, sale price, date found]
    Then gbp_orig_price and gbp_sale_price and Percent_Discount is appended to the end"""
    bikeDataAddition: list = bikeData
    gbp_orig_price: int = 0

    for i, bike in enumerate(bikeData):
        gbp_orig_price = int(bike[2][1:-3])
        bikeDataAddition[i].append(gbp_orig_price)

        gbp_sale_price = int(bike[3][1:-3])
        bikeDataAddition[i].append(gbp_sale_price)

        bikeDataAddition[i].append(round((gbp_sale_price/gbp_orig_price)*100))


    return bikeDataAddition


def checkBikeIsntLoadedAlready(bikeData: list, client: bigquery.client.Client) -> list:
    """Gets the UID's from the database and checks the newly scraped UID's, returning only the new ones"""

    QUERY = (
        'SELECT UID FROM `CanyonOutletBikeSaleData.CanyonOutletBikeSaleDataTable` ')
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

def check_bike_list(Bikelist: list) -> list:
    """check structure is sound"""
    brokenbikedata: list = []

    for bike in Bikelist:
        if type(bike[0]) is str and type(bike[1]) is str and type(bike[2]) is str and type(bike[3]) is str and type(bike[4]) is datetime.datetime:
            pass
        else:
            brokenbikedata.append(bike)

    return brokenbikedata


def InsertintoDB(Bikelist: list, client: bigquery.client.Client) -> bool:
    """take a list of bike sales, output them into the DB
    Setup DB connection, for loop through insert rows
    """

    table_id = "CanyonOutletBikeSaleData.CanyonOutletBikeSaleDataTable"
    table = client.get_table(table_id)  # Make an API request.
    rows_to_insert = Bikelist

    checked_bike_list = check_bike_list(Bikelist)
    if not len(checked_bike_list) == 0:
        print ("ERROR, scrape failed, the following bike failed : " + checked_bike_list)

    errors = client.insert_rows(table, rows_to_insert)  # Make an API request.
    if errors != []:
        print("ERROR: New rows have not been added, errors = " + str(errors))
        return False
    else:
        print("bike rows successfully inserted into BQ = " + str(len(Bikelist)))
        return True


# def env_vars():
#     """for secrets and CICD"""
#     # return os.environ.get('twilio_auth_token', 'Specified environment variable, twilio_auth_token, is not set.')
#     return os.environ.get('twilio_auth_token', None)


def BikelisttoSMSAdvanced(bikelist: list) -> bool:
    """from this page: https://www.twilio.com/docs/sms/quickstart/python"""

    account_sid = os.environ.get('TWILIO_ACCOUNT_SID', None)
    auth_token = os.environ.get('twilio_auth_token', None)
    if auth_token is None:
        print("auth token isn't present, check env variables")
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
            print(message.sid)
    return True


def main(client: bigquery.Client, saveHTML: bool, test: bool = False) -> None:
    """main method, checks to see if its an off line 'test' or if it needs to get data from the web.
    Saves a new set of html if it does go out to get it.
    Parses the output and should then save to cloud db."""
    if test:
        with open('examplePageAeroadSizeM.html', 'r') as file:
            raw_html = str(file.read())
        with open('examplePageAllBikes.html', 'r') as fileAll:
            raw_max_html = str(fileAll.read())
    else:
        raw_html = simple_get('https://www.canyon.com/en-gb/outlet/road-bikes/?cgid=outlet-road&\
        prefn1=pc_familie&prefn2=pc_outlet&prefn3=pc_rahmengroesse&prefv1=Aeroad&prefv2=true&prefv3=M')
        raw_max_html = simple_get('https://www.canyon.com/en-gb/outlet/road-bikes/?\
        cgid=outlet-road&prefn1=pc_outlet&prefv1=true')
        if raw_html == "none" or raw_max_html == "none":
            print("Critical error: no return from website")
            exit(-1)
        elif saveHTML:
            with open("./latestAeroadSizeM.html", 'w') as out_file:
                out_file.writelines(raw_html)
            with open("./latestAllBikes.html", 'w') as out_max_file:
                out_max_file.writelines(raw_max_html)

    # Cycle for Aeroad Size M
    AearoadBikelistToCheck = addGBPprices(parseSearch(raw_html))
    BikelistToSMS = checkBikeIsntLoadedAlready(AearoadBikelistToCheck, client)
    if checkBikeIsntLoadedAlready:
        BikelisttoSMSAdvanced(BikelistToSMS)

    # Cycle for All bikes
    BikelistToCheck = parseSearch(raw_max_html)
    BikelistToInsert = checkBikeIsntLoadedAlready(BikelistToCheck, client)
    if BikelistToInsert:
        InsertintoDB(BikelistToInsert, client)


def __init__():
    pass


if __name__ == "__main__":
    test = True
    # test = False
    myClient = bigquery.Client.from_service_account_json('./canyonscraper-54d54af48066.json')
    main(myClient, test, True)


def PythonCanyonScraper(event, context) -> None:
    """Launch method for Cloud Function"""
    Prod_test = False
    client = bigquery.Client()
    main(client, Prod_test, False)
