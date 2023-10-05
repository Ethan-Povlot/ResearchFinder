from scraper_lib import get_nature_days_back
print('nature')
for i in range(10):
    #try:
    df = get_nature_days_back(6)
    df.to_pickle('nature_temp.pkl')
    break
    #except Exception as e:
    #    print(e)
    #    continue
