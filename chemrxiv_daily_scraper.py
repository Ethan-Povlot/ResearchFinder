from scraper_lib import get_chemrxiv
print("chemrxiv")
for i in range(10):
    try:
        df = get_chemrxiv(100)
        df.to_pickle('chemrxiv_temp.pkl')
        break
    except:
        continue