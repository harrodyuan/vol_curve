"""
SpiderRock Options Data Download via PyKX
==========================================

Connects to SpiderRock's kdb+ database to fetch intraday options trade data.
Saves to CSV for analysis with the volatility surface tools.

Requirements:
    pip install pykx pandas

License:
    Requires SpiderRock data subscription and kc.lic file in working directory.
"""

import os
import pandas as pd
from datetime import datetime, timedelta


def connect_spiderrock():
    """
    Establish connection to SpiderRock kdb+ server.
    Returns PyKX connection handle.
    """
    import pykx as kx
    
    host = os.getenv('SPIDERROCK_HOST', 'localhost')
    port = int(os.getenv('SPIDERROCK_PORT', 5000))
    
    return kx.SyncQConnection(host=host, port=port)


def fetch_opra_trades(conn, date: str, ticker: str = 'SPY') -> pd.DataFrame:
    """
    Fetch OPRA option trades for a given date and ticker.
    
    Args:
        conn: PyKX connection handle
        date: Trade date as 'YYYY.MM.DD'
        ticker: Underlying symbol (default: SPY)
    
    Returns:
        DataFrame with columns matching SpiderRock opratrade schema
    """
    query = f"""
    select 
        prtTimestamp,
        ticker_tk,
        okey_yr, okey_mn, okey_dy, okey_xx, okey_cp,
        prtPrice, prtSize, prtIv,
        uBid, uAsk, uPrc
    from opratrade 
    where date = {date}, ticker_tk = `{ticker}
    """
    
    result = conn(query)
    return result.pd()


def download_date_range(start_date: str, end_date: str, ticker: str = 'SPY'):
    """
    Download options data for a date range.
    
    Args:
        start_date: Start date as 'YYYY-MM-DD'
        end_date: End date as 'YYYY-MM-DD'
        ticker: Underlying symbol
    """
    conn = connect_spiderrock()
    
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    current = start
    while current <= end:
        date_str = current.strftime('%Y.%m.%d')
        filename = f"Opratrade_{date_str}_{ticker}.csv"
        
        if os.path.exists(filename):
            print(f"  Skip {filename} (exists)")
            current += timedelta(days=1)
            continue
        
        try:
            df = fetch_opra_trades(conn, date_str, ticker)
            if len(df) > 0:
                df.to_csv(filename, index=False)
                print(f"  Saved {filename} ({len(df):,} trades)")
            else:
                print(f"  Skip {date_str} (no data)")
        except Exception as e:
            print(f"  Error {date_str}: {e}")
        
        current += timedelta(days=1)
    
    conn.close()


def download_sample_day():
    """Download a single sample trading day for testing."""
    try:
        conn = connect_spiderrock()
        
        date = '2023.12.01'
        ticker = 'SPY'
        
        print(f"Downloading {ticker} trades for {date}...")
        df = fetch_opra_trades(conn, date, ticker)
        
        filename = f"Dec2023_Opratrade_{date}_{ticker}.csv"
        df.to_csv(filename, index=False)
        print(f"Saved {filename} ({len(df):,} trades)")
        
        conn.close()
        return df
        
    except Exception as e:
        print(f"Connection failed: {e}")
        print("\nTo use this script:")
        print("  1. Set SPIDERROCK_HOST and SPIDERROCK_PORT environment variables")
        print("  2. Place kc.lic in the working directory")
        print("  3. Ensure you have an active SpiderRock subscription")
        return None


if __name__ == '__main__':
    download_sample_day()

