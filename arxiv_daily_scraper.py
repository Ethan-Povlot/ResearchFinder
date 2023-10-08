from scraper_lib import get_arxiv_days_back
print('arxiv')
for i in range(10):
    try:
        df = get_arxiv_days_back(2)
        df.to_pickle(r'daily_temp_files\arxiv_temp.pkl')
        break
    except:
        continue