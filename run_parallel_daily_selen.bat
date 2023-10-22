@echo off
cd C:\Users\ethan\Documents\ResearchFinder
start "Lancet Scraper 12" "C:/Users/ethan/AppData/Local/Programs/Python/Python311/python.exe" "C:\Users\ethan\Documents\ResearchFinder\lancet_daily_scraper.py"
timeout /t 500
start "AHA Scraper 4" "C:/Users/ethan/AppData/Local/Programs/Python/Python311/python.exe" "C:\Users\ethan\Documents\ResearchFinder\aha_daily_scraper.py"
timeout /t 500
start "Jama Scraper 9" "C:/Users/ethan/AppData/Local/Programs/Python/Python311/python.exe" "C:\Users\ethan\Documents\ResearchFinder\jama_daily_scraper.py"
timeout /t 500
start "Nature Scraper 2" "C:/Users/ethan/AppData/Local/Programs/Python/Python311/python.exe" "C:\Users\ethan\Documents\ResearchFinder\nature_daily_scraper.py"
pause