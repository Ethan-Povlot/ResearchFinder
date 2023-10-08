import requests
import pandas as pd
from datetime import datetime, timedelta


def get_chemrxiv(days_back):
    skip_num = 0
    total_count=1
    start_date = (datetime.now()-timedelta(days=days_back)).strftime('%Y-%m-%d')
    def get_affiliation(x):
        out = []
        for affil in x:
            out.append(affil['name'])
        return out
    def get_authors_affils(x):
        authors = []
        affiliations = []
        for name in x:
            authors.append(name['firstName']+' '+name['lastName'])
            affiliations.extend(get_affiliation(name['institutions']))
        return authors, list(set(affiliations))
    def get_chemrixiv_subjects(x):
        subjects = []
        for subj in x:
            subjects.append(subj['name'])
        return subjects
    out = []
    while skip_num < total_count:
        response = requests.get(f'https://chemrxiv.org/engage/chemrxiv/public-api/v1/items?limit=50&skip={skip_num}&searchDateFrom={start_date}T00:00:00.000Z')
        json_resp = response.json()
        total_count = json_resp['totalCount']
        skip_num+=len(json_resp['itemHits'])
        print(skip_num)
        for paper in json_resp['itemHits']:
            paper_info = {}
            paper_info['paper_id'] = paper['item']['id']
            paper_info['authors'],paper_info['affiliations'] = get_authors_affils(x = paper['item']['authors'])
            paper_info['subjects'] = get_chemrixiv_subjects(paper['item']['categories'])
            paper_info['title'] = paper['item']['title']
            paper_info['abstract'] = paper['item']['abstract']
            paper_info['url'] = 'https://chemrxiv.org/engage/chemrxiv/article-details/'+str(paper['item']['id'])
            paper_info['date'] = paper['item']['publishedDate'][:10]
            paper_info['source'] = paper['item']['origin']
            out.append(paper_info)
    return pd.DataFrame.from_records(out)
print("chemrxiv")
for i in range(10):
    try:
        df = get_chemrxiv(2)
        df.to_pickle(r'daily_temp_files\chemrxiv_temp.pkl')
        break
    except:
        continue