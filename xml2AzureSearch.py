import io
import xmltodict
import requests
import os
import time
from string import Template


# parsing a large xml file from https://github.com/zygmuntz/goodbooks-10k/tree/master/books_xml
#
# '/Users/djb/Cloud/OneDrive - Microsoft/SLaM/BRC-CRIS-Query/goodreadbooksdump/books_xml'

# pretty print json dump json.dumps(o,  sort_keys=false, indent=4, separators=(',', ': '))

# multi author XMLFILE = '/Users/djb/Cloud/OneDrive - Microsoft/SLaM/BRC-CRIS-Query/goodreadbooksdump/books_xml/103111.xml'

XMLFILE = '/Users/djb/Cloud/OneDrive - Microsoft/SLaM/BRC-CRIS-Query/goodreadbooksdump/books_xml/5587960.xml'
XMLDIR = '/Users/djb/Cloud/OneDrive - Microsoft/SLaM/BRC-CRIS-Query/goodreadbooksdump/books_xml/'
APIKEY =
SEARCHURL = 'https://brctest.search.windows.net'


def createIndex():
    postTemplate = """ {	"name": "goodreads",
                "fields": [
                {"name": "id","type": "Edm.String", "key": true, "searchable": false, "sortable": false, "facetable" : false},
                {"name": "isbn","type": "Edm.String", "searchable": true, "sortable": true, "facetable" : true},
                {"name": "isbn13","type": "Edm.String", "searchable": true, "sortable": true, "facetable" : true},
                {"name": "author","type": "Edm.String", "searchable": true, "sortable": true, "facetable" : true},
                {"name": "title","type": "Edm.String", "searchable": true, "sortable": true, "facetable" : false},
                {"name": "publisher","type": "Edm.String", "searchable": true, "sortable": true, "facetable" : false},
                {"name": "country_code","type": "Edm.String", "searchable": false, "sortable": true, "facetable" : true},
                {"name": "language_code","type": "Edm.String", "searchable": false, "sortable": true, "facetable" : true},
                {"name": "num_pages","type": "Edm.Double", "searchable": false, "sortable": true, "facetable" : true},
                {"name": "publication_date","type": "Edm.DateTimeOffset", "searchable": false, "sortable": true, "facetable" : false},
                {"name": "description","type": "Edm.String", "searchable": true, "sortable": false, "facetable" : false},
                {"name": "average_rating","type": "Edm.Double", "searchable": false, "sortable": true, "facetable" : true},
                {"name": "text_reviews_count","type": "Edm.Double", "searchable": false, "sortable": true, "facetable" : true}
            ]
    }"""

    params = {'api-version': '2016-09-01'}
    headers = {'api-key': APIKEY, 'Content-Type': 'application/json'}
    req = requests.post(SEARCHURL + '/indexes', headers=headers, data=postTemplate, params=params)

    if req.status_code != 200:
        print req.text

def addIdxEntry(postData):
    params = {'api-version': '2016-09-01'}
    headers = {'api-key': APIKEY, 'Content-Type': 'application/json'}
    req = requests.post(SEARCHURL + '/indexes/goodreads/docs/index', headers=headers, data=postData, params=params)

    if req.status_code != 200:
        print "error " + req.text

    return(req.status_code)


def extBookFromXMLFILE(xmlfile):
    """

    :rtype : none as yet
    """
    f = io.open(xmlfile, mode="r", encoding="utf-8")
    xmldata = f.read()

    o = xmltodict.parse(xmldata)
    bookDict = o["GoodreadsResponse"]["book"]

    bookProps = ["id", "title", "isbn", "isbn13", "country_code", "publication_year", "publisher", "language_code",
                 "description", "average_rating", "text_reviews_count", "num_pages"]

    # Get the all of the books from the entry - main book and similar books
    bid = bookDict["id"]
    if bookDict["title"]:
        btitle = bookDict["title"].replace('"','*')
    else:
        btitle = ""
    bisbn = bookDict["isbn"]
    bisbn13 = bookDict["isbn13"]
    bcountry_code = bookDict["country_code"]
    if isinstance(bookDict["authors"]["author"], list):
        bauthor = []
        for authdict in bookDict["authors"]["author"]:
            bauthor.append(authdict["name"])
    # author could be a list of orderedDict or orderedDict - convert to a list of author strings, even if only one
    elif isinstance(bookDict["authors"]["author"], dict):
        bauthor = [bookDict["authors"]["author"]["name"], ]

    bauthors = ",".join(bauthor) # convert from list into comma separated list
    bpublisher = bookDict["publisher"]
    blanguagecd = bookDict["language_code"]
    if bookDict["num_pages"]:
        bnumpages = int(bookDict["num_pages"])
    else:
        bnumpages = 0

    # get correct format for the publication day and month
    if bookDict["publication_day"] and bookDict["publication_month"] and bookDict["publication_year"]:
        if int(bookDict["publication_month"]) < 10:
            pubMonth = "0" + bookDict["publication_month"]
        else:
            pubMonth = bookDict["publication_month"]
        #
        if int(bookDict["publication_day"]) < 10:
            pubDay = "0" + bookDict["publication_day"]
        else:
            pubDay = bookDict["publication_day"]
        #
        bpublicationdate = bookDict["publication_year"] + "-" + pubMonth + "-" + pubDay
    else:
        bpublicationdate = "0001-01-01"
    #
    if bookDict["description"]:
        bdescription = bookDict["description"].replace('"', '*')
    else:
        bdescription = ""
    #
    baveragereating = float(bookDict["average_rating"])
    if bookDict["text_reviews_count"]:
        btextreviewcount = int(bookDict["text_reviews_count"])
    else:
        btextreviewcount = None

    # assemble a json document to submit
    idxTemplate = Template("""{
    "value": [
        {
            "@search.action": "upload",
            "id": "$id",
            "title": "$title",
            "isbn": "$isbn",
            "isbn13": "$isbn13",
            "country_code": "$country_code",
            "author": "$author",
            "publisher": "$publisher",
            "language_code": "$language_code",
            "num_pages" : $num_pages,
            "publication_date" : "$publication_date",
            "description": "$description",
            "average_rating": $average_rating,
            "text_reviews_count": $review_count
            }
        ]
    }
    """)

    idxPostData = idxTemplate.substitute(id=bid, title=btitle, isbn=bisbn, isbn13=bisbn13, country_code=bcountry_code,
                                         author=bauthors, publisher=bpublisher, language_code=blanguagecd,
                                         num_pages=bnumpages, publication_date=bpublicationdate,
                                         description=bdescription,average_rating=baveragereating,
                                         review_count=btextreviewcount)
    idxPostData = idxPostData.encode('utf-8')
    retCode = addIdxEntry(idxPostData)
    if retCode != 200:
        print "Error processing file", xmlfile



if __name__ == '__main__':
    # call create index API
    # createIndex()
    # extBookFromXMLFILE('filepath')

    #loop round the files in XMLDIR parse and add them to the index
    idxcount = 0
    begin = time.time()
    for fn in os.listdir(XMLDIR):
        fpath = XMLDIR + fn
        if os.path.isfile(fpath):
            start = time.time()
            extBookFromXMLFILE(fpath)
            elapsed = time.time() - start
            print idxcount, fn, 'call time = ',  elapsed
            idxcount += 1
    print
    print 'Total Elapsed = ', time.time() - begin , 'Seconds'
