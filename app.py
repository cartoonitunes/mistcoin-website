from flask import Flask, render_template, request, redirect, send_from_directory
import requests
import os
from datetime import datetime, UTC
import re
import time

app = Flask(__name__)


@app.after_request
def add_cache_headers(response):
    if request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    return response


@app.route('/robots.txt')
def robots():
    return send_from_directory('static', 'robots.txt')


@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('static', 'sitemap.xml')


@app.route('/llms.txt')
def llms_txt():
    return send_from_directory('static', 'llms.txt', mimetype='text/plain')


@app.route('/llms-full.txt')
def llms_full_txt():
    return send_from_directory('static', 'llms-full.txt', mimetype='text/plain')

# MistCoin reference
MISTCOIN_CONTRACT = "0x7fd4d7737597e7b4ee22acbf8d94362343ae0a79"
MISTCOIN_SUPPLY = 1_000_000
MISTCOIN_TIMESTAMP = 1446552343

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
BASESCAN_API_KEY = os.getenv("BASESCAN_API_KEY")  # legacy, V2 uses single key
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")

# Etherscan V2 unified API — single endpoint + key for all chains
ETHERSCAN_V2_BASE = "https://api.etherscan.io/v2/api"
CHAIN_IDS = {"eth": 1, "base": 8453}

# Simple in-memory cache for MistCoin price (5 min TTL)
_mist_price_cache = {"price": None, "expires": 0}

def get_cached_mist_price():
    now = time.time()
    if _mist_price_cache["price"] is not None and now < _mist_price_cache["expires"]:
        return _mist_price_cache["price"]
    try:
        mist_url = f"https://api.coingecko.com/api/v3/coins/ethereum/contract/{MISTCOIN_CONTRACT}?x_cg_demo_api_key={COINGECKO_API_KEY}"
        mist_resp = requests.get(mist_url, timeout=10)
        if mist_resp.status_code == 200:
            mist_data = mist_resp.json()
            price = mist_data.get("market_data", {}).get("current_price", {}).get("usd", 0.00001)
            _mist_price_cache["price"] = price
            _mist_price_cache["expires"] = now + 300  # 5 min
            return price
    except Exception:
        pass
    # Return cached value even if expired, or fallback
    return _mist_price_cache["price"] or 0.00001

def is_eth_address(address):
    return bool(re.fullmatch(r'^0x[a-fA-F0-9]{40}$', address))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/origin-checker', methods=['GET', 'POST'])
def origin_checker():
    if request.method == 'POST':
        contract = request.form.get('contract', '').strip().lower()
        chain = request.form.get('chain', 'eth').lower()

        if not contract:
            return render_template('origin.html', error="Please enter a contract address.")

        if not is_eth_address(contract):
            return render_template('origin.html', error="Please enter a valid contract address.")

        # Step 1: Get deployment timestamp via getcontractcreation (Etherscan V2)
        deployed_ts = None
        deployed_date = None
        origin = None
        try:
            chain_id = CHAIN_IDS.get(chain)
            if not chain_id:
                return render_template('origin.html', error="Unsupported chain.")

            api_key = ETHERSCAN_API_KEY

            api_url = (
                f"{ETHERSCAN_V2_BASE}"
                f"?chainid={chain_id}"
                f"&module=contract&action=getcontractcreation"
                f"&contractaddresses={contract}"
                f"&apikey={api_key}"
            )

            tx_resp = requests.get(api_url, timeout=10).json()

            if tx_resp.get("status") != "1" or not tx_resp.get("result"):
                # Fallback to txlist with pagination
                fallback_url = (
                    f"{ETHERSCAN_V2_BASE}"
                    f"?chainid={chain_id}"
                    f"&module=account&action=txlist"
                    f"&address={contract}"
                    f"&startblock=0&endblock=99999999"
                    f"&page=1&offset=1"
                    f"&sort=asc&apikey={api_key}"
                )
                fb_resp = requests.get(fallback_url, timeout=10).json()
                if fb_resp.get("status") != "1" or not fb_resp.get("result"):
                    return render_template('origin.html', error="Could not find deployment transaction. Make sure this is a contract address.")
                deployed_ts = int(fb_resp["result"][0]["timeStamp"])
            else:
                # Get the creation tx hash, then fetch its timestamp
                creation_tx = tx_resp["result"][0].get("txHash")
                if creation_tx:
                    tx_detail_url = (
                        f"{ETHERSCAN_V2_BASE}"
                        f"?chainid={chain_id}"
                        f"&module=proxy&action=eth_getTransactionByHash"
                        f"&txhash={creation_tx}"
                        f"&apikey={api_key}"
                    )

                    tx_detail = requests.get(tx_detail_url, timeout=10).json()
                    block_hex = tx_detail.get("result", {}).get("blockNumber")
                    if block_hex:
                        block_num = int(block_hex, 16)
                        block_url = (
                            f"{ETHERSCAN_V2_BASE}"
                            f"?chainid={chain_id}"
                            f"&module=block&action=getblockreward"
                            f"&blockno={block_num}"
                            f"&apikey={api_key}"
                        )
                        block_resp = requests.get(block_url, timeout=10).json()
                        deployed_ts = int(block_resp.get("result", {}).get("timeStamp", 0))

                if not deployed_ts:
                    # Final fallback
                    return render_template('origin.html', error="Could not determine deployment date.")

            deployed_date = datetime.fromtimestamp(deployed_ts, tz=UTC).strftime('%Y-%m-%d')
            origin = "MistCoin $WMC" if deployed_ts > MISTCOIN_TIMESTAMP else "Vitalik Buterin's Standard Docs"

        except requests.exceptions.Timeout:
            return render_template('origin.html', error="Request timed out. Please try again.")
        except Exception:
            return render_template('origin.html', error="Error fetching deployment data. Please try again.")

        is_wrapped_mistcoin = contract.lower() == MISTCOIN_CONTRACT.lower()

        # Calculate days difference
        mist_date = datetime.fromtimestamp(MISTCOIN_TIMESTAMP, tz=UTC)
        token_date = datetime.fromtimestamp(deployed_ts, tz=UTC)
        days_diff = abs((token_date - mist_date).days)

        # Step 2: Try to get token info from CoinGecko (graceful degradation)
        name = None
        symbol = None
        logo = None
        price = None
        market_cap = None
        mist_price = None
        mistcoin_valued_price = None
        percent_up = None
        cg_available = False

        try:
            cg_chain = 'ethereum' if chain == 'eth' else chain
            cg_url = f"https://api.coingecko.com/api/v3/coins/{cg_chain}/contract/{contract}?x_cg_demo_api_key={COINGECKO_API_KEY}"
            token_resp = requests.get(cg_url, timeout=10)

            if token_resp.status_code == 200:
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
                cg_available = True
        except Exception:
            pass

        # Step 3: Get MistCoin price (cached)
        if cg_available and not is_wrapped_mistcoin:
            mist_price = get_cached_mist_price()

        # Step 4: Calculate comparison if we have market data
        if cg_available and market_cap and mist_price and mist_price > 0:
            mistcoin_valued_price = market_cap / MISTCOIN_SUPPLY
            percent_up = ((mistcoin_valued_price - mist_price) / mist_price) * 100

        # Render result with whatever data we have
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
            market_cap=round(market_cap, 2) if market_cap else None,
            mistcoin_price=mist_price,
            new_mistcoin_price=round(mistcoin_valued_price, 6) if mistcoin_valued_price else None,
            percent_up=round(percent_up, 2) if percent_up is not None else None,
            deployed_date=deployed_date,
            days_diff=days_diff,
            cg_available=cg_available
        )

    # GET: prefill form from query params if present
    contract = request.args.get('contract', '')
    chain = request.args.get('chain', 'eth')
    return render_template('origin.html', contract=contract, chain=chain)

@app.route('/mist-simulator')
def mist_simulator():
    return render_template('mist_simulator.html')

@app.route('/<path:anything>')
def catch_all(anything):
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
