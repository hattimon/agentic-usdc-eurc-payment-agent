import requests
import json

url = "https://www.moltbook.com/api/v1/agents/register"

payload = {
    "name": "USDC_EURC_Payment_Agent",
    "description": "Python agent that sends ETH, USDC and EURC on Ethereum Sepolia testnet."
}

resp = requests.post(url, json=payload, timeout=30)
resp.raise_for_status()

print(json.dumps(resp.json(), indent=2))
