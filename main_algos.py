import pandas as pd
import swifter
from langdetect import detect
from sklearn.metrics.pairwise import cosine_similarity
from llama_cpp import Llama
import spacy
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from gensim.models import KeyedVectors
nlp = spacy.load("en_core_web_sm")

LLM = Llama(model_path=r"llama\llama-2-7b-chat.Q4_K_M.gguf")
def get_llama_summary(abstract):
    output = LLM("Q:Summarize this text: "+abstract+'A:')["choices"][0]["text"]
    return output
path = r'C:\Users\ethan/gensim-data\word2vec-google-news-300\word2vec-google-news-300.bin'
model = KeyedVectors.load_word2vec_format(path, binary=True)
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
def reset_recommendations():
    if input('Are you really sure??? If so type "Yes, I understand"') == "Yes, I understand":
        df = pd.DataFrame(columns=['paper_id', 'abstract_vec'])
        #df.to_pickle('user_pref.pkl')
        print('you have reset the recommendation database')
        return df
    else:
        print('You exited the reset')
def get_similarity(old, new):#input is output of sentence2vec()for each abstract
    return cosine_similarity([new], [old])[0][0]
def get_score(new, user_id, pref_df):
    user_pref_df = pref_df[pref_df[user_id+'_weight']!=0]
    user_pref_df['score'] = user_pref_df['abstract_vec'].apply(get_similarity, args=[new,])
    user_pref_df['score'] = user_pref_df['score']*user_pref_df[user_id+'_weight']
    return user_pref_df['score'].sum()