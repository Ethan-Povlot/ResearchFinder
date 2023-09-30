import requests
import threading
import pandas as pd
from datetime import datetime, timedelta
import re
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


Entrez.email = "epovlot8589@gmail.com"
Entrez.api_key = '8f0801462285bdfc3696dd0c55c09e52cd08'


print('starting')
uni_names = list(set(pd.read_csv('uni_lst.csv')['University'].values.tolist()))
nlp = spacy.load("en_core_web_sm")
path = r'llama\word2vec-google-news-300.bin'

################################################# generic functions to explore ####################################################
def get_similarity(old, new):#input is output of sentence2vec()for each abstract
    return cosine_similarity([new], [old])[0][0]
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
        print('here')
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
    print('here')
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
        if paper_id in explored_files:
            continue
        try:
            entry_data = {
                'paper_id':paper_id,
                'title':entry[1].replace("Title: ", '').replace("\n", ''),
                'authors':entry[2].replace("Authors:", '').replace("\n", '').split(', '),
                'subjects':entry[3].replace("Subjects: ", '').replace("\n", ''),
                'abstract':entry[4].replace("\n", ''),
                'affiliations': download_arxiv(paper_id, source='arXiv')
            }
            out.append(entry_data)
            if i%5==0:
                print(i)
            i+=1
        except:
            pass
    print(len(out)) 
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
    df['url'] = 'https://arxiv.org/abs/'+df['paper_id'].astype(str)
    return df

################################################################## grant scrapers here ##################################################################



################################################################## NIH pubMed DB ##################################################################
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
            paper_dict['paper_id'] = response_json[5]['dc:identifier']
            if paper_dict['paper_id'] in explored_files:
                continue
            paper_dict['date'] = response_json[i]['prism:coverDate']
            paper_dict = get_data_per_doi(response_json[i]['prism:doi'], paper_dict)
            out.append(paper_dict)
            if datetime.strptime(response_json[i]['prism:coverDate'], '%Y-%m-%d') < datetime.today()-timedelta(days=days_back):
                dates_back_found = False
                break
            
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
    out['affiliation'] = list(set([entry['author_corresponding_institution']]+download_arxiv(out['paper_id'], source=out['source'])))
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




################################################################## llama 2 implementation ##################################################################
llama_cache = {}
def get_llama_summary(abstract):
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


################################################################## Main run section ##################################################################
df_explored = pd.read_pickle('last_month_wo_llama.pkl')
explored_files = df_explored[df_explored['score_divider'] <=2]['paper_id'].values.tolist()
explored_files = dict(zip(explored_files, [None]*len(explored_files)))
## add code to check if the file was seen yesterday, if so skip it
results = []
num_days = 2 
print('starting osf')
logging.info('OSF starting')
results.append(get_osf(num_days))
print('starting arxiv')
logging.info('arXiv starting')

results.append(get_arxiv_days_back(num_days))
logging.info('arXiv finished')
results.append(get_scopus(num_days))
logging.info('Scopus finished')
results.append(get_bioMedxiv(num_days))
logging.info('biomed finished')
results.append(get_pubmed(num_days))
logging.info('NIH pubmed finished')

# threads = []
# logging.info('multi_thread start')
# for func in [get_osf, get_arxiv_days_back, get_scopus, get_bioMedxiv, get_pubmed]:
#     thread = threading.Thread(target=lambda f, args: results.append(f(*args)), args=(func, (num_days,)))
#     threads.append(thread)
#     thread.start()

# for thread in threads:
#     thread.join()
new_daily_df = pd.concat(results)
print('starting combining and scoring')




new_daily_df['language'] = new_daily_df['abstract'].apply(get_lang)
new_daily_df=new_daily_df[new_daily_df['language'] == 'en']
model = KeyedVectors.load_word2vec_format(path, binary=True)# here for memory optimization
new_daily_df['abstract_vec'] = new_daily_df['abstract'].apply(sentence2vec)
new_daily_df['score_divider'] =1
#combining the data that is already run with the 
old_df = pd.read_pickle('last_month.pkl')
old_df['score_divider'] = old_df['score_divider'].astype(int)+1

old_df = old_df[old_df['score_divider'].astype(int)<=30]

output_df = pd.concat([old_df, new_daily_df])
output_df =output_df.drop_duplicates(subset='paper_id')
pref_df = pd.read_pickle('user_pref.pkl')
users =  []
logging.info('starting scoring')

for name in list(pref_df.columns):
    if '_weight' in name.lower():
        users.append(name[:-7])
LLM = Llama(model_path=r"llama\llama-2-7b.Q4_K_M.gguf",  n_ctx=2048, n_threads=4, )
for user in users:
    output_df[user+'_score'] = output_df['abstract_vec'].apply(get_score, args = [user,pref_df])
    output_df[user+'_score'] = output_df[user+'_score']/output_df['score_divider']#decreases the score of older papers
    output_df = output_df.sort_values(by=[user+'_score'], ascending=False).reset_index(drop=True)
    output_df.to_pickle('last_month_wo_llama.pkl')
    llama_df = output_df.iloc[:20]
    else_df = output_df.iloc[20:]
    else_df['llama_abstract'] = else_df['abstract']
    llama_df['llama_abstract'] =llama_df['abstract'].apply(get_llama_summary)
    output_df=pd.concat([llama_df, else_df])
output_df.to_pickle('last_month.pkl')
print('all saved')
logging.info('Done @ '+datetime.now().strftime('%Y-%m-%d %H:%M'))

