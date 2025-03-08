from sec_filing_fetcher import SECFilingFetcher, FINANCIAL_CONCEPTS
from datetime import datetime
import requests
import json
import pandas as pd

def format_value_with_scale(value, scale=None):
    """Return raw value without formatting."""
    if pd.isna(value):
        return 'N/A'
    return value

def format_percent(value):
    """Format number as percentage"""
    return f"{value:.1f}%"

def get_quarter_name(date_str):
    """Convert date to quarter name (e.g., Q1 2024)"""
    date = datetime.strptime(date_str, '%Y-%m-%d')
    month = date.month
    quarter = (month - 1) // 3 + 1
    return f"Q{quarter} {date.year}"

def get_metric_with_alternatives(fetcher, ticker, primary_metric, alternatives, period_type, offset):
    """Try to get a metric using alternative tags if primary one fails"""
    metrics_to_try = [primary_metric] + alternatives
    for metric in metrics_to_try:
        data = fetcher.get_financial_data_for_period(ticker, metric, period_type, offset)
        if data:
            return data
    return None

def find_q4_data(fetcher, ticker, metric, alternatives=[]):
    """
    Calculate Q4 3-month data by subtracting Q3 YTD from annual total.
    Returns a dictionary matching SEC API structure if found, None otherwise.
    """
    # Get all values for this metric
    all_data = []
    for i in range(20):  # Look through more periods to find both Q3 YTD and annual
        data = get_metric_with_alternatives(fetcher, ticker, metric, alternatives, 'quarterly', i)
        if data:
            date = datetime.strptime(data['end_date'], '%Y-%m-%d')
            quarter = (date.month - 1) // 3 + 1
            value = data['value']
            all_data.append((date, quarter, value, data['end_date']))
    
    # Sort by date, newest first
    all_data.sort(reverse=True, key=lambda x: x[0])
    
    # Find matching Q3 YTD and annual pairs
    for i, (date, quarter, value, end_date) in enumerate(all_data):
        if quarter == 4:  # This is an annual total
            annual_total = value
            annual_date = end_date
            annual_year = date.year
            # Look for corresponding Q3 YTD
            for q3_date, q3_quarter, q3_value, q3_end_date in all_data:
                if q3_quarter == 3 and q3_date.year == date.year:  # This is Q3 YTD
                    # Calculate Q4 value
                    q4_value = annual_total - q3_value
                    
                    # Create Q4 start date (day after Q3 end)
                    q3_end = datetime.strptime(q3_end_date, '%Y-%m-%d')
                    q4_start = (q3_end + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
                    
                    # Create dictionary matching SEC API structure
                    return {
                        'start': q4_start,
                        'end': annual_date,
                        'val': q4_value,
                        'fp': 'Q4',
                        'fy': annual_year,
                        'form': '10-K',
                        'filed': None  # We don't have the filing date
                    }
    
    return None

def show_income_statement(fetcher, ticker, quarter_offset):
    """Display income statement for a specific quarter"""
    # Get revenue data
    revenue_data = fetcher.get_financial_data_for_period(ticker, 'RevenueFromContractWithCustomerExcludingAssessedTax', 'quarterly', quarter_offset)
    
    # If this is Q4 data (based on date), try to calculate it
    if revenue_data:
        date = datetime.strptime(revenue_data['end_date'], '%Y-%m-%d')
        quarter = (date.month - 1) // 3 + 1
        if quarter == 4:  # This is annual data
            q4_data = find_q4_data(fetcher, ticker, 'RevenueFromContractWithCustomerExcludingAssessedTax')
            if q4_data:
                revenue_data = {'value': q4_data['val'], 'end_date': q4_data['end']}
    
    if revenue_data:
        period_end = revenue_data['end_date']
        revenue = revenue_data['value']
        
        print(f"\nQuarterly Income Statement for {get_quarter_name(period_end)} (ending {period_end})")
        print("-" * 80)
        
        # Revenue
        print(f"{'Revenue':40} {format_value_with_scale(revenue):>12}")
        
        # Cost of Revenue & Gross Profit
        cost_of_revenue_data = get_metric_with_alternatives(
            fetcher, ticker, 'CostOfRevenue',
            ['CostOfGoodsAndServicesSold', 'CostOfGoodsAndServiceExcludingDepreciationDepletionAndAmortization'],
            'quarterly', quarter_offset
        )
        
        # If this is Q4, calculate the quarterly value
        if cost_of_revenue_data:
            date = datetime.strptime(cost_of_revenue_data['end_date'], '%Y-%m-%d')
            quarter = (date.month - 1) // 3 + 1
            if quarter == 4:  # This is annual data
                q4_data = find_q4_data(fetcher, ticker, 'CostOfRevenue', 
                    ['CostOfGoodsAndServicesSold', 'CostOfGoodsAndServiceExcludingDepreciationDepletionAndAmortization'])
                if q4_data:
                    cost_of_revenue_data = {'value': q4_data['val'], 'end_date': q4_data['end']}
        
        if cost_of_revenue_data:
            cost_of_revenue = cost_of_revenue_data['value']
            print(f"{'Cost of Revenue':40} {format_value_with_scale(cost_of_revenue):>12}")
            
            # Calculate gross profit
            gross_profit = revenue - cost_of_revenue
            gross_margin = (gross_profit / revenue) * 100
            print(f"\n{'Gross Profit':40} {format_value_with_scale(gross_profit):>12}")
            print(f"{'Gross Margin':40} {format_percent(gross_margin):>12}")
        
        # Operating Expenses
        operating_expenses_data = get_metric_with_alternatives(
            fetcher, ticker, 'OperatingExpenses',
            ['OperatingCostsAndExpenses'],
            'quarterly', quarter_offset
        )
        
        # If this is Q4, calculate the quarterly value
        if operating_expenses_data:
            date = datetime.strptime(operating_expenses_data['end_date'], '%Y-%m-%d')
            quarter = (date.month - 1) // 3 + 1
            if quarter == 4:  # This is annual data
                q4_data = find_q4_data(fetcher, ticker, 'OperatingExpenses', ['OperatingCostsAndExpenses'])
                if q4_data:
                    operating_expenses_data = {'value': q4_data['val'], 'end_date': q4_data['end']}
        
        if operating_expenses_data:
            print(f"\n{'Operating Expenses':40} {format_value_with_scale(operating_expenses_data['value']):>12}")
        
        # Operating Income
        operating_income_data = get_metric_with_alternatives(
            fetcher, ticker, 'OperatingIncomeLoss',
            ['OperatingIncome', 'IncomeLossFromOperations'],
            'quarterly', quarter_offset
        )
        
        # If this is Q4, calculate the quarterly value
        if operating_income_data:
            date = datetime.strptime(operating_income_data['end_date'], '%Y-%m-%d')
            quarter = (date.month - 1) // 3 + 1
            if quarter == 4:  # This is annual data
                q4_data = find_q4_data(fetcher, ticker, 'OperatingIncomeLoss', 
                    ['OperatingIncome', 'IncomeLossFromOperations'])
                if q4_data:
                    operating_income_data = {'value': q4_data['val'], 'end_date': q4_data['end']}
        
        if operating_income_data:
            operating_income = operating_income_data['value']
            operating_margin = (operating_income / revenue) * 100
            print(f"\n{'Operating Income':40} {format_value_with_scale(operating_income):>12}")
            print(f"{'Operating Margin':40} {format_percent(operating_margin):>12}")
        
        # Net Income
        net_income_data = fetcher.get_financial_data_for_period(ticker, 'NetIncomeLoss', 'quarterly', quarter_offset)
        
        # If this is Q4, calculate the quarterly value
        if net_income_data:
            date = datetime.strptime(net_income_data['end_date'], '%Y-%m-%d')
            quarter = (date.month - 1) // 3 + 1
            if quarter == 4:  # This is annual data
                q4_data = find_q4_data(fetcher, ticker, 'NetIncomeLoss')
                if q4_data:
                    net_income_data = {'value': q4_data['val'], 'end_date': q4_data['end']}
        
        if net_income_data:
            net_income = net_income_data['value']
            net_margin = (net_income / revenue) * 100
            print(f"\n{'Net Income':40} {format_value_with_scale(net_income):>12}")
            print(f"{'Net Margin':40} {format_percent(net_margin):>12}")
        
    else:
        print("Could not fetch revenue data for the specified quarter")

def is_quarterly_data(data):
    """
    Determine if this is a 3-month period by checking:
    1. Has both start and end dates
    2. Is a 10-Q filing
    3. Start and end dates are ~3 months apart
    """
    if 'start' not in data or 'end' not in data:
        return False
        
    start_date = datetime.strptime(data['start'], '%Y-%m-%d')
    end_date = datetime.strptime(data['end'], '%Y-%m-%d')
    duration = (end_date - start_date).days
    
    # Check if duration is roughly 3 months (90 ± 10 days)
    is_quarterly_duration = 80 <= duration <= 100
    
    # For Q1 data, check fiscal period indicator
    is_q1 = data.get('fp') == 'Q1'
    
    # For other quarters, make sure we're getting the 3-month period, not YTD
    if not is_q1 and not is_quarterly_duration:
        return False
    
    # Make sure start date is at beginning of quarter
    quarter_start = (start_date.month - 1) // 3 * 3 + 1
    is_quarter_start = start_date.month == quarter_start and start_date.day == 1
    
    return is_quarter_start or is_q1

def get_period_data(fetcher, ticker, metric, alternatives=[]):
    """Get all period data for a metric"""
    company_info = fetcher.get_company_info(ticker)
    if not company_info:
        return []
        
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{company_info['cik']}.json"
    fetcher._rate_limit_request()
    response = requests.get(url, headers=fetcher.headers)
    
    if not response.ok:
        return []
    
    try:
        data = response.json()
    except json.JSONDecodeError:
        return []
    
    # Try each metric name
    metrics_to_try = [metric] + alternatives
    
    for metric_name in metrics_to_try:
        if 'facts' in data and 'us-gaap' in data['facts'] and metric_name in data['facts']['us-gaap']:
            metric_data = data['facts']['us-gaap'][metric_name]
            values = metric_data['units'].get('USD', [])
            if values:
                return values
    
    return []

def get_quarterly_data(ticker):
    # Configure pandas display options
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_rows', None)
    pd.set_option('display.expand_frame_repr', False)
    
    fetcher = SECFilingFetcher()
    
    metrics = {
        'Revenue': ('RevenueFromContractWithCustomerExcludingAssessedTax', 
                   ['RevenueFromContractWithCustomerIncludingAssessedTax', 'Revenues', 'SalesRevenueNet']),
        'Cost of Revenue': ('CostOfRevenue', ['CostOfGoodsAndServicesSold', 'CostOfGoodsAndServiceExcludingDepreciationDepletionAndAmortization', 'CostOfGoodsSold']),
        'Research and Development': ('ResearchAndDevelopmentExpense', []),
        'Selling and Marketing': ('SellingAndMarketingExpense', ['SellingGeneralAndAdministrativeExpense']),
        'General and Administrative': ('GeneralAndAdministrativeExpense', []),
        'Operating Income': ('OperatingIncomeLoss', ['OperatingIncome']),
        'Other Income/Expense': ('OtherNonoperatingIncomeExpense', []),
        'Interest Income': ('InterestAndDividendIncome', ['InvestmentIncomeInterest']),
        'Interest Expense': ('InterestExpense', []),
        'Income Tax': ('IncomeTaxExpenseBenefit', []),
        'Net Income': ('NetIncomeLoss', [])
    }
    
    # Get data for each metric
    data = {}
    end_dates = {}
    fiscal_info = {}
    
    for metric_name, (tag, alternatives) in metrics.items():
        raw_values = get_period_data(fetcher, ticker, tag, alternatives)
        if raw_values:
            # First pass: collect annual totals and Q3 YTD data
            annual_data = {}  # year -> value
            q3_ytd_data = {}  # year -> value
            
            for value in raw_values:
                if ('start' in value and 'end' in value and 
                    'fp' in value and 'fy' in value and 'val' in value):
                    
                    start_date = datetime.strptime(value['start'], '%Y-%m-%d')
                    end_date = datetime.strptime(value['end'], '%Y-%m-%d')
                    duration = (end_date - start_date).days
                    
                    # Store annual totals
                    if value['fp'] == 'FY':
                        annual_data[value['fy']] = {
                            'val': value['val'],
                            'end': value['end']
                        }
                    
                    # Store Q3 YTD (9-month) data
                    if value['fp'] == 'Q3' and duration > 100:
                        q3_ytd_data[value['fy']] = {
                            'val': value['val'],
                            'end': value['end']
                        }
                    
                    # Process regular 3-month periods (Q1-Q3)
                    if 80 <= duration <= 100:
                        # Get quarter number from fiscal period
                        if value['fp'].startswith('Q'):
                            quarter = int(value['fp'][1])
                            period_key = f"Q{quarter} {value['fy']}"
                            if period_key not in data:
                                data[period_key] = {}
                                end_dates[period_key] = value['end']
                                fiscal_info[period_key] = (int(value['fy']), quarter)
                            data[period_key][metric_name] = value['val']
            
            # Calculate and add Q4 data
            for year in annual_data:
                if year in q3_ytd_data:
                    # Calculate Q4 value
                    q4_value = annual_data[year]['val'] - q3_ytd_data[year]['val']
                    period_key = f"Q4 {year}"
                    
                    if period_key not in data:
                        data[period_key] = {}
                        end_dates[period_key] = annual_data[year]['end']
                        fiscal_info[period_key] = (int(year), 4)
                    data[period_key][metric_name] = q4_value
    
    # Create DataFrame
    df = pd.DataFrame.from_dict(data, orient='index')
    
    # Add period end date as first column
    df['Period End Date'] = pd.Series(end_dates)
    
    # Move Period End Date to first column
    cols = ['Period End Date'] + [col for col in df.columns if col != 'Period End Date']
    df = df[cols]
    
    # Sort by fiscal year and quarter (descending)
    df = df.reindex(sorted(df.index, key=lambda x: fiscal_info[x], reverse=True))
    
    return df

# Get and display data
if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else None
    if ticker:
        df = get_quarterly_data(ticker)
        print(df) 