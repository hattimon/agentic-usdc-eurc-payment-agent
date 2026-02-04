import os
import sys
from decimal import Decimal

from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

ALCHEMY_SEPOLIA_URL = os.getenv("ALCHEMY_SEPOLIA_URL")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
USDC_CONTRACT_ADDRESS = os.getenv("USDC_CONTRACT_ADDRESS")
EURC_CONTRACT_ADDRESS = os.getenv("EURC_CONTRACT_ADDRESS")

USDC_DECIMALS = 6
EURC_DECIMALS = 6  # EURC na Ethereum Sepolia ma 6 miejsc po przecinku[web:72][web:74]

# Chain ID dla Ethereum Sepolia[web:103][web:104][web:110]
SEPOLIA_CHAIN_ID = 11155111

w3 = Web3(Web3.HTTPProvider(ALCHEMY_SEPOLIA_URL))


def require_connection():
    if not w3.is_connected():
        raise RuntimeError("Brak połączenia z Sepolia – sprawdź ALCHEMY_SEPOLIA_URL")


def checksum(address: str) -> str:
    if not Web3.is_address(address):
        raise ValueError(f"Niepoprawny adres: {address}")
    return Web3.to_checksum_address(address)


def get_eth_balance(address: str) -> Decimal:
    require_connection()
    addr = checksum(address)
    balance_wei = w3.eth.get_balance(addr)
    return Decimal(w3.from_wei(balance_wei, "ether"))


def erc20_abi():
    # Minimalne ABI do balanceOf, transfer, decimals, symbol – wspólne dla USDC i EURC[web:64][web:76]
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
        raise RuntimeError("Brak USDC_CONTRACT_ADDRESS w .env")
    contract = get_erc20_contract(USDC_CONTRACT_ADDRESS)
    addr = checksum(address)
    raw = contract.functions.balanceOf(addr).call()
    return Decimal(raw) / (10 ** USDC_DECIMALS)


def get_eurc_balance(address: str) -> Decimal:
    require_connection()
    if not EURC_CONTRACT_ADDRESS:
        raise RuntimeError("Brak EURC_CONTRACT_ADDRESS w .env")
    contract = get_erc20_contract(EURC_CONTRACT_ADDRESS)
    addr = checksum(address)
    raw = contract.functions.balanceOf(addr).call()
    return Decimal(raw) / (10 ** EURC_DECIMALS)


def print_status():
    require_connection()
    latest_block = w3.eth.block_number
    block = w3.eth.get_block(latest_block)
    print("Połączenie udane!")
    print("Ostatni blok:", latest_block)
    print("Hash bloku:", block.hash.hex())
    print("Liczba transakcji w bloku:", len(block.transactions))

    if WALLET_ADDRESS:
        eth_bal = get_eth_balance(WALLET_ADDRESS)
        print(f"Saldo ETH {WALLET_ADDRESS}: {eth_bal} ETH")
        try:
            usdc_bal = get_usdc_balance(WALLET_ADDRESS)
            print(f"Saldo USDC {WALLET_ADDRESS}: {usdc_bal} USDC")
        except Exception as e:
            print(f"Nie udało się pobrać salda USDC: {e}")
        try:
            eurc_bal = get_eurc_balance(WALLET_ADDRESS)
            print(f"Saldo EURC {WALLET_ADDRESS}: {eurc_bal} EURC")
        except Exception as e:
            print(f"Nie udało się pobrać salda EURC: {e}")
    else:
        print("Brak WALLET_ADDRESS w .env")


def build_and_send_erc20_transfer(
    token_symbol: str,
    contract_address: str,
    decimals: int,
    to_address: str,
    amount: Decimal,
) -> str:
    require_connection()

    if not PRIVATE_KEY:
        raise RuntimeError("Brak PRIVATE_KEY w .env (trzymamy go tylko lokalnie).")

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
    print(f"{token_symbol} transfer wysłany, hash: {tx_hash.hex()}")
    return tx_hash.hex()


def send_usdc(to_address: str, amount: Decimal) -> str:
    if not USDC_CONTRACT_ADDRESS:
        raise RuntimeError("Brak USDC_CONTRACT_ADDRESS w .env")
    return build_and_send_erc20_transfer(
        "USDC", USDC_CONTRACT_ADDRESS, USDC_DECIMALS, to_address, amount
    )


def send_eurc(to_address: str, amount: Decimal) -> str:
    if not EURC_CONTRACT_ADDRESS:
        raise RuntimeError("Brak EURC_CONTRACT_ADDRESS w .env")
    return build_and_send_erc20_transfer(
        "EURC", EURC_CONTRACT_ADDRESS, EURC_DECIMALS, to_address, amount
    )


def send_eth(to_address: str, amount_eth: Decimal) -> str:
    """
    Wysyła native ETH z WALLET_ADDRESS na to_address.
    amount_eth podajesz w ETH, np. 0.01.
    """
    require_connection()

    if not PRIVATE_KEY:
        raise RuntimeError("Brak PRIVATE_KEY w .env (trzymamy go tylko lokalnie).")

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
    print(f"ETH transfer wysłany, hash: {tx_hash.hex()}")
    return tx_hash.hex()


def main():
    if len(sys.argv) < 2:
        print("Użycie:")
        print("  python main.py status")
        print("  python main.py balance")
        print("  python main.py send-eth <TO_ADDRESS> <AMOUNT_ETH>")
        print("  python main.py send-usdc <TO_ADDRESS> <AMOUNT_USDC>")
        print("  python main.py send-eurc <TO_ADDRESS> <AMOUNT_EURC>")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "status":
        print_status()

    elif cmd == "balance":
        if not WALLET_ADDRESS:
            print("Brak WALLET_ADDRESS w .env")
            sys.exit(1)
        eth_bal = get_eth_balance(WALLET_ADDRESS)
        print(f"ETH balance: {eth_bal} ETH")
        try:
            usdc_bal = get_usdc_balance(WALLET_ADDRESS)
            print(f"USDC balance: {usdc_bal} USDC")
        except Exception as e:
            print(f"Nie udało się pobrać salda USDC: {e}")
        try:
            eurc_bal = get_eurc_balance(WALLET_ADDRESS)
            print(f"EURC balance: {eurc_bal} EURC")
        except Exception as e:
            print(f"Nie udało się pobrać salda EURC: {e}")

    elif cmd == "send-eth":
        if len(sys.argv) != 4:
            print("Użycie: python main.py send-eth <TO_ADDRESS> <AMOUNT_ETH>")
            sys.exit(1)
        to_addr = sys.argv[2]
        amount_str = sys.argv[3]
        try:
            amount = Decimal(amount_str)
        except Exception:
            print("AMOUNT_ETH musi być liczbą (np. 0.01)")
            sys.exit(1)
        tx_hash = send_eth(to_addr, amount)
        print("Sprawdź transakcję na Sepolia Etherscan z tym hashem.")

    elif cmd == "send-usdc":
        if len(sys.argv) != 4:
            print("Użycie: python main.py send-usdc <TO_ADDRESS> <AMOUNT_USDC>")
            sys.exit(1)
        to_addr = sys.argv[2]
        amount_str = sys.argv[3]
        try:
            amount = Decimal(amount_str)
        except Exception:
            print("AMOUNT_USDC musi być liczbą (np. 1 lub 0.5)")
            sys.exit(1)
        tx_hash = send_usdc(to_addr, amount)
        print("Sprawdź transakcję na Sepolia Etherscan z tym hashem.")

    elif cmd == "send-eurc":
        if len(sys.argv) != 4:
            print("Użycie: python main.py send-eurc <TO_ADDRESS> <AMOUNT_EURC>")
            sys.exit(1)
        to_addr = sys.argv[2]
        amount_str = sys.argv[3]
        try:
            amount = Decimal(amount_str)
        except Exception:
            print("AMOUNT_EURC musi być liczbą (np. 1 lub 0.5)")
            sys.exit(1)
        tx_hash = send_eurc(to_addr, amount)
        print("Sprawdź transakcję na Sepolia Etherscan z tym hashem.")

    else:
        print(f"Nieznane polecenie: {cmd}")


if __name__ == "__main__":
    main()
