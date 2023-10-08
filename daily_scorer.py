import pandas as pd
from scraper_lib import *
from pathlib import Path
path = r'C:\Users\ethan\Documents\ResearchFinder\daily_temp_files'
files = Path(path).glob('*.pkl')
new_daily_df = pd.DataFrame()
for f in files:
    new_daily_df = pd.concat([new_daily_df, pd.read_pickle(str(f))])
new_daily_df = new_daily_df.reset_index(drop=True)

print('starting combining and scoring')

new_daily_df['language'] = new_daily_df['abstract'].apply(get_lang)
new_daily_df=new_daily_df[new_daily_df['language'] == 'en']
# here for memory optimization
path = r'llama\word2vec-google-news-300.bin'
model = KeyedVectors.load_word2vec_format(path, binary=True)
new_daily_df['abstract_vec'] = new_daily_df['abstract'].apply(sentence2vec, args = [model,])
new_daily_df['score_divider'] = (pd.Timestamp.today()  -new_daily_df['date'].apply(pd.to_datetime)).dt.days
#combining the data that is already run with the 
old_df = pd.read_pickle('last_month.pkl')
old_df['score_divider'] = (pd.Timestamp.today()  -old_df['date'].apply(pd.to_datetime)).dt.days

#old_df = old_df[old_df['score_divider'].astype(int)<=30]

output_df = pd.concat([new_daily_df , old_df])
output_df =output_df.drop_duplicates(subset='paper_id')
pref_df = pd.read_pickle('user_pref.pkl')
users = []
logging.info('starting scoring')

for name in list(pref_df.columns):
    if '_weight' in name.lower():
        users.append(name[:-7])
# LLM = Llama(model_path=r"llama\llama-2-7b.Q4_K_M.gguf",  n_ctx=2048, n_threads=4, )
for user in users:
    output_df[user+'_score'] = output_df['abstract_vec'].apply(get_score, args = [user,pref_df])
    output_df[user+'_score'] = output_df[user+'_score']/output_df['score_divider']#decreases the score of older papers
    output_df = output_df.sort_values(by=[user+'_score'], ascending=False).reset_index(drop=True)
    output_df.to_pickle('last_month_wo_llama.pkl')
    #llama_df = output_df.iloc[:20]
    #else_df = output_df.iloc[20:]
    #else_df['llama_abstract'] = else_df['abstract']
    #llama_df['llama_abstract'] =llama_df['abstract'].apply(get_llama_summary, args=[LLM,])
    #output_df=pd.concat([llama_df, else_df])
output_df.to_pickle('last_month.pkl')
print('all saved')
logging.info('Done @ '+datetime.now().strftime('%Y-%m-%d %H:%M'))
