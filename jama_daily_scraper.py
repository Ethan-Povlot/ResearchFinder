import pandas as pd
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from selenium import webdriver


last_known_date = datetime.now().strftime('%Y-%m-%d')
def jama_get_extra_info(doi):
    global last_known_date
    response = requests.get(f'https://api.crossref.org/works/{doi}')
    json_resp = response.json()
    abstract = BeautifulSoup(json_resp['message']['abstract'],'html.parser').text
    title = json_resp['message']['title'][0]
    subjects = json_resp['message']['subject']
    url = json_resp['message']['link'][0]['URL']
    try:
        date = '-'.join(str(item) for item in json_resp['message']['published-print']['date-parts'][0])
        last_known_date = date
    except:
        date = last_known_date
    source = 'Jama'
    authors = []
    affiliations = []
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
    return abstract, title, subjects, url, date, source, authors, affiliations

def jama_get_days_back(days_back):
    days_back = 5#find and remove later
    out = []
    i=1
    while True:
        urlString = f'https://jamanetwork.com/searchresults?sort=Newest&f_ArticleTypeDisplayName=Research&page={i}'
        i+=1
        driver = webdriver.Chrome()
        driver.get(urlString)
        html = driver.page_source
        driver.close()
        soup=BeautifulSoup(html,'html.parser')
        for cite in soup.find_all('cite', class_ ='article--citation'):
            paper_info = {}
            paper_info['doi'] = cite.text.replace('. ', ';').split(';')[-1].strip()
            try:
                paper_info['abstract'],paper_info['title'],paper_info['subjects'],paper_info['url'],paper_info['date'],paper_info['source'],paper_info['authors'],paper_info['affiliations'] = jama_get_extra_info(paper_info['doi'])
            except:
                continue
            out.append(paper_info)
        if len(out)>0:
            if datetime.strptime(out[-1]['date'], '%Y-%m-%d').date() <datetime.now().date()-timedelta(days=days_back):
                break
    return pd.DataFrame.from_records(out)
print("Jama")
for i in range(10):
    try:
        df = jama_get_days_back(5)
        df.to_pickle(r'daily_temp_files\jama_temp.pkl')
        break
    except:
        continue