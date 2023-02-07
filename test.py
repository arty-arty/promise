import time
from contract.contract import PromiseYou
from algosdk.mnemonic import to_private_key
from algosdk.future.transaction import *
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
from algosdk.atomic_transaction_composer import (
    TransactionSigner,
    TransactionWithSigner,
    AccountTransactionSigner,
    MultisigTransactionSigner,
    AtomicTransactionComposer,
)


def divide_chunks(l, n):
    # looping till length l
    for i in range(0, len(l), n):
        yield l[i:i + n]


def fetchPersonalInfo(infotype):
    boxes_names = app_client.get_box_names()
    personal_state_holders = [
        name for name in boxes_names if name.startswith(infotype)]
    personal_state_values = [list(divide_chunks(app_client.get_box_contents(
        state), 32)) for state in personal_state_holders]
    return dict(zip(personal_state_holders, personal_state_values))


# Function to find my id
def getPermuatation():
    permutation = app_client.get_box_contents(b'permutation')
    permutation_arr = array.array('H', permutation)
    permutation_arr.byteswap()
    return list(permutation_arr)


def getMyChallengeId(personal_state_holder):
    n_for_user = app_client.get_box_contents(
        b'ID' + personal_state_holder)
    n_for_user = array.array('H', n_for_user)
    n_for_user.byteswap()
    return n_for_user[0]


# Initialization. Same app id as in oracle.py must be specified.
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

suggested_params = algod_client.suggested_params()
personal_state_holder = decode_address(app_client.sender)

print("Hello Dear Mr.Stranger")


def step():
    state = fetchPersonalInfo(b"STATE")
    try:
        state = state[b"STATE"+personal_state_holder][0]
    except:
        state = b"1_NON_BOOKED"

    if state == b'1_NON_BOOKED':
        print("In a moment you will buy one question for one ALGO")
        print("The transaction has started")
        ptxn = PaymentTxn(app_client.sender, suggested_params,
                          app_client.app_addr, int(1000000*1.0))
        result = app_client.call(
            PromiseYou.book_challenge,
            payment=TransactionWithSigner(ptxn, signer),
            boxes=[[app_client.app_id, "STATE".encode() + decode_address(app_client.sender)],
                   [app_client.app_id, "POST_ROUND".encode(
                   ) + decode_address(app_client.sender)]
                   ])
        print("Transaction succeeded. A question was booked.")
        print("Waiting a bit for the server to post a question.")
        print("")
        time.sleep(15)

    if state == b'2_YES_BOOKED':
        print("Sorry, your question was not posted by the server.")
        print("Trying to get you a refund")
        result = app_client.call(PromiseYou.no_posted_refund,
                                 boxes=[
                                     [app_client.app_id, "STATE".encode(
                                     ) + decode_address(app_client.sender)],
                                     [app_client.app_id, "POST_ROUND".encode(
                                     ) + decode_address(app_client.sender)],
                                 ])
        print("You got refunded")
        print("")
        time.sleep(15)

    if state == b'3_YES_POSTED':
        permutation = getPermuatation()
        # print("Permutation:", permutation)
        questions = fetchPersonalInfo(b"salted_question_hashes")[
            b"salted_question_hashes"]
        # print(questions)
        n_for_user = getMyChallengeId(personal_state_holder)
        print("You booked a question with random index: ", n_for_user)
        question = questions[n_for_user]
        # print("My address:", personal_state_holder)
        question = question.decode()
        print(
            f"The question number {n_for_user} was indeed posted by the server")
        print(f"Please answer the question number {n_for_user}")
        print("")
        print(question)
        answer = input("Your answer: ")
        result = app_client.call(PromiseYou.answer_challenge,
                                 answer=answer.ljust(32, " ").encode(),
                                 boxes=[
                                     [app_client.app_id, "STATE".encode(
                                     ) + decode_address(app_client.sender)],
                                     [app_client.app_id, "REVEAL_ROUND".encode(
                                     ) + decode_address(app_client.sender)],
                                     [app_client.app_id, "ANSWER".encode(
                                     ) + decode_address(app_client.sender)]
                                 ])
        print("You answered the challenge")
        print("The server will unlock the contract with the right answer")
        print("So it will send you the prize in a couple of rounds if you're right")
        print("Check your wallet!")
        print("")
        print("Otherwise if the server went down the client.py will call contract refund method")
        print("And you will get the prize anyway!")
        print("")
        print("Launch client.py again to play new questions. You are always welcome!")
        exit()
        time.sleep(15)

    if state == b'4_YES_ANSWED':
        print(
            "Sorry, your question was not validated by the server. Probably it went down.")
        print("Trying to get you a refund")
        result = app_client.call(PromiseYou.no_reveal_refund,
                                 boxes=[
                                     [app_client.app_id, "STATE".encode(
                                     ) + decode_address(app_client.sender)],
                                     [app_client.app_id, "REVEAL_ROUND".encode(
                                     ) + decode_address(app_client.sender)],
                                 ])
        print("You got refunded")
        print("")
        time.sleep(15)


for i in range(100):
    step()
