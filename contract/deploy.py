import time
from pyteal import *
from beaker import *
from algosdk.v2client import algod
from algosdk.atomic_transaction_composer import (
    TransactionWithSigner,
    AccountTransactionSigner,
    AtomicTransactionComposer,
)
from algosdk.future.transaction import *
from algosdk.mnemonic import to_private_key
import os
from dotenv import load_dotenv
from hashlib import sha256

from contract import PromiseYou

# Create algod client pointing to testnet node of algoexplorer
algod_address = "https://node.testnet.algoexplorerapi.io"
algod_token = ""
algod_client = algod.AlgodClient(algod_token, algod_address)

# Recover account sk from an environment value MY_MNEMONIC (put in .env)
load_dotenv()
MY_MNEMONIC = os.getenv('MY_MNEMONIC')
signer = AccountTransactionSigner(private_key=to_private_key(MY_MNEMONIC))


def deploy():
    # Create an Application client
    app_client = client.ApplicationClient(
        # Get sandbox algod client
        client=algod_client,
        # Instantiate app with the program version (default is MAX_TEAL_VERSION)
        app=PromiseYou(version=8),
        # Get acct from sandbox and pass the signer
        signer=signer,
    )

    # Deploy the app on-chain
    suggested_params = algod_client.suggested_params()
    app_id, app_addr, txid = app_client.create(
        suggested_params=suggested_params)
    print(
        f"""Deployed app in txid {txid}
        App ID: {app_id}
        Address: {app_addr}
    """
    )

    # Same questions should be put in oracle.py
    questions = [
        {"question": "Who created Algorand?", "answer": "Silvio Micali",
         "salt_question": "fasdfsda", "salt_answer": "yh66534"},
        {"question": "How many TPS Algorand has?", "answer": "6000",
         "salt_question": "t4dgdfhgh5", "salt_answer": "abvg6hkl6w"},
        {"question": "Who is Algorand CTO?", "answer": "John Woods",
         "salt_question": "h1asdfgetafgh1mbnsajk", "salt_answer": "lakfgy75nbdhurjkcm1"}
    ]

    # Pay sufficient funds for box storage
    ptxn = PaymentTxn(app_client.sender, suggested_params,
                      app_addr, int(1000000*1.0))
    atc = AtomicTransactionComposer()
    atc.add_transaction(TransactionWithSigner(ptxn, signer))
    result = atc.execute(algod_client, 4)

    # Loops through all the questions and add hashed challenges
    for i, challenge in enumerate(questions):
        question_hash = sha256(
            challenge["question"].ljust(32, " ").encode('utf-8') +
            challenge["salt_question"].ljust(32, " ").encode('utf-8')
        ).digest()
        answer_hash = sha256(
            challenge["answer"].ljust(32, " ").encode('utf-8') +
            challenge["salt_answer"].ljust(32, " ").encode('utf-8'),
        ).digest()
        app_client.call(PromiseYou.add_challenge, salted_question_hash=question_hash,
                        salted_answer_hash=answer_hash,
                        boxes=[[app_client.app_id, "salted_question_hashes"],
                               [app_client.app_id, "salted_answer_hashes"]])
        print(i)
    print("Added All Challenges")

    # Wait some time for the future round when VRF beacon can be resolved
    time.sleep(10)

    # Call contract to resolve randomness and do unbiased Knuth-Yao shuffling of questions
    app_client.call(PromiseYou.resolve_shuffle, random_contract=110096026, payment=TransactionWithSigner(ptxn, signer),
                    boxes=[[app_client.app_id, "permutation"],
                           [app_client.app_id, "permutation"]])
    print("Resolved Shuffle")
    print("")
    print("The contract is ready for players and oracle")
    print("Remember to put the app_id you got now in client.py and oracle.py")
    print("")
    print("Have a great day and thanks for using!")


if __name__ == "__main__":
    deploy()
