
import time
from contract.contract import PromiseYou
from algosdk.mnemonic import to_private_key
from algosdk.atomic_transaction_composer import (
    AccountTransactionSigner,
)
import os
from dotenv import load_dotenv

from algosdk.v2client import algod
from beaker import *
from _oracle.helper import getPermuatation, fetchPersonalStates, processPersonStates

questions = [
    {"question": "Who created Algorand?", "answer": "Silvio Micali",
        "salt_question": "fasdfsda", "salt_answer": "yh66534"},
    {"question": "How many TPS Algorand has?", "answer": "6000",
        "salt_question": "t4dgdfhgh5", "salt_answer": "abvg6hkl6w"},
    {"question": "Who is Algorand CTO?", "answer": "John Woods",
        "salt_question": "h1asdfgetafgh1mbnsajk", "salt_answer": "lakfgy75nbdhurjkcm1"}
]
current_n_question = -1

# Initialization. First launch deploy.py and write down your app id from the output.
app_id = 157715847
load_dotenv()
MY_MNEMONIC = os.getenv('MY_MNEMONIC')
signer = AccountTransactionSigner(private_key=to_private_key(MY_MNEMONIC))

# Connecting to testnet node of algoexplorer
algod_address = "https://node.testnet.algoexplorerapi.io"
algod_token = ""
algod_client = algod.AlgodClient(algod_token, algod_address)

# Creating app_client to make app_calls and interact with the contract
app_client = client.ApplicationClient(
    # Get sandbox algod client
    client=algod_client,
    # Instantiate app with the program version (default is MAX_TEAL_VERSION)
    app=PromiseYou(version=8),
    app_id=app_id,
    # Get acct from sandbox and pass the signer
    signer=signer,
)

# Loop every 10 seconds and process each player tracked in the smart contract, depending on their fetched state.
# Take collateral if the player did not answer in time. Post levels to players who bought them. Reveal true answers to check players who answered.
while True:
    try:
        app_state = app_client.get_application_state()
        current_n_question = app_state['n_challenges_unlocked']
        print(current_n_question)
        permutation = app_client.get_box_contents(b'permutation')
        permutation_array = getPermuatation(permutation)
        print("Permutation: ", permutation_array)

        personal_states = fetchPersonalStates(app_client)
        print(personal_states)
        processPersonStates(app_client, personal_states,
                            questions,  current_n_question, permutation_array)
        time.sleep(10)
    except Exception as inst:
        print("Exception thrown: ", inst)
