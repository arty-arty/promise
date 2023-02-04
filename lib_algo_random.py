# This is a useful PyTeal library to shuffle arrays, or have Uniform[0, n] random.
# The mathematical benefit - it has no modulo bias. Completely.
# No bias was achieved by using an optimized version of rejection sampling.
# Inspired by publication (https://dl.acm.org/doi/10.1145/3009909) with algorithm analysis and more insights.

# The library was developed during the hackathon for the open-source community of Algorand


from pyteal import *
from beaker import *
from beaker.lib.storage import List


@internal(TealType.uint64)
def KnuthYao(n, randomBits, currBitN: ScratchVar):
    # Outputs a random number Uniform[0, n-1]
    # Wtihout modulo bias
    # Inspired by publication (https://dl.acm.org/doi/10.1145/3009909)

    u = ScratchVar(TealType.uint64)
    x = ScratchVar(TealType.uint64)
    d = ScratchVar(TealType.uint64)
    result = ScratchVar(TealType.uint64)

    return Seq(
        u.store(Int(1)),
        x.store(Int(0)),
        result.store(Int(0)),
        While(Int(1)).Do(Seq(
            While(u.load() < n).Do(
                Seq(
                    u.store(Int(2)*u.load()),
                    x.store(Int(2)*x.load() +
                            GetBit(randomBits, currBitN.load())),
                    currBitN.store(currBitN.load() + Int(1))
                )
            ),
            d.store(u.load() - n),
            If(x.load() >= d.load()).Then(
                Seq(result.store(x.load() - d.load()), Break())).Else(
                u.store(d.load())
            )
        )
        ),
        result.load(),
    )


@internal(TealType.none)
def shuffleList(n_challenges_total: int, randomBits: ScratchVar, permutation: List, currBitN: ScratchVar):
    # An optimized random shuffling of a list. By pairwise permutations.
    # The algorithm relies on an unbiased implementation of Uniform random from our library
    # So, it is has no modulo bias too.

    i = ScratchVar(TealType.uint64)
    j = ScratchVar(TealType.uint64)
    shufflePermutation = For(i.store(Int(n_challenges_total)), i.load() >= Int(2), i.store(i.load() - Int(1))).Do(
        Seq(
            j.store(Int(1) + KnuthYao(i.load(),
                    randomBits.load(), currBitN)),
            permutation[i.load() - Int(1)
                        ].store_into(temp_i := abi.Uint16()),
            permutation[j.load() -
                        Int(1)].store_into(temp_j := abi.Uint16()),
            permutation[i.load() - Int(1)
                        ].set(temp_j),
            permutation[j.load() - Int(1)].set(temp_i),
        )
    )
    return shufflePermutation
