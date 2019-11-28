from requests import get, post
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup
from google.cloud import bigquery
import datetime, os
from twilio.twiml.messaging_response import Body, Message, Redirect, MessagingResponse
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
                # for i in bikeDataInfoList:
                #     print(str(i))
                if bikeDataInfoList[1] is not None and bikeDataInfoList[2] is not None:
                    insertTimeStamp = (datetime.datetime.now())
                    bikeDataInfoList.insert(4, insertTimeStamp)

                    bikeDataListofLists.append(bikeDataInfoList)
                else:
                    print("partial scape, got one of orig price or sale price, but not both")
    return bikeDataListofLists


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


def BikelisttoSMS(bikelist: list) -> bool:
    """sample from https://www.twilio.com/docs/sms/twiml
    SAMPLE DOESNT WORK. NOT REQUIRED, USE SMSAdvanced Method"""

    for bike in bikelist:
        if bike[1]:
            messageData = "a new " + str(bike[1]) + " has appeared, Size M"
            print(messageData)

            response = MessagingResponse()
            message = Message()
            message.body(messageData)
            response.append(message)
            response.redirect('https://demo.twilio.com/welcome/sms/')

            print(response)
    return True


def BikelisttoSMSAdvanced(bikelist: list) -> bool:
    """from this page: https://www.twilio.com/docs/sms/quickstart/python"""

    # Your Account Sid and Auth Token from twilio.com/console
    # DANGER! This is insecure. See http://twil.io/secure
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID', None)
    auth_token = os.environ.get('twilio_auth_token', None)
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
            print("complete, exiting after just 1")
            print(message.sid)
    return True


def BikelisttoWhatsAppMessage(bikelist: list) -> bool:
    """Sends bikes to Whatapp via Twilio in a for loop"""
    print(" Bike list to message ")
    print(bikelist)
    authTokentobeFIXED = os.environ.get('twilio_auth_token', None)

    for bike in bikelist:
        if bike[1]:
            messageData = "a new " + str(bike[1]) + " has appeared, Size M"
            print(messageData)
            try:
                with closing(post(
                        'https://api.twilio.com/2010-04-01/Accounts/AC466560e3a5db18f39b3943c401183e48/Messages.json',
                        auth=('AC466560e3a5db18f39b3943c401183e48', authTokentobeFIXED),
                        data=messageData)) as resp:
                    if is_good_response(resp):
                        print("good response from Twilio whatsapp push")
                    else:
                        print("bad response from Twilio whatsapp push")
                    return True
            except RequestException as e:
                log_error('Error during requests to {0} : {1}'.format(url, str(e)))
                return False
        else:
            print("no bike name in list")

    # TODO delete the 2 returns above
    return True


def main(client: bigquery.Client, test: bool, saveHTML: bool) -> None:
    """main method, checks to see if its an off line 'test' or if it needs to get data from the web.
    Saves a new set of html if it does go out to get it.
    Parses the output and should then save to cloud db."""
    if test:
        with open('examplePageAeroadSizeM.html', 'r') as file:
            raw_html = str(file.read())
    else:
        raw_html = simple_get(
            'https://www.canyon.com/en-gb/outlet/road-bikes/?cgid=outlet-road&prefn1=pc_familie&\
            prefn2=pc_outlet&prefn3=pc_rahmengroesse&prefv1=Aeroad&prefv2=true&prefv3=L')

        if raw_html == "none":
            print("no return from website")
            exit(-1)
        elif saveHTML:
            with open("./latestAeroadSizeM.html", 'w') as out_file:
                out_file.writelines(raw_html)

    BikelistToCheck = parseSearch(raw_html)
    print("Bikelist to check")
    print(BikelistToCheck)
    BikelistToMessage = checkBikeIsntLoadedAlready(BikelistToCheck, client)
    print("Bikelist to SMS")
    print(BikelistToMessage)
    BikelisttoSMSAdvanced(BikelistToMessage)

    # Test code if API json key isn't accessible
    # print(BikelisttoSMSAdvanced(parseSearch(raw_html)))


if __name__ == "__main__":
    # test = True
    test = False
    myClient = bigquery.Client.from_service_account_json('./canyonscraper-54d54af48066.json')
    main(myClient, test, True)


def PythonCanyonScraper(event, context) -> None:
    """Launch method for Cloud Function"""
    Prod_test = False
    client = bigquery.Client()
    main(client, Prod_test, False)
