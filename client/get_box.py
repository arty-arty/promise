app_id = 149558694
from algosdk.v2client import indexer
from algosdk.encoding import encode_address, decode_address 

algod_address = "https://indexer.testnet.algoexplorerapi.io"
algod_token = ""
headers = {}


#apps = indexer_client.search_applications(app_id)

algod_address = "https://testnet-algorand.api.purestake.io/idx2"
algod_token = "Fq31ZjgKfQ2cNUasrgv554yazzPBA2Dg9RhkV8Uo"
headers = {
   "X-API-Key": algod_token,
}

indexer_client = indexer.IndexerClient(algod_token, algod_address, headers)
boxes = indexer_client.application_boxes(app_id)
print(boxes)

box_name = decode_address("TIGRMMFGZEQ3RB3INBKKVAFWUHYNTHZFU7GTFUYDAQZJDW2YSIGHBLPHEQ")
box = indexer_client.application_box_by_name(app_id, box_name)
print(box)