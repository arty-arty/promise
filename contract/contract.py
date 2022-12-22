from pyteal import *
from beaker import *
from algosdk.future.transaction import *
from typing import Final, Literal
from beaker.lib.storage import Mapping, List


Hash = abi.StaticBytes[Literal[32]]
Answer = abi.StaticBytes[Literal[32]]
Question = abi.StaticBytes[Literal[32]]
Salt = abi.StaticBytes[Literal[32]]

class PromiseYou(Application):

    n_challenges_added: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="A counter for showing how to use application state",
        default=Int(0)
    )

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

    shuffle_round: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="A counter for showing how to use application state",
        default=Int(2**64 - 1)
    )

    n_challenges_total = int(2)
    permutation = List(abi.Uint16, n_challenges_total)
    # 16 bit = 2 byte
    # In a 32 K bytes box --> 16000 variables max
    # Let's take 1000 which would cost us less

    # Global boxes
    salted_question_hashes = List(Hash, n_challenges_total)
    salted_answer_hashes = List(Hash, n_challenges_total)
    # questions = List(abi.String, n_challenges_total)
    # user_answers = List(abi.String, n_challenges_total)
    # true_answers = List(abi.String, n_challenges_total)

    # User boxes
    booking_state_records = Mapping(
        abi.Address, abi.String, prefix=Bytes("STATE"))
    challenge_id_records = Mapping(
        abi.Address, abi.Uint16, prefix=Bytes("ID"))
    user_answer_records = Mapping(
        abi.Address, Answer, prefix=Bytes("ANSWER"))
    post_round_records = Mapping(
        abi.Address, abi.Uint64, prefix=Bytes("POST_ROUND"))
    answer_round_records = Mapping(
        abi.Address, abi.Uint64, prefix=Bytes("ANSWER_ROUND"))
    reveal_round_records = Mapping(
        abi.Address, abi.Uint64, prefix=Bytes("REVEAL_ROUND"))

    @internal(TealType.none)
    def pay(self, receiver: Expr, amount: Expr):
        return InnerTxnBuilder.Execute(
            {
                TxnField.type_enum: TxnType.Payment,
                TxnField.receiver: receiver,
                TxnField.amount: amount,
                TxnField.fee: consts.Algos(0.001),
            }
        )

    @create
    def create(self):
        return Seq(
            self.initialize_application_state()
        )

    @opt_in
    def opt_in(self):
        return self.initialize_account_state()

    @external
    def get_metadata(self, output: abi.String):
        return output.set(Bytes("ARC23_METADATA_ipfs://bafybeic3ui4dj5dzsvqeiqbxjgg3fjmfmiinb3iyd2trixj2voe4jtefgq/metadata.json"))

    # @update
    # def update(self):
    #     return self.initialize_application_state()
    shuffle_timeout = 1

    @external(authorize=Authorize.only(Global.creator_address()))
    def add_challenge(self, salted_question_hash: Hash, salted_answer_hash: Hash):
        create_boxes = If(self.n_challenges_added.get() == Int(0)).Then(Seq(
            Pop(self.salted_question_hashes.create()),
            Pop(self.salted_answer_hashes.create())
        ))
        add_challenge = Seq(
            self.salted_question_hashes[self.n_challenges_added.get()].set(
                salted_question_hash),
            self.salted_answer_hashes[self.n_challenges_added.get()].set(
                salted_answer_hash),
            self.n_challenges_added.increment()
        )
        lock_challenges_if_needed = If(self.n_challenges_added.get() == Int(self.n_challenges_total)
                                       ).Then(Seq(
                                           self.status.set(
                                               Bytes("2_RESOLVE_PRNG_SHUFFLE")),
                                           self.shuffle_round.set(
                                               Global.round() + Int(self.shuffle_timeout)),
                                       ))
        return Seq(
            Assert(self.status == Bytes("1_ADD_CHALLENGES")),
            Assert(self.n_challenges_added.get() <
                   Int(self.n_challenges_total)),
            create_boxes,
            add_challenge,
            lock_challenges_if_needed,
        )

    @ external(authorize=Authorize.only(Global.creator_address()))
    def resolve_shuffle(self, payment: abi.PaymentTransaction):
        # DO INNER TXN to RANDOM BEACON (by using internal method like in joe contract)
        # USE internal method to shuffle refernece article in a comment
        # Modulo Unbiased
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
            Assert(self.status == Bytes("2_RESOLVE_PRNG_SHUFFLE")),
            Assert(Global.round() >= self.shuffle_round.get()),
            Pop(self.permutation.create()),
            loop,
            self.status.set(Bytes("3_SOLVE_CHALLENGES"))
        )

    # Account.addres + concat Bytes("STATE")
    # Account.addres + concat Bytes("CHALLENGE")
    post_timeout = 10
    collateral = 0.2

    @ external
    def book_challenge(self, payment: abi.PaymentTransaction):
        # If account state is zero set default 1_NON-BOOKED
        payment = payment.get()

        # Carefully calculate and make users pay for their boxes + collateral
        return Seq(
            Assert(self.status == Bytes("3_SOLVE_CHALLENGES")),
            If(Not(self.booking_state_records[Txn.sender()].exists())).
            Then(self.booking_state_records[Txn.sender()].set(
                Bytes("1_NON_BOOKED"))),
            Assert(self.booking_state_records[Txn.sender()].get() == Bytes(
                "1_NON_BOOKED")),
            Assert(payment.amount() >= consts.Algos(0.1 + self.collateral)),
            Assert(payment.receiver() == self.address),
            Assert(payment.sender() == Txn.sender()),
            (post_round := abi.Uint64()).set(
                Global.round() + Int(self.post_timeout)),
            self.post_round_records[Txn.sender()].set(
                post_round),
            self.booking_state_records[Txn.sender()].set(Bytes("2_YES_BOOKED"))
        )

    answer_timeout = 5

    @ external(authorize=Authorize.only(Global.creator_address()))
    def post_challenge(self, booker: abi.Address, question: Question, salt: Salt, *, output: abi.Uint16,
                       ):
        challenge_id = self.permutation[self.n_challenges_unlocked.get()]
        salted_question_hash = self.salted_question_hashes[Btoi(
            challenge_id.get())]
        # salted_answer_hash = self.salted_answer_hashes[challenge_id.get()]

        unlock_challenge = Seq(
            Assert(salted_question_hash == Sha256(
                Concat(question.get(), salt.get()))),
            challenge_id.store_into(output),
            self.challenge_id_records[booker].set(challenge_id.get()),
            self.n_challenges_unlocked.increment())
        return Seq(
            Assert(self.status == Bytes("3_SOLVE_CHALLENGES")),
            Assert(self.booking_state_records[booker].get() == Bytes(
                "2_YES_BOOKED")),
            unlock_challenge,
            (answer_round := abi.Uint64()).set(
                Global.round() + Int(self.answer_timeout)),
            self.answer_round_records[booker].set(
                answer_round),
            self.booking_state_records[booker].set(Bytes("3_YES_POSTED"))
        )

    @external
    def no_posted_refund(self):
        post_round = self.post_round_records[Txn.sender()]
        booking_state = self.booking_state_records[Txn.sender()]
        money_back = self.pay(Txn.sender(), consts.Algos(self.collateral))

        return Seq(Assert(self.status == Bytes("3_SOLVE_CHALLENGES")),
                   Assert(booking_state.get() == Bytes("2_YES_BOOKED")),
                   Assert(Global.round() >= Btoi(post_round.get())),
                   money_back,
                   booking_state.set(Bytes("1_NON_BOOKED")))

    reveal_timeout = 5

    @external
    def answer_challenge(self, answer: Answer):
        booking_state = self.booking_state_records[Txn.sender()]

        return Seq(
            Assert(self.status == Bytes("3_SOLVE_CHALLENGES")),
            Assert(booking_state.get() == Bytes("3_YES_POSTED")),
            self.user_answer_records[Txn.sender()].set(answer.get()),
            self.reveal_round_records[Txn.sender()].set(
                Itob(Global.round() + Int(self.reveal_timeout))),
            booking_state.set(Bytes("4_YES_ANSWED"))
        )

    reward = 0.5

    # # TODO Add minus transaction fee in every pay

    @external(authorize=Authorize.only(Global.creator_address()))
    def reveal_answer(self, booker: abi.Address, answer: Answer, salt: Salt):
        booking_state = self.booking_state_records[booker]
        challenge_id = self.challenge_id_records[booker]
        salted_answer_hash = self.salted_answer_hashes[Btoi(
            challenge_id.get())]
        user_answer = self.user_answer_records[booker]
        answer_round = abi.Uint64()

        pay_reward_to_user = self.pay(booker.get(), consts.Algos(
            self.collateral + self.reward))

        earn_collateral_to_service = self.pay(Global.creator_address(), consts.Algos(
            self.collateral))

        assert_answer_is_right = Assert(
            BytesEq(salted_answer_hash.get(), Sha256(Concat(answer.get(), salt.get()))
                    ))

        return Seq(
            Assert(self.status == Bytes("3_SOLVE_CHALLENGES")),
            assert_answer_is_right,
            self.answer_round_records[booker].store_into(answer_round),
            If(
                booking_state.get() == Bytes("4_YES_ANSWED")
            ).Then(
                If(answer.get() == user_answer.get(),
                   pay_reward_to_user, earn_collateral_to_service)
            ).ElseIf(
                And(booking_state.get() == Bytes("3_YES_POSTED"),
                    Global.round() >= answer_round.get())
            ).Then(
                earn_collateral_to_service,
            ),
            booking_state.set(Bytes("1_NON_BOOKED"))
        )

    @external
    def no_reveal_refund(self):

        booking_state = self.booking_state_records[Txn.sender()]
        money_back = self.pay(Txn.sender(), consts.Algos(
            self.collateral + self.reward))
        reveal_round = abi.Uint64()
        return Seq(Assert(self.status == Bytes("3_SOLVE_CHALLENGES")),
                   Assert(booking_state.get() == Bytes("4_YES_ANSWED")),
                   self.reveal_round_records[Txn.sender()].store_into(
                       reveal_round),
                   Assert(Global.round() >= reveal_round.get()),
                   money_back,
                   booking_state.set(Bytes("1_NON_BOOKED"))
                   )
