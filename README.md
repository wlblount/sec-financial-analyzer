# SEC Financial Data Analyzer

A Python tool to fetch and analyze quarterly financial data from the SEC's EDGAR database. This tool retrieves raw financial metrics and calculates derived values, with special handling for Q4 data.

## Features

- Direct access to SEC EDGAR API
- Retrieval of quarterly financial metrics (Revenue, Income, etc.)
- Automatic calculation of Q4 data from annual and Q3 YTD values
- Support for both command line and Jupyter notebook usage
- Handles multiple financial metrics with alternative tags

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/sec_analyzer_clean.git
cd sec_analyzer_clean
```

2. Install required packages:
```bash
pip install pandas requests
```

## Usage

### Command Line
```bash
python analyze.py TICKER
```
Example:
```bash
python analyze.py AAPL
```

### Jupyter Notebook
```python
from sec_filing_fetcher import SECFilingFetcher
from test_income_statement import get_quarterly_data

# Get quarterly data for a company
df = get_quarterly_data('AAPL')
print(df)
```

## File Structure

- `sec_filing_fetcher.py`: Handles communication with SEC EDGAR API
- `test_income_statement.py`: Contains data processing logic and financial calculations
- `analyze.py`: Command line interface

## Data Processing

The tool processes financial data in the following way:
1. Retrieves raw quarterly data from SEC API
2. Identifies and processes 3-month periods (Q1-Q3)
3. Calculates Q4 values by subtracting Q3 YTD from annual totals
4. Organizes data into a pandas DataFrame with proper fiscal periods

## Available Metrics

- Revenue
- Cost of Revenue
- Research and Development
- Selling and Marketing
- General and Administrative
- Operating Income
- Other Income/Expense
- Interest Income
- Interest Expense
- Income Tax
- Net Income

## Notes

- Q4 data is calculated by subtracting Q3 YTD from annual totals
- The tool automatically handles different GAAP taxonomy tags
- All values are returned in their original units from SEC filings

## Requirements

- Python 3.6+
- pandas
- requests

## License

[Your chosen license] 