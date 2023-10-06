from scraper_lib import get_mdpi_days_back
print('mdpi')
for i in range(10):
    #try:
    df = get_mdpi_days_back(2)
    df.to_pickle('mdpi_temp.pkl')
    # break
    # except:
    #     continue