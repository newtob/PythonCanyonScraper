from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup
from google.cloud import bigquery
import datetime


def simple_get(url):
    """Attempts to get the content at `url` by making an HTTP GET request.
    If the content-type of response is some kind of HTML/XML, return the text content, otherwise return None."""
    try:
        with closing(get(url, stream=True)) as resp:
            if is_good_response(resp):
                # TODO response.text vs response.content
                return resp.text
            else:
                return None
    except RequestException as e:
        log_error('Error during requests to {0} : {1}'.format(url, str(e)))
        return None


def is_good_response(resp):
    """Returns True if the response seems to be HTML, False otherwise.    """
    content_type = resp.headers['Content-Type'].lower()
    return (resp.status_code == 200
            and content_type is not None
            and content_type.find('html') > -1)


def log_error(e):
    """TODO: do something else with a HTML requests error"""
    print(e)


def parseSearch(raw_html):
    """Find three elements in the web page, bike name, orig price and sale price, output them
    data struct is a list of the following:[UID, BikeName, orig price, sale price, date found]
    TODO: make search for non Aeraod models work"""

    bikeDataListofLists = []
    BikeNamelist, OrigPricelist, SalePricelist = [], [], []
    try:
        html: BeautifulSoup = BeautifulSoup(raw_html, 'html.parser')
    except TypeError as e:
        print("Type Error parsing raw html = " + e)
        exit(-1)

    for s in html.select('span'):
        # print ("span class is : " + str(s.get('class')))
        if s.get('class') is not None:
            # print("0 = " + str(s.get('class')[0]))

            if 'productTile__productName' in s.get('class'):
                # print("found a productTile__productName" + s.text.replace("\\n", "").strip())
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

    # for i in bikeDataListofLists:
    #    print (str(i))
    # myTimeStamp = str(datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc))
    # return BikeNamelist, OrigPricelist, SalePricelist, myTimeStamp


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


def InsertintoDB(Bikelist, client):
    """take a list of bike sales, output them into the DB
    Setup DB connection, for loop through insert rows"""

    # print("InsertintoDB: starting InsertintoDB method...")
    table_id = "CanyonOutletBikeSaleData.CanyonOutletBikeSaleDataTable"
    table = client.get_table(table_id)  # Make an API request.
    rows_to_insert = Bikelist
    # print("InsertintoDB: setup finished, trying to insert rows...")

    errors = client.insert_rows(table, rows_to_insert)  # Make an API request.
    if errors != []:
        print("New rows have not been added, errors = " + str(errors))
    else:
        print("rows inserted = " + str(len(Bikelist)))

    return True


def main():
    """main method, checks to see if its an off line 'test' or if it needs to get data from the web.
    Saves a new set of html if it does go out to get it.
    Parses the output and should then save to cloud db."""
    if test:
        with open('examplePageAeroadSizeM.html', 'r') as file:
            raw_html = str(file.read())
        with open('examplePageAllBikes.html', 'r') as fileAll:
            raw_max_html = str(fileAll.read())
    else:
        raw_html = simple_get('https://www.canyon.com/en-gb/outlet/road-bikes/?cgid=outlet-road&prefn1=pc_familie&prefn2=pc_outlet&prefn3=pc_rahmengroesse&prefv1=Aeroad&prefv2=true&prefv3=M')
        raw_max_html = simple_get('https://www.canyon.com/en-gb/outlet/road-bikes/?cgid=outlet-road&prefn1=pc_outlet&prefv1=true')
        if raw_html is None or raw_max_html is None:
            print("no return from website")
            exit(-1)
        else:
            with open("./latestAeroadSizeM.html", 'w') as out_file:
                out_file.writelines(raw_html)
            with open("./latestAllBikes.html", 'w') as out_max_file:
                out_max_file.writelines(raw_max_html)

        # print("raw html coming out next: \t" + str(raw_html))
        # print("raw html of all bikes   : \t" + str(raw_html))

    # print("the raw_html type is : \t" + str(type(raw_html)))
    # print("the raw_max_html type is : \t" + str(type(raw_max_html)))

    # this doesn't work now, need to re-implement the Aeroad search later on.
    # print("Aeroad only: \t" + str(parseSearch(raw_html)))
    # print("All bikes: \t\t" + str(parseSearch(raw_max_html)))
    BikelistToCheck = parseSearch(raw_max_html)
    # print(BikelistToCheck)
    client = bigquery.Client.from_service_account_json('./canyonscraper-54d54af48066.json')
    BikelistToInsert = checkBikeIsntLoadedAlready(BikelistToCheck, client)
    # print(BikelistToInsert)
    if BikelistToInsert:
        InsertintoDB(BikelistToInsert, client)


if __name__ == "__main__":
    test = True
    #test = False
    main()