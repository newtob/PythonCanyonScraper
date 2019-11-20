from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup
import datetime


def simple_get(url):
    """Attempts to get the content at `url` by making an HTTP GET request.
    If the content-type of response is some kind of HTML/XML, return the text content, otherwise return None."""
    try:
        with closing(get(url, stream=True)) as resp:
            if is_good_response(resp):
                #TODO response.text vs response.content
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
    """Find three elements in the webpage, bike name, orig price and sale price, output them
    TODO: search for non Aeraod models"""

    BikeNamelist, OrigPricelist, SalePricelist = [], [], []
    try:
        html = BeautifulSoup(raw_html, 'html.parser')
    except TypeError as e:
        print("Type Error parsing raw html = " + e)
        exit(-1)

    for s in html.select('span'):
        BikeName, OrigPrice, SalePrice = None, None, None
        if s.text.startswith("\\n                Aeroad"):
            BikeName = s.text.replace("\\n", "").strip()
            BikeNamelist.append(BikeName)
            for i, child in enumerate(s.next_element.next_element.next_element.children):
                if child.name == "span":
                    #print('found a new span ' + str(i) )
                    #print(child.text.replace("\\n", "").strip())
                    if i == 1:
                        OrigPricelist.append(child.text.replace("\\n", "").strip())
                    if i == 3:
                        SalePricelist.append(child.text.replace("\\n", "").strip())


    myTimeStamp = str(datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc))

    return BikeNamelist, OrigPricelist, SalePricelist, myTimeStamp


def main():
    """main method"""
    if test:
        with open('examplePageAeroadSizeM.html', 'r') as file:
            raw_html = str(file.read())
        with open('examplePageAllBikes.html', 'r') as fileAll:
            raw_max_html = str(fileAll.read())
    else:
        raw_html = simple_get('https://www.canyon.com/en-gb/outlet/road-bikes/?cgid=outlet-road&prefn1=pc_familie&prefn2=pc_outlet&prefn3=pc_rahmengroesse&prefv1=Aeroad&prefv2=true&prefv3=M')
        raw_max_html = simple_get('https://www.canyon.com/en-gb/outlet/road-bikes/?cgid=outlet-road&prefn1=pc_outlet&prefv1=true')

        if raw_html == None or raw_max_html == None:
            print("no return from website")
        else:
            with open("./latestAeroadSizeM.html", 'w') as out_file:
                out_file.writelines(raw_html)
            with open("./latestAllBikes.html", 'w') as out_max_file:
                out_max_file.writelines(raw_max_html)

        #print("raw html coming out next: \t" + str(raw_html))
        #print("raw html of all bikes   : \t" + str(raw_html))

    #print("the raw_html type is : \t" + str(type(raw_html)))
    #print("the raw_max_html type is : \t" + str(type(raw_max_html)))

    print("Aeroad only: \t" + str(parseSearch(raw_html)))
    #
    print("All bikes: \t\t" + str(parseSearch(raw_max_html)))

    #TODO output these two lists to a database

if __name__ == "__main__":
    #test = True
    test = False
    main()