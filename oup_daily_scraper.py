from scraper_lib import get_oup_days_back
print('OUP')
for i in range(10):
    try:
        df = get_oup_days_back(2)
        df.to_pickle(r'daily_temp_files\oup_temp.pkl')
        break
    except:
        continue