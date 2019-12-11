from google.cloud import bigquery


def addGBPprices(bikeData: list) -> list:
    """data struct starts of as a list of the following:[UID, BikeName, orig price, sale price, date found]
    Then gbp_orig_price and gbp_sale_price and Percent_Discount is appended to the end"""
    bikeDataAddition: list = bikeData
    gbp_orig_price: int = 0
    gbp_sale_price: int = 0
    bike_date_list: list = []
    newbike_list_of_list: list = []

    for i in bikeData:
        bike_date_list.append(i)

    for i, bike in enumerate(bike_date_list):
        gbp_orig_price = (bike[2][1:-3].replace(',', ''))

        gbp_sale_price = (bike[3][1:-3].replace(',', ''))
        if "rom " in gbp_sale_price:
            gbp_sale_price = gbp_sale_price[5:]
        gbp_orig_price = int(gbp_orig_price)
        gbp_sale_price = int(gbp_sale_price)

        newbike_list_of_list.append([bike[0], bike[1], bike[2], bike[3], bike[4], gbp_orig_price, gbp_sale_price, round((gbp_sale_price/gbp_orig_price)*100)])

    return newbike_list_of_list


def get_bigquery_bike_list(client: bigquery.client.Client) -> list:
    """get all from bikes"""
    get_bikes_query = (
        'SELECT * FROM `CanyonOutletBikeSaleData.CanyonOutletBikeSaleDataTable` ')
    query_job = client.query(get_bikes_query)  # API request
    rows = query_job.result()  # Waits for query to finish

    return rows


def InsertintoDB(Bikelist: object, client: object) -> object:
    """take a list of bike sales, output them into the DB
    Setup DB connection, for loop through insert rows
    """

    table_id = "CanyonOutletBikeSaleData.CanyonOutletGBPBikeSaleDataTable"
    table = client.get_table(table_id)  # Make an API request.
    rows_to_insert = Bikelist

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
    3) InsertintoDB"""

    print("get bikes from bigquery")
    bikes = get_bigquery_bike_list(client)
    print("add prices")
    bikes_gbp = addGBPprices(bikes)

    for i in bikes_gbp:
        print(i)
    print(len(bikes_gbp))

    InsertintoDB(bikes_gbp, client)


if __name__ == "__main__":
    myClient = bigquery.Client.from_service_account_json('./canyonscraper-ee35f3c9cec6.json')
    # main(myClient)
