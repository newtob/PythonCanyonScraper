import datetime
import os
from contextlib import closing

from bs4 import BeautifulSoup
from google.cloud import bigquery
from requests import get
from requests.exceptions import RequestException
from twilio.rest import Client



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
        'SELECT UID FROM `CanyonOutletBikeSaleData.CanyonOutletGBPBikeSaleDataTable` ')
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


def get_bigquery_bike_list(client: bigquery.client.Client) -> list:
    """xx"""
    get_bikes_query = (
        'SELECT * FROM `CanyonOutletBikeSaleData.CanyonOutletGBPBikeSaleDataTable` ')
    query_job = client.query(get_bikes_query)  # API request
    rows = query_job.result()  # Waits for query to finish


def InsertintoDB(Bikelist: list, client: bigquery.client.Client) -> bool:
    """take a list of bike sales, output them into the DB
    Setup DB connection, for loop through insert rows
    """

    table_id = "CanyonOutletBikeSaleData.CanyonOutletGBPBikeSaleDataTable"
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


def main(client: bigquery.Client) -> None:
    """flow: get bikes from BQ -> run field adder -> insert back into BQ
    1) get_bigquery_bike_list
    2) addGBPprices 
    3) InsertintoDB
    TODO write control flow, 
    TODO decide if data should be put into a entirely new table""" 
    pass



if __name__ == "__main__":
    myClient = bigquery.Client.from_service_account_json('./canyonscraper-54d54af48066.json')
    main(myClient)