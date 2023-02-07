from pyteal import *
from beaker import *
from algosdk.v2client import algod
from algosdk.atomic_transaction_composer import (
    TransactionSigner,
    TransactionWithSigner,
    AccountTransactionSigner,
    MultisigTransactionSigner,
    AtomicTransactionComposer,
)
from algosdk.future.transaction import *
from algosdk.mnemonic import to_private_key
from algosdk.encoding import encode_address, decode_address
import os
from dotenv import load_dotenv
from typing import Final, Literal
from beaker.lib.storage import Mapping, List
from hashlib import sha3_256, sha256

from contract import PromiseYou

# Create algod client pointing to testnet node of algoexplorer
algod_address = "https://node.testnet.algoexplorerapi.io"
algod_token = ""
algod_client = algod.AlgodClient(algod_token, algod_address)

# Recover account sk from an environment value MY_MNEMONIC (put in .env)
load_dotenv()
MY_MNEMONIC = os.getenv('MY_MNEMONIC')
signer = AccountTransactionSigner(private_key=to_private_key(MY_MNEMONIC))


Hash = abi.StaticBytes[Literal[32]]
Answer = abi.StaticBytes[Literal[32]]
Question = abi.StaticBytes[Literal[32]]
Salt = abi.StaticBytes[Literal[32]]

# Create a class, subclassing Application from beaker

# Just 1 for debugging


def demo():
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

    salt_question = "fasdfsda"
    salt_answer = "yh66534"
    question = "Who created Algorand?"
    answer = "Silvio Micali"
    question_hash = sha256(
        question.ljust(32, " ").encode('utf-8') +
        salt_question.ljust(32, " ").encode('utf-8')
    ).digest()
    answer_hash = sha256(
        (answer).ljust(32, " ").encode('utf-8') +
        (salt_answer).ljust(32, " ").encode('utf-8'),
    ).digest()
    print(question_hash, answer_hash)

    # .ljust(  32, " ").encode()
    ptxn = PaymentTxn(app_client.sender, suggested_params,
                      app_addr, int(1000000*1.0))
    atc = AtomicTransactionComposer()
    atc.add_transaction(TransactionWithSigner(ptxn, signer))
    result = atc.execute(algod_client, 4)
    for i in range(0, 3):
        app_client.call(PromiseYou.add_challenge, salted_question_hash=question_hash,
                        salted_answer_hash=answer_hash,
                        boxes=[[app_client.app_id, "salted_question_hashes"],
                               [app_client.app_id, "salted_answer_hashes"]])
        print(i)
    print("Added Challenges", "Addres of adder: ")

    # import time
    # time.sleep(10)

    ptxn = PaymentTxn(app_client.sender, suggested_params,
                      app_addr, int(1000000*1.0))
    result = app_client.call(PromiseYou.resolve_shuffle, random_contract=110096026, payment=TransactionWithSigner(ptxn, signer),
                             boxes=[[app_client.app_id, "permutation"],
                                    [app_client.app_id, "permutation"]])
    print("Resolved Shuffle", result.return_value)


if __name__ == "__main__":
    demo()
