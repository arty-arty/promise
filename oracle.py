
import time
from contract.contract import PromiseYou
from algosdk.mnemonic import to_private_key
from algosdk.atomic_transaction_composer import (
    AccountTransactionSigner,
)
import os
from dotenv import load_dotenv

from algosdk.encoding import encode_address, decode_address
from algosdk.v2client import indexer, algod
from base64 import b64decode
from beaker import *
import sys
import array

questions = [
    {"question": "Who created Algorand?", "answer": "Silvio Micali",
        "salt_question": "fasdfsda", "salt_answer": "yh66534"},
    {"question": "Who created Algorand?", "answer": "Silvio Micali",
        "salt_answer": "yh66534", "salt_question": "fasdfsda"},
    {"question": "Who created Algorand?", "answer": "Silvio Micali", "salt_answer": "yh66534", "salt_question": "fasdfsda"}]


def getQuestionAnswer(n_challenge):
    permuted_index = permutation_array[n_challenge]
    question = questions[permuted_index]
    return question


def getPermuatation(permutation):
    permutation_arr = array.array('H', permutation)
    permutation_arr.byteswap()
    return list(permutation_arr)


def fetchPersonalStates():
    boxes_names = app_client.get_box_names()
    personal_state_holders = [
        name for name in boxes_names if name.startswith(b"STATE")]
    personal_state_values = [app_client.get_box_contents(
        state) for state in personal_state_holders]
    return dict(zip(personal_state_holders, personal_state_values))


def processPersonStates(personal_states):
    for person_state in personal_states.items():
        processPersonState(person_state)
    pass


def processPersonState(person_state):
    personal_state_holder, personal_state_value = person_state
    print(personal_state_value)
    if (personal_state_value == b'2_YES_BOOKED'):
        postChallenge(personal_state_holder)

    if (personal_state_value == b'3_YES_POSTED'):
        # Trying to get the collateral, if user did not respond in time!
        try:
            revealAnswer(personal_state_holder)
        except Exception as inst:
            print("Person still has time to answer", inst)

    if (personal_state_value == b'4_YES_ANSWED'):
        revealAnswer(personal_state_holder)


def revealAnswer(personal_state_holder):
    # To do ATC Calls
    personal_state_holder = personal_state_holder.replace(
        b'STATE', b'')
    str_address = encode_address(
        personal_state_holder)

    # Get which n is for this user
    n_for_user = app_client.get_box_contents(b'ID' + personal_state_holder)
    n_for_user = getPermuatation(n_for_user)[0]

    print("N for user: ", n_for_user)

    # Retrieve
    question = questions[n_for_user]

    result = app_client.call(PromiseYou.reveal_answer, booker=str_address,
                             answer=question["answer"].ljust(
                                 32, " ").encode(),
                             salt=question["salt_answer"].ljust(
                                 32, " ").encode(),
                             boxes=[[app_client.app_id, "permutation"],
                                    [app_client.app_id, "permutation"],
                                    [app_client.app_id, "salted_answer_hashes"],
                                    [app_client.app_id, "STATE".encode(
                                    ) + personal_state_holder],
                                    [app_client.app_id, "ANSWER_ROUND".encode(
                                    ) + personal_state_holder],
                                    [app_client.app_id, "ID".encode(
                                    ) + personal_state_holder],
                                    [app_client.app_id, "ANSWER".encode(
                                    ) + personal_state_holder]
                                    ],
                             )


def postChallenge(personal_state_holder):
    personal_state_holder = personal_state_holder.replace(
        b'STATE', b'')
    str_address = encode_address(
        personal_state_holder)
    print("Holder: ", personal_state_holder, str_address, current_n_question)
    question = getQuestionAnswer(current_n_question)
    # Do it through atc to parallel process many players at once
    result = app_client.call(PromiseYou.post_challenge, booker=encode_address(
        personal_state_holder),
        question=question["question"].ljust(
        32, " ").encode(),
        salt=question["salt_question"].ljust(32, " ").encode(),
        boxes=[[app_client.app_id, "permutation"],
               [app_client.app_id, "permutation"],
               [app_client.app_id, "salted_question_hashes"],
               [app_client.app_id, "STATE".encode(
               ) + personal_state_holder],
               [app_client.app_id, "ANSWER_ROUND".encode(
               ) + personal_state_holder],
               [app_client.app_id, "ID".encode(
               ) + personal_state_holder]
               ])
    print("Posted challenge for ", str_address)
    # current_n_question = current_n_question + 1


# Initialization. First launch deploy.py and write down your app id from the output. 
app_id = 157599221
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
# Loop every 10 seconds
# Wrap in try just in case
current_n_question = -1
while True:
    try:
        app_state = app_client.get_application_state()
        current_n_question = app_state['n_challenges_unlocked']
        print(current_n_question)
        permutation = app_client.get_box_contents(b'permutation')
        permutation_array = getPermuatation(permutation)
        print("Permutation: ", permutation_array)

        personal_states = fetchPersonalStates()
        print(personal_states)
        processPersonStates(personal_states)
        time.sleep(10)
    except Exception as inst:
        print("Exception thrown: ", inst)

# box_name = decode_address(
#     "TIGRMMFGZEQ3RB3INBKKVAFWUHYNTHZFU7GTFUYDAQZJDW2YSIGHBLPHEQ")
# box = indexer_client.application_box_by_name(app_id, box_name)
# print(box)
