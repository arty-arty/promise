import inspect
import sys
from pyteal import *
from beaker import *
from typing import Final, Literal
from beaker.lib.storage import Mapping, List

try:
    from lib_algo_random import shuffleList
except:
    from lib_algo_random import shuffleList

# Initialize 32 character long string types. Later, to store challenges in boxes.
Hash = abi.StaticBytes[Literal[32]]
Answer = abi.StaticBytes[Literal[32]]
Question = abi.StaticBytes[Literal[32]]
Salt = abi.StaticBytes[Literal[32]]


class PromiseYou(Application):
    """
    The app Promise is a mathematical protocol to solve cheating in games once and for all. 
    Plus a multidtude of other benefits. Read the docs https://github.com/arty-arty/promise to get more.
    Inherited from Beaker Application class and added our Promise protocol business logic.
    Including methods, subroutines, local state variables, and boxes.
    """

    # A counter to stop the owner from adding more questions than agreed beforehand.
    n_challenges_added: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="A counter showing how many challenges are already added",
        default=Int(0)
    )

    # An incremetal counter crucial to give each next user the next question from shuffled bag.
    n_challenges_unlocked: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="An incremental counter showing how many challenges were already booked by users",
        default=Int(0)
    )

    # A status which defines if new challenges can be added, or if enough they can be shuffled, or if shuffled the games can be begin.
    status: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.bytes,
        descr="A finite state machine status for the whole contract",
        default=Bytes("1_ADD_CHALLENGES")
    )

    # A round in the future when an inner transaction is made to the randomness beacon. This future round seed is used in the VRF.
    shuffle_round: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="A round in the future when the random bits are retrieved from the beacon",
        default=Int(2**64 - 1)
    )

    """
    A hardcoded variable below denoting total number of challenges.
    Note that the biggest box is 32K bytes in Algorand.
    A list of 16bit ints can be upto 16000 long. So n_challenges can be seamlessly increased in production.
    For serious games we could just allocate more boxes bypassing the limit.
    """
    n_challenges_total = int(3)
    permutation = List(abi.Uint16, n_challenges_total)

    """
    Global boxes below represent a vault to store all the hashed questions and answers. Making up all game levels.
    Please note that the concept of questions and answers is intendedly vague.
    Question is any challenge and could be a link to IPFS. IPFS could store the whole game level, images and all resources.
    Answers could be anything the right coordinates, the right combination, the right sequence...
    Just one prerequisite the Question must have only one right Answer. Then the Promise protocol works.
    """
    salted_question_hashes = List(Hash, n_challenges_total)
    salted_answer_hashes = List(Hash, n_challenges_total)

    """
    Boxes below containing individual state records for each user.
    These boxes power the heart of the contract - the state machine.
    Depending the individual state, the user is allowed to do only one action from the list:
    Book a question, or call a money-back method, or answer the question / receive payout.
    """
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
        """A small helper function to pay users or owner once eligible."""
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

    # An example timeout in rounds (very small for quick testing) after which the random beacon is queried and questions are shuffled. Might be increased for production.
    shuffle_timeout = 1

    @external(authorize=Authorize.only(Global.creator_address()))
    def add_challenge(self, salted_question_hash: Hash, salted_answer_hash: Hash):
        """
        This method just writes the challenges into the box storage. 
        Both hashed question and answer are written. 
        Stops and locks questions when enough of them are added.
        """
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

    @external(authorize=Authorize.only(Global.creator_address()))
    def resolve_shuffle(self, random_contract: abi.Application, payment: abi.PaymentTransaction,):
        """
        Once the future shuffle_round has come this method can be triggered to retreive the random bits 
        from the beacon and shuffle the questions using an unbiased algorithm. Now the state is set
        to be ready for players. Shuffling again is forbidden by the state machine.
        """

        # The following algorithm is an excerpt from out PyTeal library lib_algo_random to shuffle arrays, or have Uniform[0, n] random.
        # The mathematical benefit - it has no modulo bias. Completely.
        # No bias was achieved by using an optimized version of rejection sampling.
        # Inspired by publication (https://dl.acm.org/doi/10.1145/3009909) with algorithm analysis and more insights.

        # We developed the library during the hackathon for the open-source community of Algorand
        randomBits = ScratchVar(TealType.bytes)
        shuffle_round = abi.Uint64()

        getRandomBits = Seq(
            # Just for faster debugging remove Int(10) in production.
            shuffle_round.set(self.shuffle_round.get() - Int(10)),
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.MethodCall(
                app_id=random_contract.application_id(),
                method_signature="must_get(uint64,byte[])byte[]",
                args=[shuffle_round,
                      Global.current_application_address()]
            ),
            InnerTxnBuilder.Submit(),
            randomBits.store(InnerTxn.last_log())
        )
        currBitN = ScratchVar(TealType.uint64)

        i = ScratchVar(TealType.uint64)
        init = i.store(Int(0))
        cond = i.load() < Int(self.n_challenges_total)
        iter = i.store(i.load() + Int(1))
        initPermutation = For(init, cond, iter).Do(
            Seq(
                (f_i := abi.Uint16()).set(i.load()),
                self.permutation[i.load()].set(f_i),
            )
        )

        # Query the random beacon, use random bits to shuffle the questions, and change state to be ready for players.
        return Seq(
            Assert(self.status == Bytes("2_RESOLVE_PRNG_SHUFFLE")),
            Assert(random_contract.application_id() == Int(110096026)),
            # Please, remove Int(10) in production. It's here just for speedy testing
            Assert(Global.round() >= self.shuffle_round.get()),
            getRandomBits,
            # Skip 6 bytes in case of this randomness beacon. For example ARC-4 reserves 4 bytes for a type prefix.
            currBitN.store(Int(32 + 32)),
            Pop(self.permutation.create()),
            initPermutation,
            shuffleList(self.n_challenges_total, randomBits,
                        self.permutation, currBitN),
            self.status.set(Bytes("3_SOLVE_CHALLENGES")),
        )

    # An example timeout in rounds (very small for quick testing) after which, if the server did not post the question, user can call no_posted_refund. Might be increased for production.
    post_timeout = 2

    # An example price to play the game. Boxes storage cost must be carefully included in production.
    collateral = 0.2

    @ external
    def book_challenge(self, payment: abi.PaymentTransaction):
        """
        This method is the first method user calls. He is assigned the next question. Payment is taken.
        He moves up the state ladder to a state denoting that he booked the question.
        """
        # If account state is zero set default: 1_NON-BOOKED
        payment = payment.get()
        return Seq(
            Assert(self.status == Bytes("3_SOLVE_CHALLENGES")),
            Assert(self.n_challenges_unlocked.get()
                   <= Int(self.n_challenges_total)),
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

    # An example timeout in rounds; after if user did not answer, collateral is eaten. Might be increased for production.
    answer_timeout = 10

    @ external(authorize=Authorize.only(Global.creator_address()))
    def post_challenge(self, booker: abi.Address, question: Question, salt: Salt, *, output: abi.Uint16,
                       ):
        """
        This method is called by the oracle to publish the question. The question must match the
        pre-commited hash. The question id is assigned to this user address. The user state is changed to 
        allow answering the question. Finally, the index n_challenges_unlocked is increased. 
        Now, ready for the next question.
        """
        challenge_id = self.permutation[self.n_challenges_unlocked.get()]
        salted_question_hash = self.salted_question_hashes[Btoi(
            challenge_id.get())]

        unlock_challenge = Seq(
            Assert(salted_question_hash == Sha256(
                Concat(question.get(), salt.get()))),
            challenge_id.store_into(output),
            self.challenge_id_records[booker].set(challenge_id.get()),
            # Unblind the question in place of hash
            salted_question_hash.set(question),
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
        """
        Method to protect the user. If the server did not post the question. 
        Whether it was down or did it on purpose. The user just calls this method and gets his collateral back.
        Safe and sound.
        """
        post_round = self.post_round_records[Txn.sender()]
        booking_state = self.booking_state_records[Txn.sender()]
        money_back = self.pay(Txn.sender(), consts.Algos(self.collateral))

        return Seq(Assert(self.status == Bytes("3_SOLVE_CHALLENGES")),
                   Assert(booking_state.get() == Bytes("2_YES_BOOKED")),
                   Assert(Global.round() >= Btoi(post_round.get())),
                   money_back,
                   # booking_state.set(Bytes("1_NON_BOOKED"))
                   Pop(booking_state.delete()),
                   )

    reveal_timeout = 2

    @external
    def answer_challenge(self, answer: Answer):
        """
        When called just stores user answer in a box to be later compared with ground truth.
        State checks preceed. 
        """
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

    @external(authorize=Authorize.only(Global.creator_address()))
    def reveal_answer(self, booker: abi.Address, answer: Answer, salt: Salt):
        """
        This method is called by the oracle. The oracle publishes the true answer on-chain.
        The answer hash must match the initial commitment. If the player did not answer / answered wrong at the time of
        solution reveal, their collateral goes to the company wallet. If their answer matches truth,
        the play earns ALGOs.
        """
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
                Pop(booking_state.delete()),
            ).Else(Reject()),
            # Unblinding used answers
            salted_answer_hash.set(answer),
            # Instead of booking_state.set(Bytes("1_NON_BOOKED")) we just remove the state.
            Pop(booking_state.delete()),

        )

    @external
    def no_reveal_refund(self):
        """
        Method to protect the user. If the server did not reveal the true answer (pre-image of the commited hash). 
        Whether it was down or did it on purpose. The user just calls this method and gets his prize.
        Deincetivizes game company to lie. User is safe.
        """
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
                   # Instead of booking_state.set(Bytes("1_NON_BOOKED")) we just remove the state.
                   Pop(booking_state.delete()),
                   )
