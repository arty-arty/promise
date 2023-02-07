import time
from algosdk.future.transaction import *
from contract.contract import PromiseYou
from algosdk.mnemonic import to_private_key
from algosdk.atomic_transaction_composer import (
    TransactionSigner,
    TransactionWithSigner,
    AccountTransactionSigner,
    MultisigTransactionSigner,
    AtomicTransactionComposer,
)
import os
from dotenv import load_dotenv

from algosdk.encoding import encode_address, decode_address
from algosdk.v2client import indexer, algod
from base64 import b64decode
from beaker import *


def fetchPersonalQuestions():
    boxes_names = app_client.get_box_names()
    personal_state_holders = [
        name for name in boxes_names if name.startswith(b"STATE")]
    personal_state_values = [app_client.get_box_contents(
        state) for state in personal_state_holders]
    return dict(zip(personal_state_holders, personal_state_values))


app_id = 150907793
load_dotenv()
MY_MNEMONIC = os.getenv('MY_MNEMONIC')
signer = AccountTransactionSigner(private_key=to_private_key(MY_MNEMONIC))

algod_address = "https://testnet-algorand.api.purestake.io/idx2"
algod_token = "Fq31ZjgKfQ2cNUasrgv554yazzPBA2Dg9RhkV8Uo"
headers = {
    "X-API-Key": algod_token,
}
indexer_client = indexer.IndexerClient(algod_token, algod_address, headers)

algod_address = "https://node.testnet.algoexplorerapi.io"
algod_token = ""
algod_client = algod.AlgodClient(algod_token, algod_address)

app_client = client.ApplicationClient(
    # Get sandbox algod client
    client=algod_client,
    # Instantiate app with the program version (default is MAX_TEAL_VERSION)
    app=PromiseYou(version=8),
    app_id=app_id,
    # Get acct from sandbox and pass the signer
    signer=signer,
)
suggested_params = algod_client.suggested_params()

# Pay for the challenge and book it.
ptxn = PaymentTxn(app_client.sender, suggested_params,
                  app_client.app_addr, int(1000000*1.0))
result = app_client.call(
    PromiseYou.book_challenge,
    payment=TransactionWithSigner(ptxn, signer),
    boxes=[[app_client.app_id, "STATE".encode() + decode_address(app_client.sender)],
           [app_client.app_id, "POST_ROUND".encode(
           ) + decode_address(app_client.sender)]
           ])
print("Booked Challenge")

# Wait for unblinded question instead of a hash
# Just query it from my box with my address

# Do answer from input line

# result = app_client.call(PromiseYou.answer_challenge,
#                          answer="Silvio Micali".ljust(32, " ").encode(),
#                          boxes=[
#                                 [app_client.app_id, "STATE".encode(
#                                 ) + decode_address(app_client.sender)],
#                              [app_client.app_id, "REVEAL_ROUND".encode(
#                              ) + decode_address(app_client.sender)],
#                              [app_client.app_id, "ANSWER".encode(
#                              ) + decode_address(app_client.sender)]
#                          ])
# print("Answered challenge")
