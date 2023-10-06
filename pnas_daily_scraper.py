from scraper_lib import get_pnas_days_back
print('PNAS')
for i in range(10):
    try:
        df = get_pnas_days_back(2)
        df.to_pickle('pnas_temp.pkl')
        break
    except:
        continue