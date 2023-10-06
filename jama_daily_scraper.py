from scraper_lib import jama_get_days_back
print("bioMedxiv")
for i in range(10):
    try:
        df = jama_get_days_back(5)
        df.to_pickle('bioMedxiv_temp.pkl')
        break
    except:
        continue