#!/usr/bin/env python3
# Copyright (c) 2014-2015 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

#
# Test addressindex generation and fetching
#

import time
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import *
from test_framework.script import *
from test_framework.mininode import *
import binascii

class SpentIndexTest(BitcoinTestFramework):
    def set_test_params(self):
        self.num_nodes = 4
        self.setup_clean_chain = True
        self.extra_args = [
            ["-usehd=1"], ["-usehd=0", "-addrindex"],
            ["-usehd=1", "-addrindex"], ["-usehd=0", "-addrindex", "-txindex"]
        ]

    def setup_network(self):
        self.setup_nodes()
        connect_nodes(self.nodes[0], 1)
        connect_nodes(self.nodes[0], 2)
        connect_nodes(self.nodes[0], 3)

        self.is_network_split = False
        self.sync_all()

    def run_test(self):
        print ("Mining blocks...")
        self.nodes[0].generate(105)
        self.sync_all()

        chain_height = self.nodes[1].getblockcount()
        assert_equal(chain_height, 105)

        # Check that
        print ("Testing spent index...")

        privkey = "cSdkPxkAjA4HDr5VHgsebAPDEh9Gyub4HK8UJr2DFGGqKKy4K5sG"
        address = "mgY65WSfEmsyYaYPQaXhmXMeBhwp4EcsQW"
        addressHash = unhexlify("0b2f0a0c31bfe0406b0ccc1381fdbe311946dadc")
        scriptPubKey = CScript([OP_DUP, OP_HASH160, addressHash, OP_EQUALVERIFY, OP_CHECKSIG])
        unspent = self.nodes[0].listunspent()
        tx = CTransaction()
        amount = unspent[0]["amount"] * 10000000
        tx.vin = [CTxIn(COutPoint(int(unspent[0]["txid"], 16), unspent[0]["vout"]))]
        tx.vout = [CTxOut(int(amount), scriptPubKey)]
        tx.rehash()

        signed_tx = self.nodes[0].signrawtransaction(binascii.hexlify(tx.serialize()).decode("utf-8"))
        txid = self.nodes[0].sendrawtransaction(signed_tx["hex"], True)
        self.nodes[0].generate(1)
        self.sync_all()

        print ("Testing getspentinfo method...")

        # Check that the spentinfo works standalone
        info = self.nodes[1].getspentinfo({"txid": unspent[0]["txid"], "index": unspent[0]["vout"]})
        assert_equal(info["txid"], txid)
        assert_equal(info["index"], 0)
        assert_equal(info["height"], 106)

        print ("Testing getrawtransaction method...")

        # Check that verbose raw transaction includes spent info
        txVerbose = self.nodes[3].getrawtransaction(unspent[0]["txid"], 1)
        assert_equal(txVerbose["vout"][unspent[0]["vout"]]["spentTxId"], txid)
        assert_equal(txVerbose["vout"][unspent[0]["vout"]]["spentIndex"], 0)
        assert_equal(txVerbose["vout"][unspent[0]["vout"]]["spentHeight"], 106)

        # Check that verbose raw transaction includes input values
        txVerbose2 = self.nodes[3].getrawtransaction(txid, 1)
        assert_equal(txVerbose2["vin"][0]["value"], Decimal(unspent[0]["amount"]))

        # Check that verbose raw transaction includes address values and input values
        privkey2 = "cSdkPxkAjA4HDr5VHgsebAPDEh9Gyub4HK8UJr2DFGGqKKy4K5sG"
        address2 = "mgY65WSfEmsyYaYPQaXhmXMeBhwp4EcsQW"
        addressHash2 = unhexlify("0b2f0a0c31bfe0406b0ccc1381fdbe311946dadc")
        scriptPubKey2 = CScript([OP_DUP, OP_HASH160, addressHash2, OP_EQUALVERIFY, OP_CHECKSIG])
        tx2 = CTransaction()
        tx2.vin = [CTxIn(COutPoint(int(txid, 16), 0))]
        tx2.vout = [CTxOut(int(amount/10), scriptPubKey2)]
        tx.rehash()
        self.nodes[0].importprivkey(privkey)
        signed_tx2 = self.nodes[0].signrawtransaction(binascii.hexlify(tx2.serialize()).decode("utf-8"))
        txid2 = self.nodes[0].sendrawtransaction(signed_tx2["hex"], True)

        # Check the mempool index
        self.sync_all()
        txVerbose3 = self.nodes[1].getrawtransaction(txid2, 1)
        assert_equal(txVerbose3["vin"][0]["address"], address2)
        assert_equal(txVerbose3["vin"][0]["value"], (Decimal(unspent[0]["amount"])/10))
        assert_equal(txVerbose3["vin"][0]["valueSat"], amount)

        # Check the database index
        block_hash = self.nodes[0].generate(1)
        self.sync_all()

        txVerbose4 = self.nodes[3].getrawtransaction(txid2, 1)
        assert_equal(txVerbose4["vin"][0]["address"], address2)
        assert_equal(txVerbose4["vin"][0]["value"], (Decimal(unspent[0]["amount"])/10))
        assert_equal(txVerbose4["vin"][0]["valueSat"], amount)

        print ("Passed\n")


if __name__ == '__main__':
    SpentIndexTest().main()
