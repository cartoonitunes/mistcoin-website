from flask import Flask, render_template, request, redirect
import requests
import os
from datetime import datetime, UTC
import re

app = Flask(__name__)

# MistCoin reference
MISTCOIN_CONTRACT = "0x7fd4d7737597e7b4ee22acbf8d94362343ae0a79"
MISTCOIN_SUPPLY = 1_000_000
MISTCOIN_TIMESTAMP = 1446552343

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
BASESCAN_API_KEY = os.getenv("BASESCAN_API_KEY")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")

def is_eth_address(address):
    return bool(re.fullmatch(r'^0x[a-fA-F0-9]{40}$', address))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/origin-checker', methods=['GET', 'POST'])
def origin_checker():
    if request.method == 'POST':
        contract = request.form.get('contract', '').lower()
        chain = request.form.get('chain', 'eth').lower()

        if not contract:
            return render_template('origin.html', error="Please enter a contract address.")
        
        is_contract_eth_address = is_eth_address(contract)
        if is_contract_eth_address == False:
            return render_template('origin.html', error="Please enter a valid contract address.")

        # Step 1: Get deployment timestamp
        try:
            if chain == 'eth':
                api_url = (
                    f"https://api.etherscan.io/api"
                    f"?module=account&action=txlist"
                    f"&address={contract}"
                    f"&startblock=0&endblock=99999999"
                    f"&sort=asc&apikey={ETHERSCAN_API_KEY}"
                )
            elif chain == 'base':
                api_url = (
                    f"https://api.basescan.org/api"
                    f"?module=account&action=txlist"
                    f"&address={contract}"
                    f"&startblock=0&endblock=99999999"
                    f"&sort=asc&apikey={BASESCAN_API_KEY}"
                )
            else:
                return render_template('origin.html', error="Unsupported chain.")

            tx_resp = requests.get(api_url).json()
            if tx_resp["status"] != "1" or not tx_resp["result"]:
                return render_template('origin.html', error="Could not find deployment transaction.")

            deployed_ts = int(tx_resp["result"][0]["timeStamp"])
            deployed_date = datetime.fromtimestamp(deployed_ts, tz=UTC).strftime('%Y-%m-%d')
            origin = "MistCoin $WMC" if deployed_ts > MISTCOIN_TIMESTAMP else "Vitalik Buterin's Standard Docs"

        except Exception as e:
            return render_template('origin.html', error=f"Error fetching deployment timestamp: {str(e)}")

        is_wrapped_mistcoin = False
        if contract.lower() == '0x7Fd4d7737597E7b4ee22AcbF8D94362343ae0a79'.lower():
            is_wrapped_mistcoin = True

        # Step 2: Get token info from Coingecko
        try:
            cg_url = f"https://api.coingecko.com/api/v3/coins/{chain}/contract/{contract}?x_cg_demo_api_key={COINGECKO_API_KEY}"
            token_resp = requests.get(cg_url)

            if token_resp.status_code != 200:
                return render_template('origin.html', error="Token not found on Coingecko.")

            token = token_resp.json()
            name = token.get("name", "Unknown")
            symbol = token.get("symbol", "???").upper()
            logo = token.get("image", {}).get("large", "/static/assets/img/default.png")
            price = token.get("market_data", {}).get("current_price", {}).get("usd", 0)
            if is_wrapped_mistcoin:
                market_cap = price * MISTCOIN_SUPPLY
                mist_price = price
            else:
                market_cap = token.get("market_data", {}).get("market_cap", {}).get("usd", 0)

        except Exception as e:
            return render_template('origin.html', error=f"Error fetching token data: {str(e)}")

        # Step 3: Get MistCoin live price from Coingecko
        if not is_wrapped_mistcoin:
            try:
                mist_url = f"https://api.coingecko.com/api/v3/coins/ethereum/contract/{MISTCOIN_CONTRACT}?x_cg_demo_api_key={COINGECKO_API_KEY}"
                mist_resp = requests.get(mist_url)

                if mist_resp.status_code != 200:
                    return render_template('origin.html', error="Could not retrieve MistCoin price.")

                mist_data = mist_resp.json()
                mist_price = mist_data.get("market_data", {}).get("current_price", {}).get("usd", 0.00001)

            except Exception as e:
                return render_template('origin.html', error=f"Error fetching MistCoin price: {str(e)}")

        # Step 4: Calculate MistCoin price if it had the same market cap
        try:
            mistcoin_valued_price = market_cap / MISTCOIN_SUPPLY
            percent_up = ((mistcoin_valued_price - mist_price) / mist_price) * 100
        except ZeroDivisionError:
            return render_template('origin.html', error="MistCoin price is currently zero, cannot compute comparison.")

        # Final: Render result
        return render_template(
            'origin.html',
            contract=contract,
            chain=chain,
            name=name,
            price=price,
            symbol=symbol,
            logo=logo,
            chain_upper=chain.upper(),
            origin=origin,
            market_cap=round(market_cap, 2),
            mistcoin_price=mist_price,
            new_mistcoin_price=round(mistcoin_valued_price, 6),
            percent_up=round(percent_up, 2),
            deployed_date=deployed_date
        )

    # GET: prefill form from query params if present
    contract = request.args.get('contract', '')
    chain = request.args.get('chain', 'eth')
    return render_template('origin.html', contract=contract, chain=chain)

@app.route('/<path:anything>')
def catch_all(anything):
    return redirect('/')



