# 💍 Promise 

Safely blockchainify any puzzle game with Algorand.

See video demo of [a game protected by Promise](https://youtu.be/AinSxP7sn90).
## Original technology

The protocol combines two new technologies. A paired-content-escrow. A random-sneak-peek. Both were researched for this project.

## Community contribution
An unbiased PyTeal randomness library for all.

A lot of lotteries on Algorand and other blockchains are biased. Modulo remainder arithmetics is often used to determine the winner.
This is mathematically incorrect. A [famous example of modulo bias](https://www.linkedin.com/pulse/why-firelottos-blockchain-based-random-engine-fair-kostas-chalkias/) is Firelotto.

We present [a PyTeal library for safe and unbiased random](https://github.com/arty-arty/promise/blob/master/lib_algo_random.py) lib_algo_random.py 

Though Promise needs unbiased random, this project is not a lottery at all. 
Promise is a mathematical protocol to solve cheating in games once and for all. Plus a multidtude of other benefits.
Read more to understand.

## A mathematical protocol 

There are games to tell stories. There are games to solve mysteries. If there is only one way to solve a level - only one answer - then Promise works.

Any such game old or new can, actually, be run on-chain. 
It can be placing mirrors to guide the laser through the labirynth. It can be finding one concept which unites four pictures. It can be guessing which brand is on the logo. We present a general solution to rule them all.

## A must
Why should we blockchainify games at all? What does it even mean?

Something never possible before blockchain happens. Let's see what Promise brings in.

**Auto payout on win**
> Before chains:
>  Games often just change the rules in the middle. Out of nowhere, they could drastically cut the payout. There's a [whole list of P2E scams](https://cointelegraph.com/news/scams-in-gamefi-how-to-identify-toxic-nft-gaming-projects) that could be easily avoided by using Promise. 
>  
>
> After:
> There is an algorithmic commitment. Promise escrows the money. There is no other way. Users are always auto-payed for the right answer. If the project is protected by Promise, it can be trusted.

That's why with Promise you get what you are Promised. It not only offers protection for the user. 
Unlike many client-side P2E games, Promise protected games are immune to all sorts of client-side memory hacks.

**Auto money back on non-delivery** 
> Before chains:
> There are a lot of complaints on Google Play. Paid features are often not working.
>
> After:
> Promise auto-returns escrowed money, if the level was not delivered to the user. There is no other way around. 

**Auto content quality check**
> Before chains:
> The game has inconsistent quality levels. Or examples fall far from actual gameplay. Like in those misleading Candy Crush clone ads. Seems like the devlopers just do not care. 
> Players are disappointed when their expectations meet ugly gameplay in reality.
>
> After:
> Promise shuffles the levels using Algorand's Verifiable Random Functions. Before payment, every user gets a fair sneak peek of the random levels. 
> Statistically the user gets the same high-quality for paid levels.

Soon, neural networks are going to disrupt the gaming industry. Imagine, auto-generated content tailored for your personality. There has to be a way to safely sell and buy such personal content. Unfortunately there is no guarantee. For example, some apps dumb down generation from GPT-3 to GPT-2 to save costs.
 

Actually there is a way to ensure quality, without losing funds. It is Promise. In particular its random sneak pick feature.

## A content-pair escrow
<!-- Click the link to see a demo game protected by Promise.

From a technical point of view Promise is a gaming escrow. First, it guarantees payout/decincentivizes any fraud. Second, it makes sure 
the content quality is the same as Promised by examples. How can a machine feel the quality? Actually, it can't. But, the user might get a fair sneak peek to decide.
Promise provides random examples of levels before the user pays. The levels are randomly shuffled. So, if the user loved those examples, most likely 
paid ones will be enjoyable as well. 

Which seems important in the age of neural net autogenerated content. Imagine that each person 
receives his own personal generated level. There has to be a way to safely sell and buy personal levels. This way is Promise. -->

One half of Promise is an escrow with hashed challenge-response pairs. It deincentivizes lying and non-participation for game company and player, guarantees payouts for right answers. This is not a regular escrow, but has a very particular player / game interaction scheme:

1. The player [books a question](https://github.com/arty-arty/promise/blob/fe3d97e3c8fc8835e5f59b93a5c108b96d82adbd/contract/contract.py#L242).
2. The oracle has to [reveal question's plain text](https://github.com/arty-arty/promise/blob/fe3d97e3c8fc8835e5f59b93a5c108b96d82adbd/contract/contract.py#L267). It has to match the question hash. The plain text can be a link to ipfs with a picture or a whole level folder.
3. If the [oracle does not respond](https://github.com/arty-arty/promise/blob/fe3d97e3c8fc8835e5f59b93a5c108b96d82adbd/contract/contract.py#L293) in time, player is eligible to call a money-back method.
4. The player sees the question and has to [answer](https://github.com/arty-arty/promise/blob/fe3d97e3c8fc8835e5f59b93a5c108b96d82adbd/contract/contract.py#L307) before timeout. Otherwise [oracle can take his payment](https://github.com/arty-arty/promise/blob/fe3d97e3c8fc8835e5f59b93a5c108b96d82adbd/contract/contract.py#L355).
5. The oracle has to reveal the true (matching the hash) answer before timeout. Notice that it's salted, so no problems with brutefircing small answer set. Otherwise the [player receives a compensation](https://github.com/arty-arty/promise/blob/fe3d97e3c8fc8835e5f59b93a5c108b96d82adbd/contract/contract.py#L361).
6. If [player's answer matched](https://github.com/arty-arty/promise/blob/fe3d97e3c8fc8835e5f59b93a5c108b96d82adbd/contract/contract.py#L350) the oracle answer then he receives a prize. Otherwise oracle just takes his payment. 
7. This question-pair now remains open to everyone. It was a random one, so represents the overall quality of the game. With each play the reputation of the game grows.

This fair scheme is enforced via a state machine implemented in the contract:

```python
# Global state of the contract
# Might be 
Bytes("1_ADD_CHALLENGES")
Bytes("2_RESOLVE_PRNG_SHUFFLE")
Bytes("3_SOLVE_CHALLENGES")

# Each method validates the state before execution
# Like this
Assert(self.status == Bytes("1_ADD_CHALLENGES"))
```

Individual state of each user matters. It allows to avoid a queue and gracefully serve each person:

```python
# Individual state of each user 
# Saved in a box to avoid local storage opt-in
# Might be 
Bytes("1_NON_BOOKED")
Bytes("2_YES_BOOKED")
Bytes("3_YES_POSTED")
Bytes("4_YES_ANSWED")

# Each external method validates and switches the state
# According to paired-content-escrow and random-sneak-peek logic
```

## A random-sneak-peek

The only seeming caveat after this step: what if levels are bad/dumb/fake? What if pre-loaded question-answer pairs are boring or factually incorrect? 

If the question was "Who invented the light bulb?", the malicious answer could be "hahagametrickedyouandtooksomemoney". The other half of Promise got you covered.

Let's say there are 100 question-answer pairs. They are pre-commited. Then after shuffling fairly with VRF, we might reveal a quater of them. Let's call them examples. If the user likes them. Then, statistically, paid levels are likely to be same high-quality.

Algorithmically speaking:
1. A set of N question-answer [pair hashes are pre-loaded](https://github.com/arty-arty/promise/blob/fe3d97e3c8fc8835e5f59b93a5c108b96d82adbd/contract/contract.py#L109) into the contract.
2. The [state is changed](https://github.com/arty-arty/promise/blob/fe3d97e3c8fc8835e5f59b93a5c108b96d82adbd/contract/contract.py#L121), so no new questions can be added. Plus, a future [round of random beacon resolution](https://github.com/arty-arty/promise/blob/fe3d97e3c8fc8835e5f59b93a5c108b96d82adbd/contract/contract.py#L125) is set. 
3. [Knuth-Yao](https://github.com/arty-arty/promise/blob/fe3d97e3c8fc8835e5f59b93a5c108b96d82adbd/contract/contract.py#L138) array shuffle, utilising random bits from VFR proof, is used to [permute an array](https://github.com/arty-arty/promise/blob/fe3d97e3c8fc8835e5f59b93a5c108b96d82adbd/contract/contract.py#L207) of $[1, 2, .., N]$. Let's call this permutation $\phi[i]$
4. The [state is changed](https://github.com/arty-arty/promise/blob/fe3d97e3c8fc8835e5f59b93a5c108b96d82adbd/contract/contract.py#L232) to allow players book challenges. Each next player books $\phi[i + 1]$ question. Which means questions are randomly shuffled. The contract is ready to serve users.


<!-- ## A revolutionary experience

Here is a synopsis for players.

Promise is a revolutionary new way to play games and get rewarded for being right. With Promise, you can be sure that your answers will be judged fairly and without bias, and that you will get rewarded for being correct. It also ensures that the levels provided by game companies are of high quality and entertaining. With Promise, you can trust that your gaming experience will be fun and fair. 
You can now play games with confidence, knowing that you will be rewarded for your hard work. Play today and start winning with Promise!

## A synopsis for developers

Here is a synopsis for developers.
To summarize, the contract in this repository is universal. 
You can use it to create a platform for any game that requires solving challenges. The contract's code is designed for easy deployment, and it can be easily connected to your project. 

The contract provides a fair environment for both game companies and players, ensuring both parties get paid for correct answers. It also encourages honest participation with its hashed challenge-response pairs and money-back method. And the random-sneak-peek feature ensures that the levels are of high quality.
It allows to implement any type of game as a series of question-answer pairs, shuffled randomly with VFR, and enforced by the contract. 

The contract also provides a set of methods for users to book and answer questions, as well as the game company to post questions and rewards. 

The contract also provides a set of methods for users to verify the integrity of questions, such as the random-sneak-peek, which allows players to see a small sample of questions before investing time and money. 

If you're interested in using Promise, we invite you to take a look at the source code and consider whether it may be suitable for your game.
It allows to build a game with the following features:

1. Hashed challenge-response pairs to deincentivize lying and non-participation for game company and player.
2. Money-back guarantee for player in case of oracle's failure.
3. Random sneak peek to provide an insight into what is going to be paid prior to payment. 
4. Fairness in the queue system, so each person can have his own chance without waiting in a queue.
5. Reputation system based on the number of solved challenges. 

To use it, you should:
1. Preload your questions into the contract (see `preload_questions` method). It is possible to upload questions one after another, but it is more efficient to preload a couple at once. It is important that you get the initial set of questions right because it will be used for random sneak peek;
2. Set up number of challenges you want to reveal as examples; 
3. Start the contract and start playing! -->
