import os
import sys
from decimal import Decimal

from dotenv import load_dotenv
from web3 import Web3
from moltbook_client import post_to_moltbook, PROJECT_TITLE, PROJECT_BODY

load_dotenv()

ALCHEMY_SEPOLIA_URL = os.getenv("ALCHEMY_SEPOLIA_URL")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
USDC_CONTRACT_ADDRESS = os.getenv("USDC_CONTRACT_ADDRESS")
EURC_CONTRACT_ADDRESS = os.getenv("EURC_CONTRACT_ADDRESS")

USDC_DECIMALS = 6
EURC_DECIMALS = 6  # EURC on Ethereum Sepolia also uses 6 decimal places

# Chain ID for Ethereum Sepolia
SEPOLIA_CHAIN_ID = 11155111

w3 = Web3(Web3.HTTPProvider(ALCHEMY_SEPOLIA_URL))


def require_connection():
    if not w3.is_connected():
        raise RuntimeError("Not connected to Sepolia – check ALCHEMY_SEPOLIA_URL")


def checksum(address: str) -> str:
    if not Web3.is_address(address):
        raise ValueError(f"Invalid address: {address}")
    return Web3.to_checksum_address(address)


def get_eth_balance(address: str) -> Decimal:
    require_connection()
    addr = checksum(address)
    balance_wei = w3.eth.get_balance(addr)
    return Decimal(w3.from_wei(balance_wei, "ether"))


def erc20_abi():
    # Minimal ABI for balanceOf, transfer, decimals, symbol – shared between USDC and EURC
    return [
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function",
        },
        {
            "constant": False,
            "inputs": [
                {"name": "_to", "type": "address"},
                {"name": "_value", "type": "uint256"},
            ],
            "name": "transfer",
            "outputs": [{"name": "success", "type": "bool"}],
            "type": "function",
        },
        {
            "constant": True,
            "inputs": [],
            "name": "decimals",
            "outputs": [{"name": "", "type": "uint8"}],
            "type": "function",
        },
        {
            "constant": True,
            "inputs": [],
            "name": "symbol",
            "outputs": [{"name": "", "type": "string"}],
            "type": "function",
        },
    ]


def get_erc20_contract(contract_address: str):
    require_connection()
    addr = checksum(contract_address)
    return w3.eth.contract(address=addr, abi=erc20_abi())


def get_usdc_balance(address: str) -> Decimal:
    require_connection()
    if not USDC_CONTRACT_ADDRESS:
        raise RuntimeError("Missing USDC_CONTRACT_ADDRESS in .env")
    contract = get_erc20_contract(USDC_CONTRACT_ADDRESS)
    addr = checksum(address)
    raw = contract.functions.balanceOf(addr).call()
    return Decimal(raw) / (10 ** USDC_DECIMALS)


def get_eurc_balance(address: str) -> Decimal:
    require_connection()
    if not EURC_CONTRACT_ADDRESS:
        raise RuntimeError("Missing EURC_CONTRACT_ADDRESS in .env")
    contract = get_erc20_contract(EURC_CONTRACT_ADDRESS)
    addr = checksum(address)
    raw = contract.functions.balanceOf(addr).call()
    return Decimal(raw) / (10 ** EURC_DECIMALS)


def print_status():
    require_connection()
    latest_block = w3.eth.block_number
    block = w3.eth.get_block(latest_block)
    print("Connected to Sepolia")
    print("Latest block:", latest_block)
    print("Block hash:", block.hash.hex())
    print("Number of transactions in block:", len(block.transactions))

    if WALLET_ADDRESS:
        eth_bal = get_eth_balance(WALLET_ADDRESS)
        print(f"ETH balance for {WALLET_ADDRESS}: {eth_bal} ETH")
        try:
            usdc_bal = get_usdc_balance(WALLET_ADDRESS)
            print(f"USDC balance for {WALLET_ADDRESS}: {usdc_bal} USDC")
        except Exception as e:
            print(f"Failed to fetch USDC balance: {e}")
        try:
            eurc_bal = get_eurc_balance(WALLET_ADDRESS)
            print(f"EURC balance for {WALLET_ADDRESS}: {eurc_bal} EURC")
        except Exception as e:
            print(f"Failed to fetch EURC balance: {e}")
    else:
        print("Missing WALLET_ADDRESS in .env")


def build_and_send_erc20_transfer(
    token_symbol: str,
    contract_address: str,
    decimals: int,
    to_address: str,
    amount: Decimal,
) -> str:
    require_connection()

    if not PRIVATE_KEY:
        raise RuntimeError("Missing PRIVATE_KEY in .env (kept only locally).")

    from_addr = checksum(WALLET_ADDRESS)
    to_addr = checksum(to_address)

    contract = get_erc20_contract(contract_address)

    raw_amount = int(Decimal(amount) * (10 ** decimals))

    nonce = w3.eth.get_transaction_count(from_addr)

    tx = contract.functions.transfer(to_addr, raw_amount).build_transaction(
        {
            "from": from_addr,
            "nonce": nonce,
            "gas": 150000,
            "maxFeePerGas": w3.to_wei("5", "gwei"),
            "maxPriorityFeePerGas": w3.to_wei("2", "gwei"),
            "chainId": SEPOLIA_CHAIN_ID,
        }
    )

    signed = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"{token_symbol} transfer sent, tx hash: {tx_hash.hex()}")
    return tx_hash.hex()


def send_usdc(to_address: str, amount: Decimal) -> str:
    if not USDC_CONTRACT_ADDRESS:
        raise RuntimeError("Missing USDC_CONTRACT_ADDRESS in .env")
    return build_and_send_erc20_transfer(
        "USDC", USDC_CONTRACT_ADDRESS, USDC_DECIMALS, to_address, amount
    )


def send_eurc(to_address: str, amount: Decimal) -> str:
    if not EURC_CONTRACT_ADDRESS:
        raise RuntimeError("Missing EURC_CONTRACT_ADDRESS in .env")
    return build_and_send_erc20_transfer(
        "EURC", EURC_CONTRACT_ADDRESS, EURC_DECIMALS, to_address, amount
    )


def send_eth(to_address: str, amount_eth: Decimal) -> str:
    """
    Sends native ETH from WALLET_ADDRESS to to_address.
    amount_eth is specified in ETH, e.g. 0.01.
    """
    require_connection()

    if not PRIVATE_KEY:
        raise RuntimeError("Missing PRIVATE_KEY in .env (kept only locally).")

    from_addr = checksum(WALLET_ADDRESS)
    to_addr = checksum(to_address)

    value_wei = w3.to_wei(amount_eth, "ether")

    nonce = w3.eth.get_transaction_count(from_addr)

    tx = {
        "from": from_addr,
        "to": to_addr,
        "value": value_wei,
        "nonce": nonce,
        "gas": 21000,
        "maxFeePerGas": w3.to_wei("5", "gwei"),
        "maxPriorityFeePerGas": w3.to_wei("2", "gwei"),
        "chainId": SEPOLIA_CHAIN_ID,
    }

    signed = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"ETH transfer sent, tx hash: {tx_hash.hex()}")
    return tx_hash.hex()


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python main.py status")
        print("  python main.py balance")
        print("  python main.py send-eth <TO_ADDRESS> <AMOUNT_ETH>")
        print("  python main.py send-usdc <TO_ADDRESS> <AMOUNT_USDC>")
        print("  python main.py send-eurc <TO_ADDRESS> <AMOUNT_EURC>")
        print("  python main.py post-moltbook")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "status":
        print_status()

    elif cmd == "balance":
        if not WALLET_ADDRESS:
            print("Missing WALLET_ADDRESS in .env")
            sys.exit(1)
        eth_bal = get_eth_balance(WALLET_ADDRESS)
        print(f"ETH balance: {eth_bal} ETH")
        try:
            usdc_bal = get_usdc_balance(WALLET_ADDRESS)
            print(f"USDC balance: {usdc_bal} USDC")
        except Exception as e:
            print(f"Failed to fetch USDC balance: {e}")
        try:
            eurc_bal = get_eurc_balance(WALLET_ADDRESS)
            print(f"EURC balance: {eurc_bal} EURC")
        except Exception as e:
            print(f"Failed to fetch EURC balance: {e}")

    elif cmd == "send-eth":
        if len(sys.argv) != 4:
            print("Usage: python main.py send-eth <TO_ADDRESS> <AMOUNT_ETH>")
            sys.exit(1)
        to_addr = sys.argv[2]
        amount_str = sys.argv[3]
        try:
            amount = Decimal(amount_str)
        except Exception:
            print("AMOUNT_ETH must be a number (e.g. 0.01)")
            sys.exit(1)
        tx_hash = send_eth(to_addr, amount)
        print("Check the transaction on Sepolia Etherscan using this hash.")

    elif cmd == "send-usdc":
        if len(sys.argv) != 4:
            print("Usage: python main.py send-usdc <TO_ADDRESS> <AMOUNT_USDC>")
            sys.exit(1)
        to_addr = sys.argv[2]
        amount_str = sys.argv[3]
        try:
            amount = Decimal(amount_str)
        except Exception:
            print("AMOUNT_USDC must be a number (e.g. 1 or 0.5)")
            sys.exit(1)
        tx_hash = send_usdc(to_addr, amount)
        print("Check the transaction on Sepolia Etherscan using this hash.")

    elif cmd == "send-eurc":
        if len(sys.argv) != 4:
            print("Usage: python main.py send-eurc <TO_ADDRESS> <AMOUNT_EURC>")
            sys.exit(1)
        to_addr = sys.argv[2]
        amount_str = sys.argv[3]
        try:
            amount = Decimal(amount_str)
        except Exception:
            print("AMOUNT_EURC must be a number (e.g. 1 or 0.5)")
            sys.exit(1)
        tx_hash = send_eurc(to_addr, amount)
        print("Check the transaction on Sepolia Etherscan using this hash.")

    elif cmd == "post-moltbook":
        try:
            resp = post_to_moltbook("usdc", PROJECT_TITLE, PROJECT_BODY)
            print("Posted to Moltbook m/usdc.")
            print("Response:", resp)
        except Exception as e:
            print("Failed to post to Moltbook:", e)

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
