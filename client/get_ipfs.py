import urllib.request 
import json

# content ID
cid = "bafkreifacnxyt7p45fat7nirzcqhw45ac4lphyqb5ltyrnpttq3iqm4miu"

# read .json
with urllib.request.urlopen(f"https://dweb.link/ipfs/{cid}") as url:
    data = json.loads(url.read())