from contract.contract import PromiseYou
from algosdk.encoding import encode_address
from beaker import *
import array


def getQuestion(n_challenge, permutation_array, questions):
    """Select a particular question from an array taken into account that they were shuffled by permutation."""
    permuted_index = permutation_array[n_challenge]
    question = questions[permuted_index]
    return question


def getPermuatation(permutation):
    """Decode Uint16 numbers from permutation list. Notice byteswap for big endian."""
    permutation_arr = array.array('H', permutation)
    permutation_arr.byteswap()
    return list(permutation_arr)


def fetchPersonalStates(app_client):
    """Fetch boxes with state data for all contract participants - question bookers"""
    boxes_names = app_client.get_box_names()
    personal_state_holders = [
        name for name in boxes_names if name.startswith(b"STATE")]
    personal_state_values = [app_client.get_box_contents(
        state) for state in personal_state_holders]
    return dict(zip(personal_state_holders, personal_state_values))


def processPersonStates(app_client, personal_states, questions,  current_n_question, permutation_array):
    """Process each person state in a loop. Send needed transaction. See more info in processPersonState function docs."""
    for person_state in personal_states.items():
        processPersonState(app_client, person_state, questions,
                           current_n_question, permutation_array)


def processPersonState(app_client, person_state, questions,  current_n_question, permutation_array):
    """Process person state. If the player booked a question post it. If the person did not answer in time 
    collect the payment. If she answered validate her answer by submiting the ground truth into the contract."""
    personal_state_holder, personal_state_value = person_state
    print(personal_state_value)
    if (personal_state_value == b'2_YES_BOOKED'):
        postChallenge(app_client, personal_state_holder,
                      current_n_question, permutation_array, questions)

    if (personal_state_value == b'3_YES_POSTED'):
        # Trying to get the collateral, if the user did not respond in time.
        # Notice that the same method revealAnswer collects the collateral in the smart contract and reveals the true answer at the same time
        try:
            revealAnswer(app_client, personal_state_holder, questions)
        except Exception as inst:
            print("Person still has time to answer", inst)

    if (personal_state_value == b'4_YES_ANSWED'):
        revealAnswer(app_client, personal_state_holder, questions)


def revealAnswer(app_client, personal_state_holder, questions):
    """Find which challenge was booked by the user. Retreive from DB the answer to this challenge. 
    Submit it into the contract. Please notice that the contract will validate it against the hash.
    It means that the oracle can not cheat too. It can only reveal the true answer."""
    personal_state_holder = personal_state_holder.replace(
        b'STATE', b'')
    str_address = encode_address(
        personal_state_holder)

    # Get which question number n was assigned to this user
    n_for_user = app_client.get_box_contents(b'ID' + personal_state_holder)
    n_for_user = getPermuatation(n_for_user)[0]

    print("N for user: ", n_for_user)

    # Retrieve the right challenge for this user
    question = questions[n_for_user]

    # Submit the salt and answer into the contract
    # Notice that the salt protects against client-side bruteforcing, if possible answers set is small
    app_client.call(PromiseYou.reveal_answer, booker=str_address,
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


def postChallenge(app_client, personal_state_holder, current_n_question, permutation_array, questions):
    """Find which question ID the user needs. Fetch the question from DB nad post it in smart contract.
    Notice that the oracle can not change its commitment. A salted_hash protects the question. 
    Protections are implemented inside of the smart contract. It acts as a safe and trusted intermediary between player and game company. 
    Forbids each side to cheat.
     """
    personal_state_holder = personal_state_holder.replace(
        b'STATE', b'')
    str_address = encode_address(
        personal_state_holder)
    print("Holder: ", personal_state_holder, str_address, current_n_question)
    question = getQuestion(
        current_n_question, permutation_array, questions)
    app_client.call(PromiseYou.post_challenge, booker=encode_address(
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
