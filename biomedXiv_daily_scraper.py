from scraper_lib import get_bioMedxiv
print("bioMedxiv")
for i in range(10):
    try:
        df = get_bioMedxiv(2)
        df.to_pickle(r'daily_temp_files\bioMedxiv_temp.pkl')
        break
    except:
        continue