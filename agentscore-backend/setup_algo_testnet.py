"""
Algorand Testnet Setup Script for AgentScore Demo
=================================================
This script:
1. Creates escrow + demo bot wallets
2. Attempts to fund via testnet dispenser
3. Makes a real on-chain payment producing a verifiable txn hash
4. Prints all info for .env configuration

Run: python setup_algo_testnet.py
"""
from __future__ import annotations

import json
import sys
import time

import httpx
from algosdk import account, mnemonic, transaction
from algosdk.v2client import algod

ALGOD_ADDRESS = "https://testnet-api.algonode.cloud"
ALGOD_TOKEN = ""

def get_client() -> algod.AlgodClient:
    return algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS)


def create_wallet(label: str) -> dict:
    pk, addr = account.generate_account()
    mn = mnemonic.from_private_key(pk)
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  Address:  {addr}")
    print(f"  Mnemonic: {mn}")
    return {"address": addr, "private_key": pk, "mnemonic": mn}


def check_balance(address: str) -> float:
    try:
        client = get_client()
        info = client.account_info(address)
        amt = info.get("amount", 0) / 1_000_000
        print(f"  Balance:  {amt:.6f} ALGO")
        return amt
    except Exception as e:
        print(f"  Balance check error: {e}")
        return 0.0


def fund_from_dispenser(address: str) -> bool:
    """Try multiple testnet faucet endpoints."""
    endpoints = [
        ("POST", "https://dispenser.testnet.aws.algodev.network/fund",
         {"receiver": address, "amount": 10_000_000}),
    ]
    for method, url, payload in endpoints:
        try:
            if method == "POST":
                r = httpx.post(url, json=payload, follow_redirects=True, timeout=15)
            else:
                r = httpx.get(url, follow_redirects=True, timeout=15)
            if r.status_code == 200 and "tx" in r.text.lower():
                print(f"  ✅ Funded via {url}")
                return True
        except Exception:
            pass
    print(f"  ⚠️  Auto-fund failed. Please fund manually:")
    print(f"     https://dispenser.testnet.aws.algodev.network/")
    print(f"     Address: {address}")
    return False


def make_payment(sender_pk: str, sender_addr: str, receiver_addr: str,
                 amount_micro: int, note: str) -> str | None:
    """Make a real Algorand testnet payment and return txn ID."""
    try:
        client = get_client()
        params = client.suggested_params()

        txn = transaction.PaymentTxn(
            sender=sender_addr,
            sp=params,
            receiver=receiver_addr,
            amt=amount_micro,
            note=note.encode(),
        )

        signed = txn.sign(sender_pk)
        txn_id = client.send_transaction(signed)
        print(f"  📤 Submitted txn: {txn_id}")

        # Wait for confirmation
        result = transaction.wait_for_confirmation(client, txn_id, 4)
        confirmed_round = result.get("confirmed-round", "?")
        print(f"  ✅ Confirmed in round {confirmed_round}")
        print(f"  🔗 Explorer: https://testnet.explorer.perawallet.app/tx/{txn_id}")
        return txn_id
    except Exception as e:
        print(f"  ❌ Payment error: {e}")
        return None


def main():
    print("\n" + "🔷" * 30)
    print("  AgentScore — Algorand Testnet Setup")
    print("🔷" * 30)

    # Create wallets
    escrow = create_wallet("ESCROW WALLET (AgentScore Platform)")
    demo_user = create_wallet("DEMO USER WALLET (Telegram Bot User)")

    print("\n\n📊 Checking initial balances...")
    escrow_bal = check_balance(escrow["address"])
    user_bal = check_balance(demo_user["address"])

    if escrow_bal < 1 or user_bal < 1:
        print("\n\n💰 Wallets need funding!")
        print("Please visit: https://dispenser.testnet.aws.algodev.network/")
        print(f"\nFund ESCROW:    {escrow['address']}")
        print(f"Fund DEMO USER: {demo_user['address']}")
        print("\nPaste these addresses one at a time into the dispenser.")
        print("The dispenser gives 10 ALGO per request.")
        print("\nAfter funding, run this script again to make a test payment.")

    # Print .env config
    print("\n\n" + "=" * 60)
    print("  .env Configuration")
    print("=" * 60)
    print(f"ESCROW_WALLET_ADDRESS={escrow['address']}")
    print(f"ESCROW_WALLET_MNEMONIC={escrow['mnemonic']}")
    print(f"DEMO_USER_ADDRESS={demo_user['address']}")
    print(f"DEMO_USER_MNEMONIC={demo_user['mnemonic']}")
    print(f"ALGOD_ADDRESS=https://testnet-api.algonode.cloud")
    print(f"ALGOD_TOKEN=")

    if escrow_bal >= 0.2 and user_bal >= 0.2:
        print("\n\n🚀 Both wallets funded! Making demo payment...")
        note = json.dumps({
            "service": "agentscore_demo",
            "order_id": "DEMO-001",
            "platform": "amazon",
            "user_id": 5996685319,
        })
        txn_id = make_payment(
            demo_user["private_key"],
            demo_user["address"],
            escrow["address"],
            100_000,  # 0.1 ALGO
            note,
        )
        if txn_id:
            print(f"\n✅ DEMO PAYMENT SUCCESSFUL!")
            print(f"   Txn Hash: {txn_id}")
            print(f"   Amount: 0.1 ALGO")
            print(f"   Explorer: https://testnet.explorer.perawallet.app/tx/{txn_id}")


if __name__ == "__main__":
    main()
