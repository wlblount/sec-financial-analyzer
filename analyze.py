from test_income_statement import get_quarterly_data
import pandas as pd
import sys

def analyze_company(ticker):
    """
    Analyze income statement for a given company ticker.
    """
    # Configure pandas display options for better readability
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 200)
    pd.set_option('display.max_colwidth', None)
    pd.set_option('expand_frame_repr', False)
    pd.set_option('display.precision', 2)
    pd.set_option('display.float_format', lambda x: '{:,.2f}'.format(x) if isinstance(x, (int, float)) else str(x))

    # Get quarterly data
    df = get_quarterly_data(ticker)
    
    # Reorder columns to show Period End Date first
    cols = df.columns.tolist()
    cols = ['Period End Date'] + [col for col in cols if col != 'Period End Date']
    df = df[cols]

    print(f"\nQuarterly Income Statement for {ticker}:")
    print("-" * 150)
    print(df)

    print(f"\nMost Recent Quarter Details:")
    print("-" * 150)
    print(df.head(1))

    return df

def main():
    if len(sys.argv) != 2:
        print("Usage: python analyze.py TICKER")
        print("Example: python analyze.py AAPL")
        sys.exit(1)
        
    ticker = sys.argv[1]
    df = get_quarterly_data(ticker)
    print(df)

if __name__ == "__main__":
    main() 