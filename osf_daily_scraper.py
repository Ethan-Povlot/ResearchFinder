from scraper_lib import get_osf
print('osf')
for i in range(10):
    try:
        df = get_osf(2)
        df.to_pickle('osf_temp.pkl')
        break
    except:
        continue