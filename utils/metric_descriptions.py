"""
Standardized descriptions for financial metrics
"""

METRIC_DESCRIPTIONS = {
    # Company Information
    'Sector': 'Industry sector classification',
    
    # Valuation Metrics
    'Market Cap': 'Total market value of outstanding shares',
    'Enterprise Value': 'Market Cap + Total Debt - Cash and Equivalents',
    'EV/EBITDA': 'Enterprise Value divided by EBITDA (valuation multiple)',
    'EV/Revenue': 'Enterprise Value divided by Revenue (valuation multiple)',
    
    # Financial Performance
    'Net Margin': 'Net Income as a percentage of Revenue (measures profitability)',
    'Operating Income': 'Revenue minus operating expenses (quarterly)',
    'Revenue': 'Total sales/income from business operations (quarterly)',
    
    # Share Information
    'Weighted Shares': 'Time-weighted average of outstanding shares',
    'Float': 'Number of shares available for public trading',
    
    # Company Size
    'Employees': 'Total number of full-time employees',
    
    # Additional Metrics (for future use)
    'Operating Margin': 'Operating Income divided by Revenue',
    'Gross Margin': 'Gross Profit divided by Revenue',
    'ROE': 'Return on Equity - Net Income divided by Shareholders Equity',
    'ROA': 'Return on Assets - Net Income divided by Total Assets',
    'Current Ratio': 'Current Assets divided by Current Liabilities',
    'Debt/Equity': 'Total Debt divided by Shareholders Equity',
    'Asset Turnover': 'Revenue divided by Average Total Assets'
} 