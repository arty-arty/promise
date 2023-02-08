import time
from contract.contract import PromiseYou
from algosdk.mnemonic import to_private_key
from algosdk.future.transaction import *
from algosdk.atomic_transaction_composer import (
    AccountTransactionSigner,
)
import os
from dotenv import load_dotenv

from algosdk.encoding import decode_address
from algosdk.v2client import indexer, algod
from beaker import *
import array
from algosdk.atomic_transaction_composer import (
    AccountTransactionSigner,
)

from client.helper import fetchPersonalInfo, getMyChallengeId,\
    bookChallenge, answerChallenge, refundNoReveal, refundNoPosted

# Initialization. Same app id as in oracle.py must be specified.
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

# Get suggested params from the node
suggested_params = algod_client.suggested_params()

# Get my account address in bytes
personal_state_holder = decode_address(app_client.sender)

print("Hello Dear Mr.Stranger!")


def step():
    """
    This functions mirrors the internal state machine of the Promise smart contract.
    Depending on the current state of a playing user. It either does a refund if the user is eligible.
    Sends user's answer in smart contract. Or just books a new challenge.
    """

    # Fetch the state. If the user has not interacted yet or was reset. Its the same as "1_NON_BOOKED" state
    state = fetchPersonalInfo(app_client, b"STATE")
    try:
        state = state[b"STATE"+personal_state_holder][0]
    except:
        state = b"1_NON_BOOKED"

    # Book a challenge in case the user has not booked yet.
    if state == b'1_NON_BOOKED':
        print("In a moment you will buy one question for one ALGO")
        print("The transaction has started")
        bookChallenge(app_client, suggested_params)
        print("Transaction succeeded. A question was booked.")
        print("Waiting a bit for the server to post a question.")
        print("")
        time.sleep(15)

    # Try to get a refund if the user has booked, but the server did not post the question.
    if state == b'2_YES_BOOKED':
        print("Sorry, your question was not posted by the server.")
        print("Trying to get you a refund")
        refundNoPosted(app_client)
        print("You got refunded")
        print("")
        time.sleep(15)

    #
    if state == b'3_YES_POSTED':
        questions = fetchPersonalInfo(b"salted_question_hashes")[
            b"salted_question_hashes"]
        n_for_user = getMyChallengeId(app_client, personal_state_holder)
        print("You booked a question with random index: ", n_for_user)
        question = questions[n_for_user]
        question = question.decode()
        print(
            f"The question number {n_for_user} was indeed posted by the server")
        print(f"Please answer the question number {n_for_user}")
        print("")
        print(question)
        answer = input("Your answer: ")
        answerChallenge(app_client, answer)
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

    # Try to get a refund if the user has answered, but the server did not reveal the true answer.
    if state == b'4_YES_ANSWED':
        print(
            "Sorry, your question was not validated by the server. Probably it went down.")
        print("Trying to get you a refund")
        refundNoReveal(app_client)
        print("You got refunded")
        print("")
        time.sleep(15)


for i in range(100):
    step()
