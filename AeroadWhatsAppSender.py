from requests import get, post
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup
from google.cloud import bigquery
import datetime
from twilio.twiml.messaging_response import Body, Message, Redirect, MessagingResponse
from twilio.rest import Client


def simple_get(url: str) -> str:
    """Attempts to get the content at `url` by making an HTTP GET request.
    If the content-type of response is some kind of HTML/XML, return the text content, otherwise return None."""
    try:
        with closing(get(url, stream=True)) as resp:
            if is_good_response(resp):
                # TODO response.text vs response.content
                return resp.text
            else:
                return "none"
    except RequestException as e:
        log_error('Error during requests to {0} : {1}'.format(url, str(e)))
        return "none"


def is_good_response(resp):
    """Returns True if the response seems to be HTML, False otherwise.    """
    content_type = resp.headers['Content-Type'].lower()
    return (resp.status_code == 200
            and content_type is not None
            and content_type.find('html') > -1)


def log_error(e) -> None:
    """TODO: do something else with a HTML requests error"""
    print(e)


def parseSearch(raw_html: str) -> list:
    """Find three elements in the web page, bike name, orig price and sale price, output them
    data struct is a list of the following:[UID, BikeName, orig price, sale price, date found]
    TODO: make search for Aeraod size M models work"""

    bikeDataListofLists = []
    BikeNamelist, OrigPricelist, SalePricelist = [], [], []
    try:
        html: BeautifulSoup = BeautifulSoup(raw_html, 'html.parser')
    except TypeError as e:
        print("Type Error parsing raw html = " + e)
        exit(-1)

    for s in html.select('span'):
        if s.get('class') is not None and 'productTile__productName' in s.get('class'):
            # if 'productTile__productName' in s.get('class'):
            bikeDataInfoList = []
            BikeName, UID = None, None
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
    """sample from https://www.twilio.com/docs/sms/twiml"""

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
    print(" Bike list to message ")
    print(bikelist)

    # Your Account Sid and Auth Token from twilio.com/console
    # DANGER! This is insecure. See http://twil.io/secure
    account_sid = 'AC466560e3a5db18f39b3943c401183e48'
    auth_token = '86ea23282a969a837acb67bb6bd09e41'
    SMSclient = Client(account_sid, auth_token)

    for bike in bikelist:
        if bike[1]:
            messageData = "a new " + str(bike[1]) + " has appeared, Size M"

            message = SMSclient.messages \
                .create(
                body=messageData,
                from_='+16506459228',
                to='+447823772665')

    print(message.sid)


def BikelisttoMessage(bikelist: list) -> bool:
    """Sends bikes to Whatapp via Twilio in a for loop"""
    print(" Bike list to message ")
    print(bikelist)

    for bike in bikelist:
        if bike[1]:
            messageData = "a new " + str(bike[1]) + " has appeared, Size M"
            print(messageData)
            try:
                with closing(post(
                        'https://api.twilio.com/2010-04-01/Accounts/AC466560e3a5db18f39b3943c401183e48/Messages.json',
                        auth=('AC466560e3a5db18f39b3943c401183e48', '86ea23282a969a837acb67bb6bd09e41'),
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

    # TODO delete the returns above
    return True


def main(client: bigquery.Client, test: bool, saveHTML: bool) -> None:
    """main method, checks to see if its an off line 'test' or if it needs to get data from the web.
    Saves a new set of html if it does go out to get it.
    Parses the output and should then save to cloud db."""
    if test:
        with open('examplePageAeroadSizeM.html', 'r') as file:
            raw_html = str(file.read())
        with open('examplePageAllBikes.html', 'r') as fileAll:
            raw_max_html = str(fileAll.read())
        # TODO remove me
        with open('examplePageAllBikes.html', 'r') as fileAll:
            raw_html = str(fileAll.read())
    else:
        raw_html = simple_get(
            'https://www.canyon.com/en-gb/outlet/road-bikes/?cgid=outlet-road&prefn1=pc_familie&prefn2=pc_outlet&prefn3=pc_rahmengroesse&prefv1=Aeroad&prefv2=true&prefv3=M')
        raw_max_html = simple_get(
            'https://www.canyon.com/en-gb/outlet/road-bikes/?cgid=outlet-road&prefn1=pc_outlet&prefv1=true')
        if raw_html == "none" or raw_max_html == "none":
            print("no return from website")
            exit(-1)
        elif saveHTML:
            with open("./latestAeroadSizeM.html", 'w') as out_file:
                out_file.writelines(raw_html)
            with open("./latestAllBikes.html", 'w') as out_max_file:
                out_max_file.writelines(raw_max_html)

    # # TODO working code below 4 lines ##########
    # BikelistToCheck = parseSearch(raw_html)
    # # print(BikelistToCheck)
    # BikelistToWhatsApp = checkBikeIsntLoadedAlready(BikelistToCheck, client)
    # BikelisttoMessage(BikelistToWhatsApp)

    # TODO Remove Test code while i don't have the API json key
    # print(BikelisttoMessage(parseSearch(raw_html)))
    # print(BikelisttoSMS(parseSearch(raw_html)))
    print(BikelisttoSMSAdvanced(parseSearch(raw_html)))


if __name__ == "__main__":
    test = True
    # test = False
    ######### TODO put this next line back in!! and remove the client = None ######
    # client = bigquery.Client.from_service_account_json('./canyonscraper-54d54af48066.json')
    client = None
    main(client, test, True)


def PythonCanyonScraper(event, context) -> None:
    test = False
    client = bigquery.Client()
    main(client, test, False)
