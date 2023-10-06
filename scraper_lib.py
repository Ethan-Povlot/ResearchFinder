import requests
import threading
import pandas as pd
from datetime import datetime, timedelta
import re
import json
import os
from io import BytesIO
import docx
from PyPDF2 import PdfReader
from string import digits
from selenium import webdriver
from time import sleep
import keyboard
from bs4 import BeautifulSoup
import spacy
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from gensim.models import KeyedVectors
from langdetect import detect
import logging
from pybliometrics.scopus import AbstractRetrieval
from llama_cpp import Llama
from metapub import PubMedFetcher
from Bio import Entrez
logging.basicConfig(filename='logging.log', level=logging.INFO)
logging.info('Starting @ '+datetime.now().strftime('%Y-%m-%d %H:%M'))
df_explored = pd.read_pickle('last_month_wo_llama.pkl')
explored_files = df_explored[df_explored['score_divider'] <=2]['paper_id'].values.tolist()#if a paper is for some reason updated then catch it otherwise ignore as we have already indexed it
explored_files = dict(zip(explored_files, [None]*len(explored_files)))


Entrez.email = "epovlot8589@gmail.com"
Entrez.api_key = '8f0801462285bdfc3696dd0c55c09e52cd08'


print('starting')
uni_names = list(set(pd.read_csv('uni_lst.csv')['University'].values.tolist()))
nlp = spacy.load("en_core_web_sm")
path = r'llama\word2vec-google-news-300.bin'

################################################# generic functions to explore ####################################################
def get_similarity(old, new):#input is output of sentence2vec()for each abstract
    try:
        return cosine_similarity([new], [old])[0][0]
    except:
        return 0
def get_score(new, user_id, pref_df):
    user_pref_df = pref_df[pref_df[user_id+'_weight']!=0]
    user_pref_df['score'] = user_pref_df['abstract_vec'].apply(get_similarity, args=[new,])
    user_pref_df['score'] = user_pref_df['score']*user_pref_df[user_id+'_weight']
    return user_pref_df['score'].sum()
def sentenceSimplifier(txt): 
    doc = nlp(txt)
    out = ""
    for token in doc:
        if token.pos_ in ['PROPN', 'VERB','NUM', 'NOUN']:
            out+=token.lemma_+" "
    return out[:-1]
def sentence2vec(txt):
    simplified_txt = sentenceSimplifier(txt)
    words = simplified_txt.split(" ")
    vecs_arr = np.array([model[word] for word in words if word in model]).sum(axis=0)/len(words)
    return  vecs_arr
def read_word_file(file_path):
    doc = docx.Document(file_path)
    first_page_text = []
    for para in doc.paragraphs:
        first_page_text.append(para.text)
    return '\n'.join(first_page_text)
def download_wait(path_to_downloads=r'c:\Users\ethan\Downloads'):#mostly deprecated
    seconds = 0
    dl_wait = True
    while dl_wait and seconds < 60:
        sleep(1)
        dl_wait = False
        for fname in os.listdir(path_to_downloads):
            if fname.endswith('.crdownload'):
                dl_wait = True
        seconds += 1
    return seconds
def download_arxiv_old(arxiv_id, source):#mostly deprecated, just a backup method
    driver = webdriver.Chrome()
    if source == 'arXiv':
        driver.get(f'https://arxiv.org/pdf/{arxiv_id}.pdf')
    elif source == 'biorxiv':
        driver.get(f'https://www.biorxiv.org/content/{arxiv_id}.full.pdf')
    elif source == 'medrxiv':
        driver.get(f'https://www.medrxiv.org/content/{arxiv_id}.full.pdf')

    
    keyboard.press_and_release('ctrl + s')
    sleep(1)
    keyboard.write('temp.pdf')
    keyboard.press_and_release('enter')
    download_wait()
    driver.quit()
    return get_page(r"C:\Users\ethan\Downloads\temp.pdf")

def download_arxiv(arxiv_id, source = 'arXiv'):
    i=0
    try:
        while i < 5:
            if source == 'arXiv':
                response = requests.get(f'https://arxiv.org/pdf/{arxiv_id}.pdf')
            elif source == 'biorxiv':
                response = requests.get(f'https://www.biorxiv.org/content/{arxiv_id}.full.pdf')
            elif source == 'medrxiv':
                response = requests.get(f'https://www.medrxiv.org/content/{arxiv_id}.full.pdf')

            if response.status_code == 200:
                pdf_content = BytesIO(response.content)
                #pdf_reader = PdfReader(pdf_content)
                return get_page(pdf_content,reader=True)
            i+=1
    except:
        pass
    try:
        return download_arxiv_old(arxiv_id, source)
    except:
        return None
def osf_download_old(publication_id):
    with open("temp.pdf", "wb") as pdf_file:
        pdf_file.write(requests.get(r'https://osf.io/download/'+publication_id).content)
    return get_page('temp.pdf')

def osf_download(publication_id):
    publication_link = r'https://osf.io/download/'+publication_id
    out=  get_page(BytesIO(requests.get(publication_link).content), reader=True)
    if out ==[]:
        print('old')
        return osf_download_old(publication_link)
    return out

def get_page(file_name, reader=False):
    page = None
    try:
        reader  = PdfReader(file_name)#this should work either way as this function can take in either path or file
        page = reader.pages[0].extract_text()
    except:
        try:
            page = read_word_file(file_name)
        except:
            pass
    if not reader:
        os.remove(file_name)
    if page == None:
        return []
    return get_affiliations_and_emails(page)
def get_affiliations_and_emails(page):
    page = page.replace('\n', ' ').replace(',', ' ').replace('.com', '.com ')
    page = page.translate(str.maketrans('', '', digits))
    
    
    
    pattern =r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,6}\b'
    emails = re.findall(pattern, page)
    
    brute_force = []
    for name in uni_names:
        if name in page:
            brute_force.append(name)
    
    return list(set(emails) | set(brute_force))
def get_authors(lst):
    out = []
    for auth in lst:
        out.append(auth['given']+ ' '+auth['family'])
    return out
def get_subject(lst):
    out = []
    for sub in lst:
        out.append(sub['text'])
    return out
def get_lang(x):
    try:
        return detect(x)
    except:
        return 'Fail'
    

################################################################## osf ##################################################################
def get_osf(num_days):
    global explored_files
    OSF_token = 'XhAMbzE7SI0KcHYGLgn1oI5EeMqWbtiJuUOTjR1VdLDnF343kgT9OMhTwHiTY5lfd1ma1c'
    api_url = "https://api.osf.io/v2/preprints/"

    headers = {
        "Authorization": f"Bearer {OSF_token}"
    }

    params = {
            "page[size]": 100,# this is max ==100
            "filter[date_published][gte]":(datetime.now() - timedelta(days=num_days)).isoformat()
            
        }
    out = []
    i = 0
    while True:
        response = requests.get(api_url, headers=headers, params=params)
        data = response.json()
        for publication in data["data"]:
            paper_id = publication['id']
            if paper_id in explored_files:
                continue
            # global pub
            # pub = publication
            #try:
            data_auths = requests.get(f'https://api.osf.io/v2/preprints/{paper_id}/citation/', headers=headers).json()['data']['attributes']['author']
            subjects = publication['attributes']['subjects'][0]
            title = publication["attributes"]["title"]
            abstract = publication['attributes']['description']
            url = publication['links']['html']
            date = publication['attributes']['date_published']
            emails = osf_download(publication['relationships']['primary_file']['links']['related']['href'][28:])
            if i%10 ==0:
                print(i)
            i+=1
            out.append([paper_id, data_auths, subjects, title, abstract, url, date, emails])
            # except:
            #     pass
        try:
            api_url =data['links']['next']
            if api_url == None:
                break
        except:
            break
        #break#remove before full use, just for testing
    df = pd.DataFrame(out, columns=['paper_id', 'authors', 'subjects', 'title', 'abstract', 'url', 'date', 'affiliations'])
    df['authors'] = df['authors'].apply(get_authors)
    df['subjects'] = df['subjects'].apply(get_subject)
    df['source'] = 'OSF'
    return df


################################################################## arXiv ##################################################################
i = 0
def get_arxiv_catchup_per_subject(soup):
    global i
    global explored_files
    out = []
    data = soup.text.split('\n arXiv:')
    for entry in data[1:]:
        entry = entry.split('\n\n')
        try:
            entry.remove("")
        except:
            pass
        try:
            entry.remove(" ")
        except:
            pass
        entry = [x for x in entry if not 'Comments: ' in x]
        paper_id = entry[0].split(" ")[0]
        if paper_id in str(explored_files):
            continue
        try:
            entry_data = {
                'paper_id':paper_id,
                'title':entry[1].replace("Title: ", '').replace("\n", ''),
                'authors':entry[2].replace("Authors:", '').replace("\n", '').split(', '),
                'subjects':entry[3].replace("Subjects: ", '').replace("\n", ''),
                'abstract':entry[4].replace("\n", ''),
                'url':f"https://arxiv.org/abs/{paper_id}",
                'affiliations': download_arxiv(paper_id, source='arXiv')
            }
            out.append(entry_data)
            if i%5==0:
                print(i)
            i+=1
        except:
            pass
    return out
def get_arxiv_per_day(date):
    out = []
    for subject in ['q-fin', 'cs', 'math', 'q-bio', 'hep-th', 'stat', 'econ', 'eess']: 
        url = f"https://arxiv.org/catchup?smonth={str(date.month)}&group=grp_&sday={str(date.day)}&archive={subject}&method=with&syear={str(date.year)}"
        print(url)
        j = 0
        success = False
        # the intent here is to retry the request 10 times and then if it fails all of them then return nothing as clearly something has gone very wrong and likely a new url will fix it
        while not(success) and j < 10:
            try:
                response = requests.get(url)
                success = True
            except:
                j+=1
        if not success:
            return 
        soup = BeautifulSoup(response.text, 'html.parser')
        out.extend(get_arxiv_catchup_per_subject(soup))
    df = pd.DataFrame.from_records(out)
    df['date']= date.strftime('%Y-%m-%d')
    df['source'] = 'arXiv'
    return df

def get_arxiv_days_back(num_back):
    df = pd.DataFrame()
    date = datetime.now()
    for i in range(num_back):
        df = pd.concat([df, get_arxiv_per_day(date-timedelta(days=i))])
    return df

################################################################## grant scrapers here ##################################################################



################################################################## MDPI Scraper ##################################################################
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
        except:
            pass
    return out


def get_mdpi_days_back(days_back):
    out = []
    i = 1
    while True:
        response = requests.get(f'https://www.mdpi.com/search?sort=pubdate&page_count=15&page_no={i}')
        soup = BeautifulSoup(response.text, 'html.parser')
        out.extend(get_mdpi_per_page(soup.find_all('div', class_='article-content')))
        if datetime.strptime(out[-1]['date'], '%Y-%m-%d').date() <datetime.now().date()-timedelta(days=days_back):
            break
        print(i*15)
        i+=1
    return pd.DataFrame.from_records(out)

################################################################## Nature Scraper ##################################################################
def get_info_per_article_nature(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    abstract = soup.find('meta', attrs={'name': 'dc.description'})['content']
    date = soup.find('meta', attrs={'name': 'citation_online_date'})['content'].replace('/', '-')
    paper_id = soup.find('meta', attrs={'name': 'prism.doi'})['content']
    authors =[x['content'] for x in soup.find_all('meta', attrs={'name': 'dc.creator'})]
    subjects =[x['content'] for x in soup.find_all('meta', attrs={'name': 'dc.subject'})]
    affiliations = list(set([x['content'] for x in soup.find_all('meta', attrs={'name': 'citation_author_institution'})]))
    return abstract, date, paper_id, authors, subjects, affiliations

def get_nature_per_page(divs):
    out = []
    for div in divs:
        paper_info = {}
        paper_info['title'] = div.find('a',class_="c-card__link u-link-inherit").text
        paper_info['url']= 'https://www.nature.com'+div.find('a', class_='c-card__link u-link-inherit')['href']
        paper_info['abstract'], paper_info['date'], paper_info['paper_id'], paper_info['authors'], paper_info['subjects'], paper_info['affiliations'] = get_info_per_article_nature(paper_info['url'])
        out.append(paper_info)
    return out

def get_nature_days_back(days_back):
    out = []
    i=1
    while i<=20:
        response = requests.get(f'https://www.nature.com/search?order=date_desc&page={i}&article_type=research')
        soup = BeautifulSoup(response.text, 'html.parser')
        out.extend(get_nature_per_page(soup.find_all('div', class_='c-card__body u-display-flex u-flex-direction-column')))
        if datetime.strptime(out[-1]['date'], '%Y-%m-%d').date() <datetime.now().date()-timedelta(days=days_back):
            break
        print(i)
        print(datetime.strptime(out[-1]['date'], '%Y-%m-%d').date())
        i+=1
    df = pd.DataFrame.from_records(out)
    df['source'] = 'Nature'
    return df

################################################################## NIH pubMed DB ##################################################################
def get_pubmed(days_back):
    def pubmed_affiliations(pmid):
        soup = BeautifulSoup(requests.get(f'/long-authors/').text, 'html.parser')
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
            paper_info['url'] = f'https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}'
            paper_info['affiliations'] = pubmed_affiliations(pubmed_id)
            return paper_info
        except:
            return
    days_ago = datetime.now() - timedelta(days=days_back)

    fetch = PubMedFetcher()
    search_query = f"({days_ago.strftime('%Y/%m/%d')}[Date - Entry] : {datetime.now().strftime('%Y/%m/%d')}[Date - Entry])"

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
    df = pd.DataFrame.from_records(out)
    df['source'] = 'PubMed NIH'
    return df


################################################################## Scopus Scraper ##################################################################

def get_data_per_doi(doi, output_dict):
    ab = AbstractRetrieval(doi, view='FULL')
    output_dict['title'] = ab.title
    abstract = ab.abstract
    if not abstract:
        abstract = ab.description
    output_dict['abstract'] =abstract
    output_dict['url']= ab.scopus_link
    subjects =[]
    for area in ab.subject_areas:
        subjects.append(area.area)
    authors = []
    affiliations = []
    for author in ab.authors:
        authors.append(author.indexed_name)
    affiliations = []
    for affiliation in ab.affiliation:
        affiliations.append(affiliation.name)
    output_dict['affiliations'] = affiliations
    output_dict['authors'] = authors
    output_dict['subjects'] = subjects
    return output_dict
def get_scopus(days_back):
    global explored_files
    api_key = 'f7401115c3b98c2edae8c1203c2f15b4'
    url = 'https://api.elsevier.com/content/search/scopus'

    # Define the query parameters
    params = {
        'apiKey':api_key,
        'query': f'LANGUAGE(english) AND AFFILCOUNTRY(United States) AND (AFFILORG(Georgia) OR AFFILORG(Emory)) AND date={str(datetime.today().year)}',
        'count': 100,  # You can adjust the number of results per page as needed
    }
    out =[]
    dates_back_found = True
    while dates_back_found:
        response = requests.get(url, params=params)
        response_json = response.json()['search-results']['entry']
        for i in range(len(response_json)):
            paper_dict = {}
            paper_dict['paper_id'] = response_json[i]['dc:identifier']
            if paper_dict['paper_id'] in explored_files:
                continue
            paper_dict['date'] = response_json[i]['prism:coverDate']
            paper_dict = get_data_per_doi(response_json[i]['prism:doi'], paper_dict)
            out.append(paper_dict)
            if datetime.strptime(response_json[i]['prism:coverDate'], '%Y-%m-%d') < datetime.today()-timedelta(days=days_back):
                dates_back_found = False
            
        next_dict = response.json()['search-results']['link'][2]
        if next_dict['@ref'] =='next':
            url = next_dict['@href']
        params = {
            'apiKey':api_key,
            'count': 100,  # You can adjust the number of results per page as needed
        }
    df = pd.DataFrame.from_records(out)
    df['source'] = 'Scopus'
    return df

################################################################## Bio / Med xiv ##################################################################
def info_per_bioarXiv(entry):
    out = {}
    out['source'] = entry['server']
    out['date'] = entry['date']
    out['authors'] = entry['authors']
    out['title'] = entry['title']
    out['abstract'] = entry['abstract']
    out['paper_id'] = entry['doi']
    out['subjects'] = entry['category']
    out['url'] = 'https://www.biorxiv.org/content/'+str(out['paper_id'])
    
    out['affiliations'] = list(set([entry['author_corresponding_institution']]+download_arxiv(out['paper_id'], source=out['source'])))
    return out
def get_bioMedxiv(days_back):
    global explored_files
    num_read = 0
    j = 0
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now()-timedelta(days=days_back)).strftime('%Y-%m-%d')
    out = []
    while True:
        response = requests.get(f'https://api.biorxiv.org/details/biorxiv/{start_date}/{end_date}/{num_read}')
        json_resp = response.json()['collection']
        print(len(json_resp))
        if len(json_resp) ==0:
            break
        num_read+=len(json_resp)
        for entry in json_resp:
            if j%10==0:
                print(j)
            j+=1
            if entry['doi'] in explored_files:
                continue
            out.append(info_per_bioarXiv(entry))
    return pd.DataFrame.from_records(out)
################################################################## chemrxiv ##################################################################
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
############################# National Accademy of Sciences Journal #############################
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
################################################################## JAMA #####################################################################
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

######################################################################### AHA Journal #########################################################################
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
######################################################################### Oxford Academic ########################################################
def get_oup_extra_data(url):
    driver = webdriver.Chrome()
    driver.get(url)
    html = driver.page_source
    driver.close()
    soup=BeautifulSoup(html,'html.parser')
    try:
        abstract = soup.find('section', class_='abstract').text
    except:
        try:
            h2_lst = soup.find_all('h2', class_='section-title js-splitscreen-section-title')
            limited_lst = []
            for i in range(len((h2_lst))):
                if 'intro' in h2_lst[i].text.lower() or 'abstract' in h2_lst[i].text.lower():
                    limited_lst.extend([h2_lst[i]])
            abstract = ""
            for a in limited_lst[0].find_next_siblings():
                if 'section-title js-splitscreen-section-title' in str(a):
                    break
                abstract+=a.text+' '
        except:
            abstract = ""
    script_tag = soup.find('script', type='application/ld+json')
    script_content = script_tag.string
    data = json.loads(script_content)
    keywords = data.get("keywords", [])
    authors = []
    affiliations = []
    try:
        for name in data['author']:
            authors.append(name['name'])
            affiliations.append(name['affiliation'])
        affiliations= list(set(affiliations))
        authors= list(set(authors))
    except:
        try:
            author_meta_tags = soup.find_all('meta', {'name': 'citation_author'})
            authors = []
            for auth in author_meta_tags:
                authors.append(auth['content'])
            authors =list(set(authors))
            institution_meta_tags = soup.find_all('meta', {'name': 'citation_author_institution'})
            affiliations = []
            for auth in institution_meta_tags:
                affiliations.append(auth['content'])
            affiliations =list(set(affiliations))
        except:
            pass
    return abstract, keywords, authors, affiliations


def get_oup_data(div):
    try:
        global out
        paper_info = {}
        paper_info['title'] = div.find('a', class_='article-link at-sr-article-title-link').text.strip()
        paper_info['date']=datetime.strptime(div.find('div', class_='sri-date al-pub-date').text.strip().split(': ')[-1],'%d %B %Y' ).strftime("%Y-%m-%d")
        url = div.find('a', class_="article-link at-sr-article-title-link")['href']
        paper_info['paper_id']= url[url.find('/doi'):url.find('?search')]
        paper_info['url'] = 'https://academic.oup.com'+url
        paper_info['abstract'], paper_info['subjects'], paper_info['authors'], paper_info['affiliations'] =  get_oup_extra_data(paper_info['url'])
        paper_info['source'] = 'Oxford Academic'
        out.append(paper_info)
    except:
        print('fail')
        pass

out = []
def get_oup_days_back(num_days):
    global out
    out= []
    i=1
    while True:
        url = f'https://academic.oup.com/journals/search-results?sort=Date+%E2%80%93+Newest+First&f_ContentSubTypeDisplayName=Research+Article&fl_SiteID=5567&page={i}'
        driver = webdriver.Chrome()
        driver.get(url)
        html = driver.page_source
        driver.close()
        soup=BeautifulSoup(html,'html.parser')
        threads = []
        for div in soup.find_all('div', class_='sr-list al-article-box al-normal clearfix'):
            thread = threading.Thread(target=get_oup_data, args=(div,))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        i+=1
        if datetime.strptime(out[-1]['date'], '%Y-%m-%d').date() <datetime.now().date()-timedelta(days=num_days):
            break
    return pd.DataFrame.from_records(out)

######################################################################### LLAMA ##########################################################
llama_cache = {}
def get_llama_summary(abstract, LLM):
    global llama_cache
    if abstract in llama_cache:
        return llama_cache[abstract]
    try:
        question = f"""
            Write a concise summary of the text, return a responses covering the key points of the text in a short blurb.
            ```{abstract}```
            SUMMARY:"""
        output = LLM(question, temperature=.8)["choices"][0]["text"]
        llama_cache[abstract] = output.strip()
        return "LLAMA 2: "+output
    except:
        return abstract
