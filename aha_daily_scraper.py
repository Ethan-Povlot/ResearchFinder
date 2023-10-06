from scraper_lib import get_aha_journal_days_back
print('arxiv')
for i in range(10):
    try:
        df = get_aha_journal_days_back(2)
        df.to_pickle('aha_temp.pkl')
        break
    except:
        continue