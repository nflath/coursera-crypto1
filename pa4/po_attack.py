#!/usr/bin/python

import requests
import multiprocessing.dummy
import sys

import operator

from itertools import islice
from itertools import repeat
from itertools import chain

from binascii import hexlify
from binascii import unhexlify

def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)

#--------------------------------------------------------------
# padding oracle
#--------------------------------------------------------------
class PaddingOracle(object):
    block_size = 16
    hex_block_size = 2*block_size

    def __init__(self, targetURL, ct):
        self._targetURL = targetURL

        self._ct = ct

        self._numPTBlocks = int(len(self._ct)/self.block_size) - 1
        self._ptGuesses = [bytearray(self.block_size) for i in range(self._numPTBlocks)]


    def attack(self):
        #poolSZ = 64
        #pool = multiprocessing.Pool(poolSZ)

        try:
            for block in range(self._numPTBlocks):
                self._attack_block(block)
        except Exception as e:
            print("ERROR: {}".format(e))

        return b''.join(self._ptGuesses)

    def _attack_block(self, block):
        poolSZ = 256
        pool = multiprocessing.dummy.Pool(poolSZ)

        for blockPos in reversed(range(self.block_size)):
            print("Guessing [{}][{}]".format(block, blockPos))

            res = map(self.query,
                    ((islice(self._ct, block*self.block_size),
                     self._guess_block(block, blockPos, g),
                     islice(self._ct, (block+1)*self.block_size, (block+2)*self.block_size))
                    for g in range(256)))

            res = list(res)
            value = next(v for v,correct in enumerate(res) if correct)
            assert(value is not None)

            print("Correctly guessed [{}][{}] = {}".format(block, blockPos, value))
            self._ptGuesses[block][blockPos] = value

    def _guess_block(self, block, blockPos, value):
        padLen = self.block_size - blockPos
        ctPos = block*self.block_size

        guessBlock = self._ptGuesses[block][:]
        guessBlock[blockPos:] = map(operator.xor, islice(guessBlock, blockPos, None), repeat(padLen))
        guessBlock[blockPos] = guessBlock[blockPos] ^ value
        guessBlock[:] = map(operator.xor, islice(guessBlock, None), islice(self._ct, ctPos, ctPos + self.block_size))

        return guessBlock


    def query(self, parts):
        queryHex = hexlify(bytes(chain.from_iterable(parts)))
        target = self._targetURL + queryHex.decode("ascii")

        req = requests.get(target)
        assert(req.status_code in (403,404))
        return req.status_code == 404

def self_test():
    targetURL = 'http://crypto-class.appspot.com/po?er='

    target = "f20bdba6ff29eed7b046d1df9fb7000058b1ffb4210a580f748b4ac714c001bd4a61044426fb515dad3f21f18aa577c0bdf302936266926ff37dbf7035d5eeb4"

    po = PaddingOracle(targetURL, unhexlify(target))
    pt = po.attack()

    print("Plain Text")
    print(pt.decode("ascii"))

    print("Plain Text Hex")
    print(hexlify(pt))


if __name__ == "__main__":
    self_test()
