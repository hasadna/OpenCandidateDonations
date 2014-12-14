import urllib2
import urllib
import json
import datetime
from pyquery import PyQuery as pq
import string
import csv
import hashlib

def geturl(url,data=None):
    try:
        if data is not None:
            key = hashlib.md5(url + data).hexdigest()
        else:
            key = url.encode('hex')
        return file("cache/"+key).read()
    except:
        if data is not None:
            req = urllib2.Request(url, data)
            req.add_header("Content-type", "application/x-www-form-urlencoded")
            ret = urllib2.urlopen(req).read()
        else:
            ret =urllib2.urlopen(url).read()
        cache = file("cache/"+key,'w')
        cache.write(ret)
        cache.close()
        return ret

recs = []

def get_lm_donations():
    lm_recs = []

    # Local Municipalities
    lm_url = r"https://statements.mevaker.gov.il/Handler/GuarantyDonationPublisherHandler.ashx"

    for i in range(200):
        lm_data = {"PublicationSearchType":"1",
                   "EntityID":"",
                   "GD_Name":"",
                   "CityID":"",
                   "CountryID":"",
                   "FromDate":"",
                   "ToDate":"",
                   "FromSum":"",
                   "ToSum":"",
                   "localElectionId":"",
                   "localElectionCityID":str(i),
                   "ID":None,"State":0,
                   "URL":None,"IsControl":False,"IsUpdate":False}
        lm_data = json.dumps(lm_data)
        lm_data = "action=lgds&d=%s" % urllib.quote(lm_data)

        lm = json.loads(geturl(lm_url,lm_data))
        assert(len(lm[0])<1000)
        for x in lm[0]:
            rec = {
                "election_kind": "municipality",
                "donor_city": string.capwords(x["City"]),
                "donor_country": x["Country"],
                "donor_location": string.capwords(x["City"])+" "+x["Country"],
                "election_place": x["ElectionCity"],
                "election_date": datetime.datetime.fromtimestamp(int(x["ElectionDate"][6:-2])/1000).strftime("%d/%m/%Y"),
                "election_faction": x["ElectionFaction"],
                "donor_name": string.capwords(x["GD_Name"]),
                "donation_date": datetime.datetime.fromtimestamp(int(x["GD_Date"][6:-2])/1000).strftime("%d/%m/%Y"),
                "donation_sum": float(x["GD_Sum"]),
                "donation_kind": x["GuaranteeOrDonation"],
                "currency_id": x["SumInCurrency"],
                "foreign_currency_sum": None
            }
            lm_recs.append(rec)
            recs.append(rec)

        print "%d Local Municipalities: %d entries" % (i,len(lm_recs))

def get_new_primary_donations():
    np_recs = []

    # Local Municipalities
    np_url = r"https://statements.mevaker.gov.il/Handler/GuarantyDonationPublisherHandler.ashx"

    for i in range(500):
        np_data = { "PartyID":None,
                    "EntityID":"%d" % i,
                    "EntityTypeID":1,
                    "PublicationSearchType":"1",
                    "GD_Name":"",
                    "CityID":"",
                    "CountryID":"",
                    "FromDate":"",
                    "ToDate":"",
                    "FromSum":"",
                    "ToSum":"",
                    "ID":None,
                    "State":0,
                    "URL":None,
                    "IsControl":False,
                    "IsUpdate":False}

        np_data = json.dumps(np_data)
        np_data = "action=gds&d=%s" % urllib.quote(np_data)

        np = json.loads(geturl(np_url,np_data))
        assert(len(np[0])<1000)
        for x in np[0]:
            foreign = x["SumInCurrency"].split(' ')
            if len(foreign)>1:
                foreign_sum = float(foreign[0])
                foreign_currency = foreign[1]
            else:
                foreign_sum = None
                foreign_currency = None

            rec = {
                "election_kind": "primaries",
                "donor_city": string.capwords(x["City"]),
                "donor_country": x["Country"],
                "donor_location": string.capwords(x["City"])+" "+x["Country"],
                "donation_receiver": x["CandidateName"],
                "election_faction": x["Party"],
                "donor_name": string.capwords(x["GD_Name"]),
                "donation_date": datetime.datetime.fromtimestamp(int(x["GD_Date"][6:-2])/1000).strftime("%d/%m/%Y"),
                "donation_sum": float(x["GD_Sum"]),
                "donation_kind": x["GuaranteeOrDonation"],
                "currency_id": foreign_currency,
                "foreign_currency_sum": foreign_sum,
            }
            np_recs.append(rec)
            recs.append(rec)

        print "%d New Primaries: %d entries" % (i,len(np_recs))

# Primaries
def get_primary_donations():
    pr_recs = []
    used = set()
    base_urls = [ "http://primaries.publish.mevaker.gov.il/", "http://primaries.publish.mevaker.gov.il/CandidatesWithoutParty.aspx" ]
    while len(base_urls) > 0:
        base_url = base_urls.pop(0)
        used.add(base_url)
        print base_url
        base_page = pq(geturl(base_url))
        links = base_page("a")
        links = [ pq(link).attr('href') for link in links ]
        for link in links:
            if link is None:
                continue
            if link == base_url:
                continue
            to_append = None
            if 'Candidates.aspx' in link:
                to_append = "http://primaries.publish.mevaker.gov.il/Candidates.aspx?%s" % link.split("?",1)[1]
            elif 'Donations.aspx' in link:
                to_append = "http://primaries.publish.mevaker.gov.il/Donations.aspx?%s" % link.split("?",1)[1]
            if to_append is not None and to_append not in used:
                base_urls.append(to_append)
        if 'Donations.aspx' in base_url:
            candidate_name = pq(base_page("#ctl00_TdCandidateId")).text()
            party_name = pq(base_page("#ctl00_TdPartyName")).text()
            rows = base_page("table#ctl00_ContentPlaceHolder1_TableView tr")
            for _row in rows:
                items = pq(_row)("td")
                items = [ pq(item).text() for item in items ]
                if len(items) != 5:
                    continue
                if "/" not in items[0]:
                    continue
                rec = {
                    "election_kind": "primaries",
                    "donation_date": items[0],
                    "donation_sum": float(items[1].replace(",","")),
                    "donor_name": string.capwords(items[3]),
                    "donor_location": string.capwords(items[4]),
                    "election_faction": party_name,
                    "donation_receiver": candidate_name,
                }
                if " " in items[2].strip():
                    value,currency = items[2].strip().split(" ")
                    value = float(value.replace(",",""))
                    rec["foreign_currency_sum"] = value
                    rec["currency_id"] = currency
                pr_recs.append(rec)
                recs.append(rec)

            print "Primaries %s/%s: %d entries so far" % (party_name,candidate_name,len(pr_recs))

get_primary_donations()
get_new_primary_donations()
get_lm_donations()

out=file("donations.jsons","w")
for rec in recs:
    out.write(json.dumps(rec)+"\n")

write_recs = []
for rec in recs:
    write_rec = {}
    for k,v in rec.iteritems():
        if type(v)==unicode:
            v = v.encode('utf8')
        else:
            v=str(v)
        write_rec[k] = v
    write_recs.append(write_rec)
fieldnames = recs[-1].keys()
fieldnames.append('donation_receiver')
writer = csv.DictWriter(file("donations.csv","w"),fieldnames,restval='')
writer.writeheader()
writer.writerows(write_recs)
