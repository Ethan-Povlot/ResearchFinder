from scraper_lib import get_scopus
print('scopus')
for i in range(10):
    try:
        df = get_scopus(2)
        df.to_pickle(r'daily_temp_files\scopus_temp.pkl')
        break
    except:
        continue