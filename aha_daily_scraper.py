import pandas as pd
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from selenium import webdriver

def get_aha_journal_days_back(days_back):
    out = []
    i=0
    while True:
        url =f'https://www.ahajournals.org/topic/featured/featured-article?sortBy=Earliest&startPage={i}&ContentItemType=research-article&pageSize=100'
        i+=1
        driver = webdriver.Chrome()
        driver.get(url)
        html = driver.page_source
        driver.close()
        soup=BeautifulSoup(html,'html.parser')
        divs = soup.find_all('div', class_='col-xs-12')

        for div in divs:   
            try:
                paper_info = {}
                paper_info['abstract'] = div.find('span', class_="hlFld-Abstract").text.replace('            ', '').replace('\n', '')
                paper_info['title'] = div.find('h3', class_='meta__title meta__title__margin').text.replace('                  ', '').replace('\n', '')
                paper_info['paper_id'] = div.find('h3', class_='meta__title meta__title__margin').find('a')['href']
                paper_info['source'] = 'AHA Journal'
                paper_info['date'] = datetime.strptime(div.find('span', class_='meta__pubDate').text,'%d %B %Y' ).strftime('%Y-%m-%d')
                authors = []
                for auth in div.find_all('span', class_='hlFld-ContribAuthor'):
                    authors.append(auth.text)
                response = requests.get(f'https://api.crossref.org/works/{paper_info["paper_id"]}')
                json_resp = response.json()
                affiliations = []
                for affils in json_resp['message']['author']:
                    for affil in affils['affiliation']:
                        affiliations.append(affil['name'])
                affiliations = list(set(affiliations))
                paper_info['authors'] = authors
                paper_info['affiliations'] = affiliations
                paper_info['url']= json_resp['message']['URL']
                paper_info['subjects']=json_resp['message']['subject']
                out.append(paper_info)
            except:
                pass
        if len(out)>0:
            print(out[-1]['date'])
            if datetime.strptime(out[-1]['date'], '%Y-%m-%d').date() <datetime.now().date()-timedelta(days=days_back):
                break
    return pd.DataFrame.from_records(out)

print('aha')
for i in range(10):
    try:
        df = get_aha_journal_days_back(2)
        df.to_pickle(r'daily_temp_files\aha_temp.pkl')
        break
    except:
        continue
