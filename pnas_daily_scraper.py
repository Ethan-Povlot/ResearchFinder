import pandas as pd
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

def get_pnas_auth_affil_abst(doi):
    authors = []
    affiliations = []
    response = requests.get(f'https://api.crossref.org/works/{doi}')
    json_resp = response.json()
    for id in json_resp['message']['author']:
        name = ""
        for name_type in ['given', 'family']:
            try:
                name+=id[name_type]+' '
            except:
                pass
        authors.append(name[:-1])
        for affil in id['affiliation']:
            affiliations.append(affil['name'])
    affiliations = list(set(affiliations))
    authors = list(set(authors))
    try:
        abstract =  BeautifulSoup(json_resp['message']['abstract'], "lxml").text.strip()
    except:
        abstract = ""
    try:
        subjects = json_resp['message']['subject']
    except:
        subjects = ""
    return authors, affiliations,abstract, subjects
def get_pnas_per_school(days_back, affiliation):
    start_date = (datetime.now()-timedelta(days=days_back)).strftime('%Y%m%d')
    end_date = datetime.now().strftime('%Y%m%d')
    url = f'https://www.pnas.org/action/showFeed?ui=0&mi=99mbi3&type=search&feed=rss&query=%2526access%253Don%2526content%253DarticlesChapters%2526dateRange%253D%25255B{start_date}%252BTO%252B{end_date}%25255D%2526field1%253DAffiliation%2526target%253Ddefault%2526text1%253D{affiliation}'

    response = requests.get(url)
    soup = BeautifulSoup(response.text, "xml")
    items = soup.find_all("item")
    out = []
    for item in items:
        paper_info = {}
        paper_info['paper_id'] = item.find("prism:doi").text
        paper_info['title']= item.find("dc:title").text
        paper_info['date']=item.find('prism:coverDisplayDate').text[:10]
        paper_info['url'] = 'https://www.pnas.org/doi/abs/'+paper_info['paper_id']
        paper_info['authors'], paper_info['affiliations'], paper_info['abstract'], paper_info['subjects'] = get_pnas_auth_affil_abst(paper_info['paper_id'])
        out.append(paper_info)
    df = pd.DataFrame.from_records(out)
    df['source'] = 'National Academy of Sciences US'
    return df
def get_pnas_days_back(num_days):
    results = []
    for affil in ['Emory', 'Georgia']:
        results.append(get_pnas_per_school(num_days, affil))
    return pd.concat(results)
print('PNAS')
for i in range(10):
    try:
        df = get_pnas_days_back(2)
        df.to_pickle(r'daily_temp_files\pnas_temp.pkl')
        break
    except:
        continue