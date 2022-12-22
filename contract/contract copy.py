from pyteal import *
from beaker import *
from algosdk.v2client import algod
from algosdk.atomic_transaction_composer import (
    TransactionSigner,
    TransactionWithSigner,
    AccountTransactionSigner,
    MultisigTransactionSigner,
)
from algosdk.future.transaction import *
from algosdk.mnemonic import to_private_key
from algosdk.encoding import encode_address, decode_address
import os
from dotenv import load_dotenv
from typing import Final, Literal
from beaker.lib.storage import Mapping, List

# Create algod client pointing to testnet node of algoexplorer
algod_address = "https://node.testnet.algoexplorerapi.io"
algod_token = ""
algod_client = algod.AlgodClient(algod_token, algod_address)

# Recover account sk from an environment value MY_MNEMONIC (put in .env)
load_dotenv()
MY_MNEMONIC = os.getenv('MY_MNEMONIC')
signer = AccountTransactionSigner(private_key=to_private_key(MY_MNEMONIC))


Affirmation = abi.StaticBytes[Literal[64]]
# Create a class, subclassing Application from beaker


class HelloBeaker(Application):
    n_challenges_unlocked: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="A counter for showing how to use application state",
        default=Int(0)
    )

    status: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.bytes,
        descr="A finite state machine status for the whole contract",
        default=Bytes("1_ADD_CHALLENGES")
    )

    n_challenges_total = int(1)
    permutation = List(abi.Uint16, n_challenges_total)
    # 16 bit = 2 byte
    # In a 32 K bytes box --> 16000 variables max
    # Let's take 1000 which would cost us less

    # Boxes mapping to user, instead of local AppStorage just to avoid opt-in, probably will change to LocalAccountStorage
    # booking_records =  Mapping(abi.Address, BookingRecord)
    booking_state_records = Mapping(
        abi.Address, abi.String, prefix=Bytes("STATE"))
    challenge_id_records = Mapping(abi.Address, abi.String, prefix=Bytes("ID"))
    user_answer_records = Mapping(abi.Address, abi.String, prefix=Bytes(""))
    post_round_records = Mapping(
        abi.Address, abi.String, prefix=Bytes("STATE"))
    reveal_round_records = Mapping(
        abi.Address, abi.String, prefix=Bytes("STATE"))

    @internal(TealType.none)
    def pay(self, receiver: Expr, amount: Expr):
        return InnerTxnBuilder.Execute(
            {
                TxnField.type_enum: TxnType.Payment,
                TxnField.receiver: receiver,
                TxnField.amount: amount,
                TxnField.fee: Int(0),
            }
        )

    @create
    def create(self):
        return Seq(self.initialize_application_state())

    @external
    def get_metadata(self, output: abi.String):
        return output.set(Bytes("ARC23_METADATA_ipfs://bafybeic3ui4dj5dzsvqeiqbxjgg3fjmfmiinb3iyd2trixj2voe4jtefgq/metadata.json"))

    # @update
    # def update(self):
    #     return self.initialize_application_state()

    @external(authorize=Authorize.only(Global.creator_address()))
    def add_challenge(self, hash_of_salted_question: abi.String, hash_of_salted_answer: abi.String):
        # ADD CHALLENGES IN BOXES
        # ENCODE DICT TYPE THERE
        # HASH OF SALTED QUESTION, HASH OF SALTED RESPONSE
        # COUNT ADDED CHALLENGES
        # Check n_challenges < MAX_CHALLENGES
        # Just lock when enough
        return Seq(
            Assert(self.status == Bytes("1_ADD_CHALLENGES")),
            # self.status.set(Bytes("2_SOLVE_CHALLENGES"))
        )

    @external(authorize=Authorize.only(Global.creator_address()))
    def lock_challenges(self):
        # ASSERT Assert(self.status == Bytes("1_ADD_CHALLENGES"))
        # Set GLOBAL VALUE SHUFFLE_RESOLUTION_ROUND to current + 15
        return Seq(self.status.set(Bytes("2_RESOLVE_PRNG_SHUFFLE")))

    @external(authorize=Authorize.only(Global.creator_address()))
    def resolve_shuffle(self, payment: abi.PaymentTransaction):
        # ASSERT Assert(self.status == Bytes("2_RESOLVE_PRNG_SHUFFLE"))
        # ASSERT CURRENT ROUND > SHUFFLE_RESOLUTION_ROUND
        # DO INNER TXN to RANDOM BEACON (by using internal method like in joe contract)
        # USE internal method to shuffle refernece article in a comment
        # Modulo Unbiased
        # For now just do not do shuffle
        # Do fake suffle for now with identity map
        # Create now just a static list with size n_challenges
        # Put numbers from 1 to n_challengesthere
        # output the shuffled list
        i = ScratchVar(TealType.uint64)
        init = i.store(Int(0))
        cond = i.load() < Int(self.n_challenges_total)
        iter = i.store(i.load() + Int(1))
        loop = For(init, cond, iter).Do(
            Seq(
                (f_i := abi.Uint16()).set(i.load()),
                self.permutation[i.load()].set(f_i),
            )
        )
        return Seq(
            Pop(self.permutation.create()),
            loop,
            self.status.set(Bytes("3_SOLVE_CHALLENGES"))
        )

    # Account.addres + concat Bytes("STATE")
    # Account.addres + concat Bytes("CHALLENGE")
    oracle_timeout_rounds = 3

    @external
    def book_challenge(self, payment: abi.PaymentTransaction):
        # If account state is zero set default 1_NON-BOOKED
        payment = payment.get()
        # Carefully calculate and make users pay for their boxes
        return Seq(
            Assert(self.status == Bytes("3_SOLVE_CHALLENGES")),
            If(Not(self.booking_state_records[Txn.sender()].exists())).
            Then(self.booking_state_records[Txn.sender()].set(
                Bytes("1_NON_BOOKED"))),
            Assert(self.booking_state_records[Txn.sender()].get() == Bytes(
                "1_NON_BOOKED")),
            Assert(payment.amount() >= consts.Algos(0.1)),
            Assert(payment.receiver() == self.address),
            Assert(payment.sender() == Txn.sender()),
            self.booking_state_records[Txn.sender()].set(Bytes("2_YES_BOOKED"))
        )
        # Write that this account booked a question (not specified each yet)
        # Just use him as a box key or something key
        # Later do not do it in basic version, write that this account has that many booked questions
        # Write that oracle must respond after currentRound + 10
        # bUG WHEN ORACLE NOT RESPONDED BUT THE INDEX MOVED ON
        # The pool of questions gets drained this way

        # Set account state to 2_BOOKED
        # Increment account deposit

    # booker: abi.Address, deciphered_question: abi.String, salt: abi.String,
    @external(authorize=Authorize.only(Global.creator_address()))
    def post_challenge(self, booker: abi.Account, question: abi.String, salt: abi.String, *, output: abi.Uint16,
                       ):
        # Assert booker state 2_YES_BOOKED
        # current_qustion id = question i
        # Check that txn note SHA(question + salt) equals specified for this question i

        # Write that this account has to answer this id before currentRound + 10
        # Write to state that this challenge was posted
        # Each challenge has its own state  (default 1_HIDDEN) change to 2_POSTED
        # Set account state to 3_POSTED
        # return Seq(
        #     self.n_challenges_unlocked.increment(),
        #     output.set(Int(1))
        # )
        return Seq(
            Assert(self.status == Bytes("3_SOLVE_CHALLENGES")),
            self.permutation[self.n_challenges_unlocked.get()
                             ].store_into(output),
            self.n_challenges_unlocked.increment()
        )

    # @external
    # def get_refund():
    #     # Assert(self.status == Bytes("3_SOLVE_CHALLENGES"))
    #     # Assert status BOOKED
    #     # Assert round > oracle_must_post challenge round
    #     # If oracle not posted Do moneyback innerTxn minus fee deducted
    #     # Or, maybe split those two money_backs
    #     # Set status NON-BOOKED

    #     # Assert round > oracle_must_revel challenge round
    #     # If oracle not revealed Do moneyback innerTxn
    #     # Plus do payout
    #     # Yes lets call this separate method pay out
    #     # Set status NON-BOOKED
    #     return Seq()

    # @external
    # def answer_challenge():
    #     # Assert(self.status == Bytes("3_SOLVE_CHALLENGES"))
    #     # Assert account state posted
    #     # Assert round > oracle_must_responded round
    #     # If oracle not responded Do moneyback innerTxn

    #     # Set account state to ANSWERED
    #     return Seq()

    # @external(authorize=Authorize.only(Global.creator_address()))
    # def reveal_answer(self, booker: abi.Address, answer: abi.String, salt: abi.String):
    #     # Assert(self.status == Bytes("3_SOLVE_CHALLENGES"))
    #     # Assert account state posted || answered
    #     # Assert Hash(answer + salt) == Hash(booker)
    #     # Assert this booker has answered question
    #     # Assert
    #     # Assert reveal time for this question has come
    #     # Assert answer ==
    #     # Set oracle revealed
    #     # Then pay him double prize
    #     #  Otherwise pay our company account InnerTXN
    #     # return account booker state to NON-BOOKED
    #     return Seq()
    # # # return  picked
    # # return pass


def demo():
    # Create an Application client
    app_client = client.ApplicationClient(
        # Get sandbox algod client
        client=algod_client,
        # Instantiate app with the program version (default is MAX_TEAL_VERSION)
        app=HelloBeaker(version=8),
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

    # app_info = algod_client.application_info(app_id)
    # account_info = algod_client.account_application_info("TIGRMMFGZEQ3RB3INBKKVAFWUHYNTHZFU7GTFUYDAQZJDW2YSIGHBLPHEQ", app_id)
    # acc_info = algod_client.account_info("TIGRMMFGZEQ3RB3INBKKVAFWUHYNTHZFU7GTFUYDAQZJDW2YSIGHBLPHEQ")
    # print(app_info, account_info, acc_info)
    # app_client.update()
    # Call the `hello` method
    # result = app_client.call(HelloBeaker.hello, name="Beaker")
    # print(result.return_value)  # "Hello, Beaker"
    # result = app_client.call(HelloBeaker.add_challenge)

    ptxn = PaymentTxn(app_client.sender, suggested_params,
                      app_addr, int(1000000*1.0))
    result = app_client.call(HelloBeaker.resolve_shuffle, payment=TransactionWithSigner(ptxn, signer),
                             boxes=[[app_client.app_id, "permutation"],
                                    [app_client.app_id, "permutation"]])

    ptxn = PaymentTxn(app_client.sender, suggested_params,
                      app_addr, int(1000000*1.0))
    result = app_client.call(
        HelloBeaker.book_challenge,
        payment=TransactionWithSigner(ptxn, signer),
        boxes=[[app_client.app_id, "STATE".encode() + decode_address(app_client.sender)],
               ])

    for i in range(0, 5):
        result = app_client.call(HelloBeaker.post_challenge, booker=app_client.sender,
                                 question="Who created algorand?",
                                 salt="fdafdfsfkok6op54jk36tnj5opmgjo",
                                 boxes=[[app_client.app_id, "permutation"],
                                        [app_client.app_id, "permutation"]])
        print(result.return_value)
    # result = app_client.call(HelloBeaker.post_challenge, booker=decode_address(app_client.sender),
    #                          deciphered_question="Que",
    #                          salt="abruhaopsjfoiehfriowehrweoih",
    #                          boxes=[[app_client.app_id, "permutation"],
    #                                 [app_client.app_id, "permutation"]])

    # def post_challenge(self, booker: abi.Address, deciphered_question: abi.String, salt: abi.String, output: abi.Uint16):
    # print("ADDED1")
    # result = app_client.call(HelloBeaker.add_challenge)
    # print("ADDED2")
    # result = app_client.call(HelloBeaker.shuffle_lock)
    # print("SHUFFLED")
    # result = app_client.call(HelloBeaker.add_challenge)
    # print("ADDED3")
if __name__ == "__main__":
    demo()
