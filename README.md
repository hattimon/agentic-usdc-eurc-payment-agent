# Agentic USDC/EURC Payment Agent (Sepolia)

A simple agentic payment CLI that can send ETH, USDC, and EURC on the
Ethereum Sepolia testnet.\
It is designed as a reusable building block for other AI agents that
need to trigger on‑chain payments in stablecoins.

## Features

-   Sends native ETH on Ethereum Sepolia.
-   Sends USDC and EURC (Circle testnet tokens) via standard ERC‑20
    transfers.
-   Uses EIP‑1559 transactions with proper `chainId` for Sepolia.
-   Keeps all secrets in environment variables (`.env`), never in code
    or Git.
-   Simple CLI interface that other agents or scripts can call.

## Tech Stack

-   Python 3.11
-   [web3.py](https://github.com/ethereum/web3.py)
-   [python-dotenv](https://github.com/theskumar/python-dotenv)
-   Alchemy Ethereum Sepolia RPC

## Setup

Clone the repository and create a virtual environment:

``` bash
git clone https://github.com/hattimon/agentic-usdc-eurc-payment-agent.git
cd agentic-usdc-eurc-payment-agent

python -m venv venv
# Windows PowerShell:
.\venv\Scripts\activate
# or cmd.exe:
venv\Scripts\activate

python -m pip install -r requirements.txt
```

Configure your environment variables:

1.  Copy `.env.example` to `.env`:

    ``` bash
    cp .env.example .env
    ```

2.  Fill in the values in `.env`:

    -   `ALCHEMY_SEPOLIA_URL` -- your Sepolia RPC endpoint from Alchemy
    -   `WALLET_ADDRESS` -- the public address of your agent wallet
    -   `PRIVATE_KEY` -- **private key for that wallet (keep it local,
        never commit)**
    -   `USDC_CONTRACT_ADDRESS` -- USDC contract on Sepolia
    -   `EURC_CONTRACT_ADDRESS` -- EURC contract on Sepolia

> Note: `.env` is ignored by `.gitignore` so secrets will not be pushed
> to GitHub.

## Usage

Activate your virtual environment and run commands from the project
directory.

### 1. Check network and balances

``` bash
python main.py status
```

This prints: - Connection status to Sepolia, - Latest block number and
basic block info, - ETH / USDC / EURC balances for `WALLET_ADDRESS`.

You can also just print balances:

``` bash
python main.py balance
```

### 2. Send ETH

``` bash
python main.py send-eth <TO_ADDRESS> <AMOUNT_ETH>
```

Example:

``` bash
python main.py send-eth 0xC6A5dC8B35D5493883b6604E8D562F7945b5EEa4 0.05
```

### 3. Send USDC

``` bash
python main.py send-usdc <TO_ADDRESS> <AMOUNT_USDC>
```

Example:

``` bash
python main.py send-usdc 0xC6A5dC8B35D5493883b6604E8D562F7945b5EEa4 0.10
```

### 4. Send EURC

``` bash
python main.py send-eurc <TO_ADDRESS> <AMOUNT_EURC>
```

Example:

``` bash
python main.py send-eurc 0xC6A5dC8B35D5493883b6604E8D562F7945b5EEa4 1.0
```

All transactions are sent on **Ethereum Sepolia** using EIP‑1559 fields
(`maxFeePerGas`, `maxPriorityFeePerGas`, `chainId=11155111`).

## Proof of Work (Sepolia)

Example test transactions executed by this agent:

-   ETH transfer:
    `0xeaf7cd3d49333756e60e5440384fdeafc95e98ea9694edf2a3e1d2b3e198dd8a`
-   USDC transfer:
    `0x262f3523557b23b65dc4e72752091b09fdaad2316022625c3af8e3a2ba170f3c`
-   EURC transfer: `0x0b949d8351fee87f442a41f3aaef226b8990ec7c5f90429f404a740ad5ff1a93`

You can verify them on:\
https://sepolia.etherscan.io

## Security Notes

-   Never commit your real `PRIVATE_KEY` or `.env` file.
-   Use a dedicated test wallet for this agent.
-   Only use this project on testnets (Sepolia), not on mainnet.

## Hackathon Context

This project is built for the OpenClaw / USDC hackathon on Moltbook as
an **Agentic Commerce** building block:\
other agents can delegate on‑chain payments (ETH/USDC/EURC on Sepolia)
to this payment agent instead of implementing their own transaction
logic.

## Moltbook Integration (USDC Hackathon)

This agent is also registered as a Moltbook agent:

- Agent name: `USDC_EURC_Payment_Agent`
- Platform: https://www.moltbook.com

There is a helper script `register_moltbook.py` that registers an agent
with the Moltbook API (one-time operation, already executed for this project),
and a small client `moltbook_client.py` used to publish a project
submission post to the `m/usdc` submolt.

To post the USDC Hackathon project submission from this agent, run:

```bash
python main.py --post-moltbook
```

This uses the MOLTBOOK_API_KEY from .env and creates a
#USDCHackathon ProjectSubmission AgenticCommerce post on Moltbook.
