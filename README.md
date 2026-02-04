# Agentic USDC/EURC Payment Agent (Sepolia)

Pythonowy agent CLI, który wysyła ETH, USDC i EURC na sieci Ethereum Sepolia (testnet). Służy jako prosty building block do agentic commerce.

## Setup

```bash
python -m venv venv
.\venv\Scripts\activate
python -m pip install -r requirements.txt
```

Skopiuj .env.example do .env i uzupełnij własnymi danymi.

Usage
```bash
python main.py status
python main.py balance
python main.py send-eth <TO_ADDRESS> <AMOUNT_ETH>
python main.py send-usdc <TO_ADDRESS> <AMOUNT_USDC>
python main.py send-eurc <TO_ADDRESS> <AMOUNT_EURC>
```