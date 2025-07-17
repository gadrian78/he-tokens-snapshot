######################################
#
# Hive Portfolio Tracker
#
# Created by https://peakd.com/@gadrian using "vibe" coding in June-July 2025.
#
# Use it or modify to your needs freely. Keep this author details and add to it, if you build on it.
#
######################################

import json
import os
import sys
from datetime import datetime
from prettytable import PrettyTable, TableStyle
import argparse

from hiveengine.api import Api
from hiveengine.market import Market

# Import configs
from modules.config import DEFAULT_ACCOUNT, DEFAULT_TOKENS, BASE_SNAPSHOTS_DIR

from modules.regular_tokens import (
    debug_log as util_debug_log,
    get_hive_price_usd,
    get_btc_price_usd,
    get_token_holdings,
    get_market_info,
    fetch_all_tokens
)

from modules.cache_utils import clear_caches

from modules.misc_utils import (
    validate_token,
    validate_username,
    get_snapshot_types_for_date,
    generate_snapshot_filename,
    get_user_snapshots_dir,
    validate_snapshots_dir
)

# Import diesel pool functions
from modules.diesel_pools import (
    get_user_pool_portfolio,
    get_required_tokens_for_pools,
    display_diesel_pools_table,
    set_debug_mode
)

# Import Layer 1 holdings functions
from modules.layer1_holdings import (
    get_user_layer1_portfolio,
    display_layer1_table,
    create_layer1_json_data,
    get_hbd_price_usd,
    set_debug_mode as set_layer1_debug_mode
)

api = Api()
market = Market(api)

def get_version_from_pyproject():
    """Read version from pyproject.toml file"""
    try:
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        pyproject_path = os.path.join(script_dir, 'pyproject.toml')
        
        if os.path.exists(pyproject_path):
            with open(pyproject_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('version = '):
                        # Extract version from line like: version = "1.53"
                        version = line.split('=', 1)[1].strip()
                        # Remove quotes
                        version = version.strip('"\'')
                        return version
        
        # Fallback: try importlib.metadata (for when actually installed)
        try:
            from importlib.metadata import version
            return version("my-hive-engine-tokens-snapshot")
        except:
            return "1.60"  # hardcoded fallback

    except Exception as e:
        return f"1.60-error({str(e)[:20]})"

VERSION = get_version_from_pyproject()

DEBUG = False

def debug_log(text):
    """Local debug logging function that respects the DEBUG flag"""
    if DEBUG:
        print(text)

# Override the utility module's debug_log function
util_debug_log.debug_log = debug_log

# Set debug mode for diesel pools module if available
set_debug_mode(DEBUG)

def create_portfolio_json(token_data, pool_data, layer1_holdings, layer1_values, hive_usd, hbd_usd, btc_usd, account, timestamp):
    """Create comprehensive portfolio JSON structure"""
    
    # Calculate totals
    total_tokens_usd = sum(t["total_usd"] for t in token_data)
    total_pools_usd = sum(p["total_usd"] for p in pool_data)
    total_layer1_usd = layer1_values["total_combined_usd"] if layer1_values else 0
    total_combined_usd = total_tokens_usd + total_pools_usd + total_layer1_usd
    
    total_tokens_hive = sum(t["total_hive"] for t in token_data)
    total_pools_hive = sum(p["total_hive"] for p in pool_data)
    total_layer1_hive = layer1_values["total_combined_hive"] if layer1_values else 0
    total_combined_hive = total_tokens_hive + total_pools_hive + total_layer1_hive
    
    total_combined_btc = total_combined_usd / btc_usd if btc_usd > 0 else 0
    
    # Build comprehensive JSON structure
    portfolio_data = {
        "metadata": {
            "account": account,
            "snapshot_timestamp": timestamp,
            "snapshot_unix": int(datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").timestamp()),
            "script_version": VERSION,
            "prices": {
                "hive_usd": hive_usd,
                "hbd_usd": hbd_usd,
                "btc_usd": btc_usd,
                "hive_btc_ratio": int(btc_usd / hive_usd) if hive_usd > 0 else 0
            }
        },
        "summary": {
            "total_portfolio": {
                "usd": total_combined_usd,
                "hive": total_combined_hive,
                "btc": total_combined_btc
            },
            "layer1_total": {
                "usd": total_layer1_usd,
                "hive": total_layer1_hive,
                "btc": total_layer1_usd / btc_usd if btc_usd > 0 else 0
            },
            "tokens_total": {
                "usd": total_tokens_usd,
                "hive": total_tokens_hive,
                "btc": total_tokens_usd / btc_usd if btc_usd > 0 else 0
            },
            "pools_total": {
                "usd": total_pools_usd,
                "hive": total_pools_hive,
                "btc": total_pools_usd / btc_usd if btc_usd > 0 else 0
            },
            "token_count": len([t for t in token_data if t["total_usd"] > 0]),
            "pool_count": len(pool_data),
            "layer1_assets": len([k for k, v in layer1_values.items() if k.endswith('_usd') and v > 0]) if layer1_values else 0
        },
        "layer1_holdings": create_layer1_json_data(layer1_holdings, layer1_values, hive_usd, hbd_usd, btc_usd, account, timestamp) if layer1_holdings and layer1_values else {},
        "tokens": {
            token["symbol"]: {
                "liquid": token["liquid"],
                "staked": token["staked"],
                "delegated": token["delegated"],
                "total_amount": token["liquid"] + token["staked"] + token["delegated"],
                "market": {
                    "volume_24h_usd": token["volume_24h_usd"]
                },
                "values": {
                    "usd": token["total_usd"],
                    "hive": token["total_hive"],
                    "btc": token["total_btc"]
                }
            }
            for token in token_data if token["total_usd"] > 0 or token["liquid"] + token["staked"] + token["delegated"] > 0
        },
        "diesel_pools": {
            pool["token_pair"]: {
                "pool_name": pool.get("token_pair", pool["token_pair"]),
                "shares": pool["user_shares"],
                "share_percentage": pool.get("share_percentage", 0),
                "base_amount": pool.get("base_amount", 0),
                "quote_amount": pool.get("quote_amount", 0),
                "values": {
                    "usd": pool["total_usd"],
                    "hive": pool["total_hive"],
                    "btc": pool["total_btc"]
                }
            }
            for pool in pool_data
        }
    }
    
    return portfolio_data

def save_snapshot(snapshot_type, token_data, pool_data, layer1_holdings, layer1_values, hive_usd, hbd_usd, btc_usd, account, timestamp, snapshots_dir):
    """Save a single snapshot file"""
    
    # Create directory structure
    type_dir = os.path.join(snapshots_dir, snapshot_type)
    os.makedirs(type_dir, exist_ok=True)
    
    # Generate filename
    date_obj = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    filename = generate_snapshot_filename(snapshot_type, account, date_obj)
    filepath = os.path.join(type_dir, filename)
    
    # Create JSON data
    portfolio_json = create_portfolio_json(token_data, pool_data, layer1_holdings, layer1_values, hive_usd, hbd_usd, btc_usd, account, timestamp)
    
    # Add snapshot-specific metadata
    portfolio_json["metadata"]["snapshot_type"] = snapshot_type
    portfolio_json["metadata"]["filename"] = filename
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(portfolio_json, f, indent=2, ensure_ascii=False)
        
        debug_log(f"✅ Saved {snapshot_type} snapshot: {filepath}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to save {snapshot_type} snapshot: {e}")
        return False

def save_automated_snapshots(token_data, pool_data, layer1_holdings, layer1_values, hive_usd, hbd_usd, btc_usd, account, timestamp, snapshots_dir, quiet=False):
    """Save all applicable snapshot types for the current date"""

     # Get user-specific snapshots directory
    user_snapshots_dir = get_user_snapshots_dir(snapshots_dir, account)

     # Create user directory if it doesn't exist
    os.makedirs(user_snapshots_dir, exist_ok=True)
    
    date_obj = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    snapshot_types = get_snapshot_types_for_date(date_obj)
    
    if not quiet:
        print(f"📸 Taking snapshots: {', '.join(snapshot_types)}")
        print(f"📁 Saving to: {user_snapshots_dir}")
    
    saved_count = 0
    for snapshot_type in snapshot_types:
        if save_snapshot(snapshot_type, token_data, pool_data, layer1_holdings, layer1_values, hive_usd, hbd_usd, btc_usd, account, timestamp, user_snapshots_dir):
            saved_count += 1
    
    if not quiet:
        print(f"✅ Successfully saved {saved_count}/{len(snapshot_types)} snapshots")
        print()
    
    return saved_count

def display_table(token_data, hive_price_usd, btc_price_usd, account):
    """Display token holdings in a formatted table"""
    # Sort tokens by total USD value (descending)
    sorted_tokens = sorted(token_data, key=lambda x: x["total_usd"], reverse=True)

    table = PrettyTable()
    table.field_names = [
        "Symbol", "Liquid", "Staked", "Delegated", "Total", 
        "Price (HIVE)", "Price (USD)", 
        "24h Vol (USD)", "USD Value", "HIVE Value", "BTC Value"
    ]

    total_usd = total_hive = total_btc = 0

    for token in sorted_tokens:
        total = token["liquid"] + token["staked"] + token["delegated"]
        if total > 0:
            table.add_row([
                token["symbol"],
                f'{token["liquid"]:,.3f}',
                f'{token["staked"]:,.3f}',
                f'{token["delegated"]:,.3f}',
                f'{total:,.3f}',
                f'{token["price_hive"]:,.6f}',
                f'{token["price_usd"]:,.2f}',
                f'{token["volume_24h_usd"]:,.2f}',
                f'{token["total_usd"]:,.2f}',
                f'{token["total_hive"]:,.3f}',
                f'{token["total_btc"]:,.8f}',
            ])

        total_usd += token["total_usd"]
        total_hive += token["total_hive"]
        total_btc += token["total_btc"]

    if len(sorted_tokens) > 1:  # Only add totals if more than one token
        table.add_divider()
        # Add summary row
        table.add_row([
            "TOTAL", "", "", "", "",
            "", "",
            "",
            f'{total_usd:,.2f}',
            f'{total_hive:,.3f}',
            f'{total_btc:,.8f}'
        ])

    table.align = "r"
    table.align["Symbol"] = "l"
    table.set_style(TableStyle.SINGLE_BORDER)

    print("💰 TOKEN HOLDINGS:")
    print(table)

def parse_arguments():
    """Command-line arguments parsing"""
    parser = argparse.ArgumentParser(
        description=f"Hive Portfolio Tracker v{VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 take-snapshot.py
  python3 take-snapshot.py -u alice
  python3 take-snapshot.py -u bob -t SPS LEO DEC
  python3 take-snapshot.py --username charlie --tokens SWAP.BTC DBOND INCOME
  python3 take-snapshot.py --debug
  python3 take-snapshot.py --quiet --snapshots-dir /path/to/snapshots
  python3 take-snapshot.py --no-layer1

Remarks:
  - Username must be a valid Hive username.
  - Tokens must be valid Hive-Engine tokens.
  - Layer 1 holdings (HIVE, HP, HBD, savings) are tracked by default.
  - Diesel pools are tracked automatically.
  - Snapshots are automatically saved based on current date.
  - Use --debug to see detailed processing information.
  - Use --quiet for automated/scheduled runs.
  - Use --no-layer1 to skip Layer 1 holdings tracking.

Snapshot Types (automatic based on date):
  - Daily: Every day
  - Weekly: Every Monday (+ daily)
  - Monthly: 1st of each month (+ daily, + weekly if Monday)
  - Quarterly: 1st of Jan/Apr/Jul/Oct (+ daily, + weekly if Monday, + monthly)
  - Yearly: January 1st (+ all other applicable types)

Tip:
  Use redirect to have the console output in a file instead of the screen.
        """
    )
    
    parser.add_argument(
        '-u', '--username',
        type=str,
        help=f'Hive username to check (default: {DEFAULT_ACCOUNT})'
    )
    
    parser.add_argument(
        '-t', '--tokens',
        nargs='+',
        type=str,
        help=f'List of tokens to snapshot (default: {" ".join(DEFAULT_TOKENS)})'
    )
    
    parser.add_argument(
        '--snapshots-dir',
        type=str,
        default='./snapshots',
        help='Directory to save snapshots (default: ./snapshots)'
    )
    
    parser.add_argument(
        '--no-layer1',
        action='store_true',
        help='Skip Layer 1 holdings tracking (HIVE, HP, HBD, savings)'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress console output (useful for automated runs)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output'
    )
    
    return parser.parse_args()

def main():
    global DEBUG
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Set debug mode
    if (args.debug): DEBUG = args.debug

    QUIET = args.quiet
    if (QUIET): DEBUG = False
    
    # Update debug functions
    util_debug_log = debug_log
    set_debug_mode(DEBUG)
    set_layer1_debug_mode(DEBUG)
    
    # Use command line arguments if provided, otherwise use defaults
    ACCOUNT = args.username if args.username else DEFAULT_ACCOUNT
    TOKENS = [token.upper() for token in args.tokens] if args.tokens else DEFAULT_TOKENS
    SKIP_LAYER1 = args.no_layer1
    
    # Validate snapshots directory
    SNAPSHOTS_DIR = args.snapshots_dir if args.snapshots_dir else BASE_SNAPSHOTS_DIR
    is_valid_dir, dir_msg, normalized_dir = validate_snapshots_dir(SNAPSHOTS_DIR)
    
    if not is_valid_dir:
        if not QUIET:
            print(f"❌ Invalid snapshots directory '{SNAPSHOTS_DIR}': {dir_msg}")
        return
    
    # Use the normalized path
    SNAPSHOTS_DIR = normalized_dir

    if ACCOUNT:
        ACCOUNT = ACCOUNT.lower()
        
    # Validate username
    is_valid_user, user_msg = validate_username(ACCOUNT)
    if not is_valid_user:
        if not QUIET:
            print(f"❌ Invalid username '{ACCOUNT}': {user_msg}")
            print("   Username must be a valid Hive username.")
        return
    
    debug_log(f"🎯 Account: @{ACCOUNT}")
    debug_log("🔍 Fetching token list from Hive Engine for validation...")
    
    valid_token_symbols = fetch_all_tokens(api)
    debug_log(f"✅ Found {len(valid_token_symbols)} valid tokens")

    # Validate tokens
    for token in TOKENS:
        is_valid_token, token_msg = validate_token(token, valid_token_symbols)
        if not is_valid_token:
            if not QUIET:
                print(f"❌ Invalid token: {token_msg}")
                print("   Token must be a valid Hive-Engine token.")
            return

    # add diesel pool tokens to the list of tokens to check on
    # converting return of addition to a set removes duplicates 
    diesel_pool_tokens = get_required_tokens_for_pools(ACCOUNT, api)
    TOKENS = list(set(TOKENS + list(diesel_pool_tokens)))

    # Display what we're using
    debug_log(f"🪙 Tokens: {', '.join(TOKENS)}")
    debug_log(f"🏦 Layer 1 tracking: {'disabled' if SKIP_LAYER1 else 'enabled'}")
    dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    debug_log(f"   Snapshot date/time: {dt}")
    debug_log('')

    if not QUIET:
        print(f"🔄 Fetching data for @{ACCOUNT}...")

    # Get regular token holdings
    debug_log("📊 Fetching token holdings...")
    holdings = get_token_holdings(api, ACCOUNT, TOKENS)        

    # Get price data
    debug_log("💰 Fetching HIVE, HBD, and BTC prices...")
    hive_usd = get_hive_price_usd()
    hbd_usd = get_hbd_price_usd()
    btc_usd = get_btc_price_usd()
    
    debug_log(f"💰 HIVE: ${hive_usd:.6f}, HBD: ${hbd_usd:.6f}, BTC: ${btc_usd:.0f}")

    # Get Layer 1 holdings
    layer1_holdings = None
    layer1_values = None
    if not SKIP_LAYER1:
        debug_log("🏦 Fetching Layer 1 holdings...")
        layer1_holdings, layer1_values = get_user_layer1_portfolio(ACCOUNT)
        if layer1_holdings and layer1_values:
            debug_log(f"✅ Layer 1 holdings fetched successfully")
        else:
            debug_log("⚠️ No Layer 1 holdings found or failed to fetch")

    # Process regular tokens
    token_data = []
    token_prices = {}  # Store prices for diesel pool calculations

    for sym in TOKENS:
        d = holdings.get(sym, {"liquid": 0.0, "staked": 0.0, "delegated_away": 0.0})
        debug_log(f"📊 Fetching market data for {sym}...")
        price_hive, vol24_hive = get_market_info(api, market, sym)
        
        # Store price for diesel pool calculations
        token_prices[sym] = price_hive
        
        total_amount = d['liquid'] + d['staked'] + d['delegated_away']
        price_usd = price_hive * hive_usd
        vol24_usd = vol24_hive * hive_usd
        total_usd = total_amount * price_usd
        total_hive = total_amount * price_hive
        total_btc = total_usd / btc_usd if btc_usd > 0 else 0
        
        token_data.append({
            "symbol": sym,
            "liquid": d['liquid'],
            "staked": d['staked'],
            "delegated": d['delegated_away'],
            "price_hive": price_hive,
            "price_usd": price_usd,
            "volume_24h_usd": vol24_usd,
            "total_usd": total_usd,
            "total_hive": total_hive,
            "total_btc": total_btc
        })

    # Get diesel pool holdings if available
    pool_data = []
    debug_log("🏊 Fetching diesel pool positions...")

    # Get additional token prices that might be needed for pools
    # We'll let the diesel pool module handle price fetching for pool tokens
    pool_data = get_user_pool_portfolio(ACCOUNT, api, token_prices)

    if pool_data:
        debug_log(f"✅ Found {len(pool_data)} diesel pool positions")
        # Convert to USD and BTC values
        for pool in pool_data:
            pool["total_usd"] = pool["total_hive"] * hive_usd
            pool["total_btc"] = pool["total_usd"] / btc_usd if btc_usd > 0 else 0
    else:
        debug_log("ℹ️ No diesel pool positions found")

    # Save automated snapshots (always save, regardless of quiet mode)
    save_automated_snapshots(token_data, pool_data, layer1_holdings, layer1_values, hive_usd, hbd_usd, btc_usd, ACCOUNT, dt, SNAPSHOTS_DIR, QUIET)

    # Skip console display if quiet mode
    if QUIET:
        clear_caches()
        return

    # Display header information
    print()
    print(f"🎯 Account: @{ACCOUNT}")
    print(f"🪙 Tokens: {', '.join(TOKENS)}")
    print(f"🏦 Layer 1 tracking: {'disabled' if SKIP_LAYER1 else 'enabled'}")
    print(f"   Snapshot date/time: {dt}")
    print()
    print(f"💰 HIVE Price: ${hive_usd:.6f}")
    print(f"💰 HBD Price: ${hbd_usd:.6f}")
    print(f"🪙 BTC Price: ${btc_usd:,.0f}")
    print()

    # Display results
    has_layer1_data = layer1_holdings and layer1_values and layer1_values.get("total_combined_usd", 0) > 0
    has_token_data = any(t["total_usd"] > 0 for t in token_data)
    has_pool_data = len(pool_data) > 0

    if has_layer1_data:
        display_layer1_table(layer1_holdings, layer1_values, hive_usd, hbd_usd, btc_usd, ACCOUNT)
        print()
    elif not SKIP_LAYER1:
        debug_log("ℹ️ No Layer 1 holdings found")
    
    if has_token_data:
        display_table(token_data, hive_usd, btc_usd, ACCOUNT)
        print()
    else:
        print("ℹ️ No significant token holdings found")
    
    if has_pool_data:
        display_diesel_pools_table(pool_data, hive_usd, btc_usd, ACCOUNT)
        print()
    else:
        debug_log("ℹ️ No diesel pool positions found")
    
    # Display combined totals if multiple categories exist
    categories_count = sum([has_layer1_data, has_token_data, has_pool_data])
    if categories_count > 1:
        total_layer1_usd = layer1_values["total_combined_usd"] if layer1_values else 0
        total_tokens_usd = sum(t["total_usd"] for t in token_data)
        total_pools_usd = sum(p["total_usd"] for p in pool_data)
        total_combined_usd = total_layer1_usd + total_tokens_usd + total_pools_usd
        
        total_layer1_hive = layer1_values["total_combined_hive"] if layer1_values else 0
        total_tokens_hive = sum(t["total_hive"] for t in token_data)
        total_pools_hive = sum(p["total_hive"] for p in pool_data)
        total_combined_hive = total_layer1_hive + total_tokens_hive + total_pools_hive
        
        total_combined_btc = total_combined_usd / btc_usd if btc_usd > 0 else 0
        
        print("=" * 90)
        print("📊 COMBINED PORTFOLIO SUMMARY:")
        if has_layer1_data:
            print(f"   Layer 1 Holdings: {total_layer1_usd:10,.2f} USD  |  {total_layer1_hive:11,.3f} HIVE")
        if has_token_data:
            print(f"   HE Tokens:        {total_tokens_usd:10,.2f} USD  |  {total_tokens_hive:11,.3f} HIVE")
        if has_pool_data:
            print(f"   Diesel Pools:     {total_pools_usd:10,.2f} USD  |  {total_pools_hive:11,.3f} HIVE")
        print(f"   TOTAL PORTFOLIO:  {total_combined_usd:10,.2f} USD  |  {total_combined_hive:11,.3f} HIVE  |  {total_combined_btc:3.8f} BTC")
        print("=" * 90)

    # Add BTC/HIVE ratio, and prices of HIVE, HBD, and BTC
    if btc_usd > 0 and hive_usd > 0:
        hive_btc_ratio = int(btc_usd / hive_usd)
        print()
        print(f"  HIVE:BTC ≈ 1/{hive_btc_ratio:,.0f}")
        print(f"  HIVE:USD = ${hive_usd:,.6f}")
        print(f"  HBD :USD = ${hbd_usd:,.6f}")
        print(f"  BTC :USD = ${btc_usd:,.0f}")
        print()

    # Clear caches at the end
    clear_caches()

if __name__ == "__main__":
    main()
