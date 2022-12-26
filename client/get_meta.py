app_id = 149516899
from algosdk.v2client import indexer
import base64

algod_address = "https://indexer.testnet.algoexplorerapi.io"
algod_token = ""
headers = {}

# algod_address = "https://testnet-algorand.api.purestake.io/idx2"
# algod_token = "Fq31ZjgKfQ2cNUasrgv554yazzPBA2Dg9RhkV8Uo"
# headers = {
#    "X-API-Key": algod_token,
# }
indexer_client = indexer.IndexerClient(algod_token, algod_address, headers)

apps = indexer_client.search_applications(app_id)
#print(apps)

creation_round = apps["applications"][0]["created-at-round"]
creator = apps["applications"][0]["params"]["creator"]

transactions = indexer_client.search_transactions(
    address=creator, 
    application_id=0, 
#    block=creation_round,
#    note_prefix="hello".encode(),
    )
#transactions filter by appplication-id = 0 to only include creation

# Probably should handle updates 
# Because the code could change

print(transactions)

indexer_client.