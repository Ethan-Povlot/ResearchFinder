import requests
try:
   response = requests.post('http://researchfinder.ddns.net/shutdown')
except:
   pass

#this code trys to kill the current website so a new one can be instantated and take over, for memory reasons 