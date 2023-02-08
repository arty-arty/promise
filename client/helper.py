import array
from contract.contract import PromiseYou
from algosdk.future.transaction import *

from algosdk.encoding import decode_address
from beaker import *
import array
from algosdk.atomic_transaction_composer import (
    TransactionWithSigner,
)

# Here are some utility functions to get the info/boxes we need from node


def divide_chunks(l, n):
    """A function to divide list in chunks of length n to read Beaker Lists"""
    for i in range(0, len(l), n):
        yield l[i:i + n]


def fetchPersonalInfo(app_client, infotype):
    """A function to fetch personal info, like a question string assigned to my account"""
    boxes_names = app_client.get_box_names()
    personal_state_holders = [
        name for name in boxes_names if name.startswith(infotype)]
    personal_state_values = [list(divide_chunks(app_client.get_box_contents(
        state), 32)) for state in personal_state_holders]
    return dict(zip(personal_state_holders, personal_state_values))


def getPermuatation(app_client):
    "A function to get the order of shuffled questions"
    permutation = app_client.get_box_contents(b'permutation')
    permutation_arr = array.array('H', permutation)
    permutation_arr.byteswap()
    return list(permutation_arr)


def getMyChallengeId(app_client, personal_state_holder):
    """A function to get the question id assigned to an account of personal_state holder"""
    n_for_user = app_client.get_box_contents(
        b'ID' + personal_state_holder)
    n_for_user = array.array('H', n_for_user)
    n_for_user.byteswap()
    return n_for_user[0]

# Below are app_call wrappers to make code better readable


def bookChallenge(app_client, suggested_params):
    ptxn = PaymentTxn(app_client.sender, suggested_params,
                      app_client.app_addr, int(1000000*1.0))
    app_client.call(
        PromiseYou.book_challenge,
        payment=TransactionWithSigner(ptxn, app_client.signer),
        boxes=[[app_client.app_id, "STATE".encode() + decode_address(app_client.sender)],
               [app_client.app_id, "POST_ROUND".encode(
               ) + decode_address(app_client.sender)]
               ])


def answerChallenge(app_client, answer):
    app_client.call(PromiseYou.answer_challenge,
                    answer=answer.ljust(32, " ").encode(),
                    boxes=[
                        [app_client.app_id, "STATE".encode(
                        ) + decode_address(app_client.sender)],
                        [app_client.app_id, "REVEAL_ROUND".encode(
                        ) + decode_address(app_client.sender)],
                        [app_client.app_id, "ANSWER".encode(
                        ) + decode_address(app_client.sender)]
                    ])


def refundNoReveal(app_client):
    app_client.call(PromiseYou.no_reveal_refund,
                    boxes=[
                        [app_client.app_id, "STATE".encode(
                        ) + decode_address(app_client.sender)],
                        [app_client.app_id, "REVEAL_ROUND".encode(
                        ) + decode_address(app_client.sender)],
                    ])


def refundNoPosted(app_client):
    app_client.call(PromiseYou.no_posted_refund,
                    boxes=[
                        [app_client.app_id, "STATE".encode(
                        ) + decode_address(app_client.sender)],
                        [app_client.app_id, "POST_ROUND".encode(
                        ) + decode_address(app_client.sender)],
                    ])
