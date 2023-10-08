import pandas as pd
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

df_explored = pd.read_pickle(r'C:\Users\ethan\Documents\ResearchFinder\last_month_wo_llama.pkl')
df_explored = df_explored[df_explored['source']=='MDPI']
explored_files = df_explored[df_explored['score_divider'] <=2]['paper_id'].values.tolist()#if a paper is for some reason updated then catch it otherwise ignore as we have already indexed it
explored_files = dict(zip(explored_files, [None]*len(explored_files)))
del df_explored
def get_extra_info_mdpi(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    affiliations = [x.text for x in soup.find_all('div', class_='affiliation-name')]
    date_txt = soup.find('div', class_ = 'pubhistory').text
    date = datetime.strptime(date_txt[date_txt.find("Published:")+len('published')+2:].strip(),'%d %B %Y' ).strftime("%Y-%m-%d")
    authors = [x['content'] for x in  soup.find_all('meta', attrs={'name': 'dc.creator'})][:-1]
    try:
        subjects = soup.find('span', itemprop='keywords').text.split('; ')
    except:
        subjects = ""
    return affiliations, authors, date, subjects

def get_mdpi_per_page(divs):
    global explored_files
    out = []
    for div in divs:
        try:
            paper_info = {}
            paper_info['paper_id'] = div.find('a', class_="title-link")['href']
            if paper_info['paper_id'] in explored_files:
                continue
            paper_info['abstract'] = div.find('div', class_='abstract-full').text.strip()
            paper_info['title'] = div.find('a', class_="title-link").text.strip()
            paper_info['url'] =  'https://www.mdpi.com'+paper_info['paper_id']
            paper_info['affiliations'], paper_info['authors'], paper_info['date'], paper_info['subjects'] = get_extra_info_mdpi(paper_info['url'])
            if paper_info['subjects'] =='':
                    try:
                        paper_info['subjects'] = div.find('div', class_='belongsTo').text.strip().split(',')
                    except:
                        paper_info['subjects'] = ""
            paper_info['source'] = 'MDPI'
            out.append(paper_info)
        except Exception as e:
            print(e)
            pass
    return out


def get_mdpi_days_back(days_back):
    out = []
    i = 1
    while True:
        response = requests.get(f'https://www.mdpi.com/search?sort=pubdate&page_count=15&page_no={i}')
        soup = BeautifulSoup(response.text, 'html.parser')
        out.extend(get_mdpi_per_page(soup.find_all('div', class_='article-content')))
        print(out[-1]['date'])
        if datetime.strptime(out[-1]['date'], '%Y-%m-%d').date() <datetime.now().date()-timedelta(days=days_back):
            break
        print(i*15)
        i+=1
    return pd.DataFrame.from_records(out)
print('mdpi')
for i in range(10):
    #try:
    df = get_mdpi_days_back(2)
    df.to_pickle(r'daily_temp_files\mdpi_temp.pkl')
    break
    #     break
    # except:
    #     continue