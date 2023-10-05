from scraper_lib import get_pubmed
print("pubmed")
for i in range(10):
    try:
        df = get_pubmed(2)
        df.to_pickle('pubmed_temp.pkl')
        break
    except:
        continue