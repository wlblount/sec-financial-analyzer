import os
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import time
from typing import Dict, List, Optional
import re
from collections import OrderedDict

# Define common financial concepts with descriptions
FINANCIAL_CONCEPTS = {
    'income_statement': OrderedDict({
        'Revenues': 'Total revenue',
        'RevenueFromContractWithCustomerExcludingAssessedTax': 'Revenue from customer contracts',      
        'SalesRevenueNet': 'Net sales revenue',
        'CostOfRevenue': 'Cost of goods/services sold',
        'GrossProfit': 'Gross profit (Revenue - Cost of Revenue)',
        'ResearchAndDevelopmentExpense': 'R&D expenses',
        'SellingGeneralAndAdministrativeExpense': 'SG&A expenses',
        'SellingAndMarketingExpense': 'Sales and marketing expenses',
        'GeneralAndAdministrativeExpense': 'G&A expenses',
        'OperatingExpenses': 'Total operating expenses',
        'OperatingIncomeLoss': 'Operating income/loss',
        'InterestExpense': 'Interest expense',
        'NetIncomeLoss': 'Net income/loss',
    }),
    'balance_sheet': OrderedDict({
        'Assets': 'Total assets',
        'AssetsCurrent': 'Current assets',
        'CashAndCashEquivalentsAtCarryingValue': 'Cash and equivalents',
        'AccountsReceivableNetCurrent': 'Accounts receivable',
        'InventoryNet': 'Net inventory',
        'Liabilities': 'Total liabilities',
        'LiabilitiesCurrent': 'Current liabilities',
        'AccountsPayableCurrent': 'Accounts payable',
        'StockholdersEquity': 'Stockholders equity'
    }),
    'cash_flow': OrderedDict({
        'NetCashProvidedByUsedInOperatingActivities': 'Net cash from operations',
        'NetCashProvidedByUsedInInvestingActivities': 'Net cash from investing',
        'NetCashProvidedByUsedInFinancingActivities': 'Net cash from financing',
    })
}

class SECFilingFetcher:
    def __init__(self, email: str = "email@yahoo.com"):
        self.base_url = "https://www.sec.gov"
        self.edgar_url = "https://www.sec.gov/edgar"
        self.submissions_url = "https://data.sec.gov/submissions"

        logging.basicConfig(level=logging.INFO,
                          format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        self.headers = {
            'User-Agent': f'Company Financial Analysis Tool (Python) {email}',
            'Accept': 'application/json',
            'Host': 'data.sec.gov'
        }

        self.request_delay = 0.1
        self.last_request_time = 0

    def _rate_limit_request(self):
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.request_delay:
            time.sleep(self.request_delay - time_since_last_request)
        self.last_request_time = time.time()

    def get_company_info(self, ticker: str) -> Optional[Dict]:
        """Get company info from SEC using ticker symbol."""
        self._rate_limit_request()
        url = "https://www.sec.gov/files/company_tickers.json"
        
        try:
            # Use different headers for www.sec.gov
            headers = {
                'User-Agent': self.headers['User-Agent'],
                'Accept': 'application/json'
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            companies = response.json()
            
            # Find the company by ticker (case-insensitive)
            ticker = ticker.upper()
            for _, company in companies.items():
                if company['ticker'].upper() == ticker:
                    return {
                        'name': company['title'],
                        'cik': str(company['cik_str']).zfill(10)
                    }
            
            self.logger.error(f"Could not find company info for ticker {ticker}")
            return None
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching company info: {e}")
            return None

    def get_financial_tables(self, company_info: Dict) -> Optional[Dict]:
        """Get financial tables from SEC filings."""
        if not company_info or 'cik' not in company_info:
            return None

        try:
            # Get all company facts at once
            url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{company_info['cik']}.json"
            
            self._rate_limit_request()
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            # Get all available concepts
            us_gaap_facts = data.get('facts', {}).get('us-gaap', {})
            if not us_gaap_facts:
                self.logger.error("No US GAAP facts found")
                return None

            # Process each statement type
            financial_data = {}
            for statement_type, concepts in FINANCIAL_CONCEPTS.items():
                all_periods_data = []
                
                # Get data for each concept
                for concept, description in concepts.items():
                    if concept in us_gaap_facts:
                        fact_data = us_gaap_facts[concept]
                        if 'units' in fact_data:
                            values = fact_data['units'].get('USD', [])
                            if not values and 'shares' in fact_data.get('units', {}):
                                values = fact_data['units'].get('shares', [])
                            
                            if values:
                                # Sort by end date to get most recent periods
                                values.sort(key=lambda x: x['end'], reverse=True)
                                
                                # Get the most recent 10-K data
                                annual_data = next((v for v in values if v.get('form') == '10-K'), None)
                                
                                if annual_data:
                                    all_periods_data.append({
                                        'Concept': concept,
                                        'Description': description,
                                        'Value': annual_data['val'],
                                        'Period': annual_data['end'],
                                        'Filed': annual_data.get('filed', 'Unknown'),
                                        'Form': annual_data.get('form', 'Unknown')
                                    })
                    else:
                        self.logger.info(f"Concept {concept} not found in company facts")
                
                if all_periods_data:
                    # Create DataFrame
                    df = pd.DataFrame(all_periods_data)
                    
                    # Format the data
                    df.set_index(['Concept', 'Description'], inplace=True)
                    df = df[['Value']]  # Keep only the value column
                    
                    # Convert to millions (except for share counts and per share values)
                    for idx in df.index:
                        if not any(term in idx[0] for term in ['SharesOutstanding', 'PerShare']):
                            df.loc[idx, 'Value'] = df.loc[idx, 'Value'] / 1_000_000
                    
                    financial_data[statement_type] = df
            
            return financial_data

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching financial tables: {str(e)}")
            return None

    def get_financial_data_for_period(self, ticker: str, metric: str, period_type: str = 'annual', period_offset: int = 0) -> dict:
        """
        Fetch financial data for a specific period.
        
        Args:
            ticker (str): Company ticker symbol
            metric (str): Financial metric to fetch (e.g., 'Revenues', 'NetIncomeLoss')
            period_type (str): 'annual' for 10-K or 'quarterly' for 10-Q
            period_offset (int): How many periods back to go (0 = most recent, 1 = previous period, etc.)
            
        Returns:
            dict: Financial data including value, period end date, and filing date
        """
        company_info = self.get_company_info(ticker)
        if not company_info:
            return None
            
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{company_info['cik']}.json"
        self._rate_limit_request()
        response = requests.get(url, headers=self.headers)
        data = response.json()
        
        us_gaap_facts = data.get('facts', {}).get('us-gaap', {})
        
        # For revenue metrics, try alternative tags
        if metric == 'Revenues':
            revenue_tags = [
                'RevenueFromContractWithCustomerExcludingAssessedTax',  # Prioritize this tag
                'SalesRevenueNet',
                'Revenues'
            ]
            
            for tag in revenue_tags:
                if tag in us_gaap_facts:
                    values = us_gaap_facts[tag]['units'].get('USD', [])
                    if values:
                        # Sort by end date
                        values.sort(key=lambda x: x['end'], reverse=True)
                        
                        # Filter by form type
                        form_type = '10-K' if period_type.lower() == 'annual' else '10-Q'
                        filtered_values = [v for v in values if v.get('form') == form_type]
                        
                        if filtered_values and period_offset < len(filtered_values):
                            selected_period = filtered_values[period_offset]
                            return {
                                'value': selected_period['val'],
                                'end_date': selected_period['end'],
                                'filing_date': selected_period.get('filed', 'N/A'),
                                'form': form_type,
                                'concept_used': tag  # Add this to show which tag was used
                            }
            return None
        
        # For non-revenue metrics, use original logic
        if metric not in us_gaap_facts:
            return None
            
        values = us_gaap_facts[metric]['units'].get('USD', [])
        if not values:
            return None
            
        # Sort by end date
        values.sort(key=lambda x: x['end'], reverse=True)
        
        # Filter by form type
        form_type = '10-K' if period_type.lower() == 'annual' else '10-Q'
        filtered_values = [v for v in values if v.get('form') == form_type]
        
        if not filtered_values or period_offset >= len(filtered_values):
            return None
            
        selected_period = filtered_values[period_offset]
        return {
            'value': selected_period['val'],
            'end_date': selected_period['end'],
            'filing_date': selected_period.get('filed', 'N/A'),
            'form': form_type,
            'concept_used': metric
        }

def main():
    """Example usage of the SECFilingFetcher."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch financial data from SEC EDGAR')
    parser.add_argument('ticker', help='Stock ticker symbol')
    parser.add_argument('--email', default='email@yahoo.com', help='Email for SEC API authentication')
    args = parser.parse_args()
    
    fetcher = SECFilingFetcher(email=args.email)
    print(f"\nFetching company info for {args.ticker}...")
    
    company_info = fetcher.get_company_info(args.ticker)
    if company_info:
        print(f"\nFound company: {company_info['name']} (CIK: {company_info['cik']})")
        print("\nFetching financial data...")
        
        tables = fetcher.get_financial_tables(company_info)
        if tables:
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
            pd.set_option('display.max_rows', None)
            pd.set_option('display.float_format', lambda x: '{:,.2f}'.format(x) if pd.notnull(x) else 'NaN')
            
            for table_type, df in tables.items():
                print(f"\n{table_type.replace('_', ' ').title()} (in millions USD, except per share amounts):")
                print("=" * 120)
                print(df)
                print("\n")
        else:
            print("\nNo financial data found")
    else:
        print(f"\nCould not find company info for {args.ticker}")

if __name__ == "__main__":
    main() 