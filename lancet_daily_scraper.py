from selenium import webdriver
import requests
import pandas as pd
from bs4 import BeautifulSoup
import xmltodict
import threading
out = []
df =pd.read_pickle(r'daily_temp_files/lancet_temp.pkl')
explored_files = df['paper_id'].values.tolist()
del df
seen_papers = dict(zip(explored_files, [None]*len(explored_files)))
lancet_rss_feeds = ['https://www.thelancet.com/rssfeed/ebiom_current.xml','https://thelancet.com/rssfeed/eclinm_current.xml', 'https://www.thelancet.com/rssfeed/lancet_current.xml','https://www.thelancet.com/rssfeed/lanrhe_current.xml','https://www.thelancet.com/rssfeed/lanres_current.xml','https://www.thelancet.com/rssfeed/lanwpc_current.xml',
                    'https://www.thelancet.com/rssfeed/lansea_current.xml','https://www.thelancet.com/rssfeed/lanepe_current.xml','https://www.thelancet.com/rssfeed/lanam_current.xml','https://www.thelancet.com/rssfeed/lanpub_current.xml','https://www.thelancet.com/rssfeed/lanpsy_current.xml','https://www.thelancet.com/rssfeed/lanplh_current.xml',
                    'https://www.thelancet.com/rssfeed/lanonc_current.xml','https://www.thelancet.com/rssfeed/laneur_current.xml','https://www.thelancet.com/rssfeed/lanmic_current.xml','https://www.thelancet.com/rssfeed/laninf_current.xml','https://www.thelancet.com/rssfeed/lanhl_current.xml','https://www.thelancet.com/rssfeed/lanhiv_current.xml',
                    'https://www.thelancet.com/rssfeed/lanhae_current.xml','https://www.thelancet.com/rssfeed/langlo_current.xml','https://www.thelancet.com/rssfeed/langas_current.xml','https://www.thelancet.com/rssfeed/landig_current.xml','https://www.thelancet.com/rssfeed/landia_current.xml','https://www.thelancet.com/rssfeed/lanchi_current.xml',
                    'https://www.thelancet.com/rssfeed/lanrhe_online.xml','https://www.thelancet.com/rssfeed/lanres_online.xml','https://www.thelancet.com/rssfeed/lanwpc_online.xml','https://www.thelancet.com/rssfeed/lansea_online.xml','https://www.thelancet.com/rssfeed/lanepe_online.xml','https://www.thelancet.com/rssfeed/lanam_online.xml',
                    'https://www.thelancet.com/rssfeed/lanpub_online.xml','https://www.thelancet.com/rssfeed/lanpsy_online.xml','https://www.thelancet.com/rssfeed/lanplh_online.xml','https://www.thelancet.com/rssfeed/lanonc_online.xml','https://www.thelancet.com/rssfeed/lanmic_online.xml','https://www.thelancet.com/rssfeed/laneur_online.xml',
                    'https://www.thelancet.com/rssfeed/laninf_online.xml','https://www.thelancet.com/rssfeed/lanhiv_online.xml','https://www.thelancet.com/rssfeed/lanhl_online.xml','https://www.thelancet.com/rssfeed/lanhae_online.xml','https://www.thelancet.com/rssfeed/langlo_online.xml','https://www.thelancet.com/rssfeed/langas_online.xml',
                    'https://www.thelancet.com/rssfeed/landig_online.xml','https://www.thelancet.com/rssfeed/landia_online.xml','https://www.thelancet.com/rssfeed/lanchi_online.xml','https://www.thelancet.com/rssfeed/lancet_online.xml','https://www.thelancet.com/rssfeed/eclinm_online.xml','https://www.thelancet.com/rssfeed/ebiom_online.xml']


def get_lancet_info(paper):
    try:
        global out
        global seen_papers
        paper_info = {}
        paper_info['paper_id'] = str(paper['dc:identifier'])
        if paper_info['paper_id'] in seen_papers:
            return
        paper_info['date']= str(paper['dc:date'])
        paper_info['source'] = str(paper['prism:publicationName'])
        paper_info['title'] = str(paper['dc:title'])
        paper_info['abstract'] = paper['description']
        paper_info['url'] = paper['link'].replace('?rss=yes', '')
        driver = webdriver.Chrome()
        driver.get(paper_info['url'])
        html = driver.page_source
        driver.close()

        soup=BeautifulSoup(html,'html.parser')
        authors=[]
        affiliations = []
        paper_info['subjects'] = [x.text for x in soup.find_all('ul', class_='rlist keywords-list inline-bullet-list')]
        for auth in soup.find_all('li', class_='loa__item author'):
            authors.append(auth.find('a', class_='loa__item__name article-header__info__ctrl loa__item__email').text)
            affil_lst = auth.find_all('div', class_='article-header__info__group__body')
            for i in range(len(affil_lst)):
                affiliations.append(affil_lst[i].text.strip())
        paper_info['affiliations'] = affiliations
        paper_info['authors'] = authors
        seen_papers[paper_info['paper_id']] = None
        out.append(paper_info)
    except:
        return
for xml_url in lancet_rss_feeds:
    threads = []
    response = requests.get(xml_url)
    dict_data = xmltodict.parse(response.content)
    try:
        for paper in dict_data['rdf:RDF']['item']:
            thread = threading.Thread(target=get_lancet_info, args=(paper,))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
    except:
        print(xml_url)
df = pd.DataFrame.from_records(out)
df['date'] =df['date'].str[:10]
df.to_pickle(r'daily_temp_files/lancet_temp.pkl')