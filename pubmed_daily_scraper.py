import threading
import requests
import pandas as pd
from metapub import PubMedFetcher
from Bio import Entrez
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

Entrez.email = "epovlot8589@gmail.com"
Entrez.api_key = '8f0801462285bdfc3696dd0c55c09e52cd08'


def get_pubmed(days_back):
    def pubmed_affiliations(pmid):
        soup = BeautifulSoup(requests.get(f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/long-authors/').text, 'html.parser')
        ul_element = soup.find('ul', class_='item-list')
        li_elements = ul_element.find_all('li')
        return [li.get_text(strip=True)[1:] for li in li_elements]
    def process_pubmed_ids(start, end):
        for i in range(start, end):
            pubmed_id = pubmed_ids[i]
            paper_info = process_pubmed_id(pubmed_id)
            if paper_info != None:
                out.append(paper_info)
    def process_pubmed_id(pubmed_id):
        try:
            paper_info = {}
            article = fetch.article_by_pmid(pubmed_id)
            paper_info['abstract'] = article.abstract
            paper_info['authors'] = article.authors_str
            paper_info['title'] = article.title
            paper_info['subject'] = article.journal
            paper_info['paper_id'] = article.doi
            paper_info['date'] = article.history['medline'].strftime('%Y-%m-%d')
            paper_info['affiliations'] = pubmed_affiliations(pubmed_id)
            return paper_info
        except:
            return
    days_ago = datetime.now() - timedelta(days=days_back)
    print(days_ago)
    fetch = PubMedFetcher()
    search_query = f"({days_ago.strftime('%Y/%m/%d')}[Date - Publication] : {datetime.now().strftime('%Y/%m/%d')}[Date - Publication])"

    batch_size = 250
    start_idx = 0
    pubmed_ids = []
    while True:
        handle = Entrez.esearch(db="pubmed", term=search_query, retmax=batch_size, retstart=start_idx)
        record = Entrez.read(handle)
        handle.close()
        
        batch_ids = record["IdList"]
        if not batch_ids:
            break  # No more results
        
        pubmed_ids.extend(batch_ids)
        start_idx += batch_size

    rate_limit = 10 
    out = []

    max_threads = len(pubmed_ids) if len(pubmed_ids) < rate_limit else rate_limit
    batch_size = len(pubmed_ids) // max_threads

    threads = []
    for i in range(max_threads):
        start = i * batch_size
        end = (i + 1) * batch_size if i < max_threads - 1 else len(pubmed_ids)
        thread = threading.Thread(target=process_pubmed_ids, args=(start, end))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()
    out = [i for i in out if i is not None]

    return pd.DataFrame.from_records(out)
print("pubmed")
for i in range(10):
    #try:
    df = get_pubmed(2)
    df.to_pickle(r'daily_temp_files\pubmed_temp.pkl')
    break
# except:
#         continue