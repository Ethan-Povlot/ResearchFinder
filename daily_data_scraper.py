import requests
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
import pandas as pd
import swifter
import logging
from pybliometrics.scopus import AbstractRetrieval
from llama_cpp import Llama
logging.basicConfig(filename='logging.log', level=logging.INFO)
logging.info('Starting @ '+datetime.now().strftime('%Y-%m-%d %H:%M'))



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
def download_arxiv_old(arxiv_id):#mostly deprecated, just a backup method
    driver = webdriver.Chrome()
    driver.get(f'https://arxiv.org/pdf/{arxiv_id}.pdf')
    keyboard.press_and_release('ctrl + s')
    sleep(1)
    keyboard.write('temp.pdf')
    keyboard.press_and_release('enter')
    download_wait()
    driver.quit()
    return get_page(r"C:\Users\ethan\Downloads\temp.pdf")

def download_arxiv(arxiv_id):
    response = requests.get(f'https://arxiv.org/pdf/{arxiv_id}.pdf')

    if response.status_code == 200:
        pdf_content = BytesIO(response.content)
        #pdf_reader = PdfReader(pdf_content)
        return get_page(pdf_content,reader=True)
        
    else:
        return download_arxiv_old(arxiv_id)
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
    

############################################################# osf ##################################################
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


######################################## arXiv ##########################################
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
                'affiliations': download_arxiv(paper_id)
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

############################ add scopus and grant scrapers here #################################
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






########################################## llama 2 implementation #############################
llama_cache = {}
def get_llama_summary(abstract):
    global llama_cache
    if abstract in llama_cache:
        return llama_cache[abstract]
    try:
        question = ("Q:Summarize this text: "+abstract+'A:')[:500]#there is a 512 char limit to the 
        output = LLM(question)["choices"][0]["text"]
        llama_cache[abstract] = output
        return output
    except:
        return abstract



###################################################################################################
df_explored = pd.read_pickle('last_month_wo_llama.pkl')
explored_files = df_explored[df_explored['score_divider'] <=2]['paper_id'].values.tolist()
explored_files = dict(zip(explored_files, [None]*len(explored_files)))
## add code to check if the file was seen yesterday, if so skip it
print('starting osf')
logging.info('OSF starting')
osf_df = get_osf(2)
print('starting arxiv')
logging.info('arXiv starting')

arxiv_df = get_arxiv_days_back(2)
logging.info('arXiv finished')
scopus_df = get_scopus(2)
logging.info('Scopus finished')


new_daily_df = pd.concat([arxiv_df, osf_df, scopus_df])
print('starting combining and scoring')




new_daily_df['language'] = new_daily_df['abstract'].apply(get_lang)
new_daily_df=new_daily_df[new_daily_df['language'] == 'en']
model = KeyedVectors.load_word2vec_format(path, binary=True)# here for memory optimization
new_daily_df['abstract_vec'] = new_daily_df['abstract'].apply(sentence2vec)
new_daily_df['score_divider'] =1
#combining the data that is already run with the 
old_df = pd.read_pickle('last_month.pkl')
old_df['score_divider'] = old_df['score_divider'].astype(int)+1

old_df = old_df[old_df['score_divider']>=30]

output_df = pd.concat([old_df, new_daily_df])
output_df =output_df.drop_duplicates(subset='paper_id')
pref_df = pd.read_pickle('user_pref.pkl')
users =  []
logging.info('starting scoring')

for name in list(pref_df.columns):
    if '_weight' in name.lower():
        users.append(name[:-7])
LLM = Llama(model_path=r"llama\llama-2-7b.Q4_K_M.gguf",  n_ctx=2048)
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

