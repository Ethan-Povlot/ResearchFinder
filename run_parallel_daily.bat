@echo off
cd C:\Users\ethan\Documents\ResearchFinder
:: Start Python scripts
start "MDPI Scraper 1" "C:/Users/ethan/AppData/Local/Programs/Python/Python311/python.exe" "C:\Users\ethan\Documents\ResearchFinder\mdpi_daily_scraper.py"
timeout /t 10
start "Nature Scraper 2" "C:/Users/ethan/AppData/Local/Programs/Python/Python311/python.exe" "C:\Users\ethan\Documents\ResearchFinder\nature_daily_scraper.py"
timeout /t 10
start "Arxiv Scraper 3" "C:/Users/ethan/AppData/Local/Programs/Python/Python311/python.exe" "C:\Users\ethan\Documents\ResearchFinder\arxiv_daily_scraper.py"
timeout /t 10
start "AHA Scraper 4" "C:/Users/ethan/AppData/Local/Programs/Python/Python311/python.exe" "C:\Users\ethan\Documents\ResearchFinder\aha_daily_scraper.py"
timeout /t 10
start "OUP Scraper 5" "C:/Users/ethan/AppData/Local/Programs/Python/Python311/python.exe" "C:\Users\ethan\Documents\ResearchFinder\oup_daily_scraper.py"
timeout /t 10
start "osf Scraper 6" "C:/Users/ethan/AppData/Local/Programs/Python/Python311/python.exe" "C:\Users\ethan\Documents\ResearchFinder\osf_daily_scraper.py"
timeout /t 10
start "Scopus Scraper 7" "C:/Users/ethan/AppData/Local/Programs/Python/Python311/python.exe" "C:\Users\ethan\Documents\ResearchFinder\scopus_daily_scraper.py"
timeout /t 10
start "BioMedXiv Scraper 8" "C:/Users/ethan/AppData/Local/Programs/Python/Python311/python.exe" "C:\Users\ethan\Documents\ResearchFinder\biomedXiv_daily_scraper.py"
timeout /t 10
start "Jama Scraper 9" "C:/Users/ethan/AppData/Local/Programs/Python/Python311/python.exe" "C:\Users\ethan\Documents\ResearchFinder\jama_daily_scraper.py"
timeout /t 10
start "PubMed Scraper 10" "C:/Users/ethan/AppData/Local/Programs/Python/Python311/python.exe" "C:\Users\ethan\Documents\ResearchFinder\pubmed_daily_scraper.py"
timeout /t 10
start "PNAS Scraper 11" "C:/Users/ethan/AppData/Local/Programs/Python/Python311/python.exe" "C:\Users\ethan\Documents\ResearchFinder\pnas_daily_scraper.py"
timeout /t 10
start "ChemrXiv Scraper 12" "C:/Users/ethan/AppData/Local/Programs/Python/Python311/python.exe" "C:\Users\ethan\Documents\ResearchFinder\chemrxiv_daily_scraper.py"
timeout /t 10
start "Lancet Scraper 12" "C:/Users/ethan/AppData/Local/Programs/Python/Python311/python.exe" "C:\Users\ethan\Documents\ResearchFinder\lancet_daily_scraper.py"
