# EdgarTools Library Capabilities

**Comprehensive analysis of edgartools features for MCP integration**

**Last Updated**: 2025-11-21
**Source Repository**: https://github.com/dgunning/edgartools
**Forked Version**: /home/ubuntu/idio/forked-edgartools

---

## Executive Summary

EdgarTools is a powerful Python library for accessing and analyzing SEC EDGAR filings. It provides three core capabilities that are highly valuable for investment analysis:

1. **Financial Statement Analysis** - Access to structured XBRL financial statements (income/balance/cash flow) with multi-period comparison
2. **Institutional Holdings (13F)** - Quarterly portfolio holdings for institutional investors with >$100M AUM
3. **Insider Trading (Forms 3/4/5)** - Real-time insider transactions with structured buy/sell data

The library excels at **data extraction and structure**, providing clean DataFrames and domain objects from raw SEC filings. It supports both modern XBRL filings (2009+) and legacy text formats, with intelligent parsing and caching.

**Key Strengths**:
- **Comprehensive**: Covers all major SEC form types (10-K/Q, 8-K, 13F, Forms 3/4/5, S-1, DEF 14A, N-PORT, etc.)
- **Structured Data**: Converts XML/HTML/text into pandas DataFrames and Python objects
- **Multi-Period**: Built-in support for time-series analysis (3-year trends, YoY comparison)
- **Query Interface**: Sophisticated fact querying for custom analysis
- **Performance**: Intelligent caching, rate limiting, and batch processing support

**Limitations**:
- Requires pyarrow dependency (not installed in forked version)
- Some features require SEC identity setup
- Performance can be slow for large batch operations
- XBRL parsing complexity can cause edge cases

---

## Core Capabilities

### 1. Financial Statement Analysis

**Priority**: HIGH - Core use case for investment analysis

#### What It Does

Provides access to structured financial statements (income statement, balance sheet, cash flow) from SEC filings via two approaches:

1. **Entity Facts API** (Recommended) - Fast, multi-period, pre-aggregated data from SEC's companyfacts endpoint
2. **XBRL Filing Parsing** - Detailed, single-filing analysis with full line-item access

#### Code Examples

**Multi-Period Financial Statements (Entity Facts API)**:
```python
from edgar import set_identity, Company

# Required: Set SEC identity
set_identity("Your Name your@email.com")

# Get company
company = Company("AAPL")

# Multi-period statements (single API call)
income = company.income_statement(periods=3)  # Last 3 fiscal years
balance = company.balance_sheet(periods=3)
cash_flow = company.cash_flow_statement(periods=3)

# Quarterly data
quarterly_income = company.income_statement(periods=4, annual=False)

print(income)  # Displays rich table with 3 years of data
```

**Single-Period Detailed Analysis (XBRL)**:
```python
# Get specific filing
filing = company.get_filings(form="10-K")[0]

# Parse XBRL
xbrl = filing.xbrl()

# Access statements
statements = xbrl.statements
income = statements.income_statement()
balance = statements.balance_sheet()
cash_flow = statements.cash_flow_statement()

# Convert to DataFrame for analysis
df = income.to_dataframe()
print(df)
```

**Custom Fact Queries (Advanced)**:
```python
# Query specific metrics across periods
facts = xbrl.facts
revenue_df = facts.query().by_concept("Revenue").to_dataframe()
rd_spending = facts.query().by_concept("ResearchAndDevelopment").to_dataframe()

# Filter by fiscal period
q2_facts = facts.query().by_period_key("duration_2024-04-01_2024-06-30").to_dataframe()

# Income statement facts only
income_facts = facts.query().by_statement_type("IncomeStatement").to_dataframe()
```

#### Data Structures

**MultiPeriodStatement** (from Entity Facts API):
```python
# Attributes
.name            # str: Company name
.statement_type  # str: "IncomeStatement", "BalanceSheet", "CashFlowStatement"
.periods         # List[str]: Period labels ["FY 2023", "FY 2022", "FY 2021"]
.data            # DataFrame: Rows=line items, Columns=periods

# Methods
.to_dataframe()  # Export to pandas DataFrame
.get_value(concept, period)  # Get specific value
```

**Statement** (from XBRL):
```python
# Attributes
.title           # str: Statement title
.company         # str: Company name
.period          # str: Period label
.data            # List[LineItem]: Structured line items

# Methods
.to_dataframe()  # Export to pandas DataFrame
.find_item(name) # Find specific line item
```

**XBRL Facts**:
```python
# FactQuery interface
facts = xbrl.facts
query = facts.query()

# Chained filtering
df = (query
      .by_concept("Revenue")
      .by_fiscal_year(2024)
      .by_statement_type("IncomeStatement")
      .to_dataframe())

# Resulting DataFrame columns:
# - concept: XBRL concept name (e.g., "us-gaap:Revenues")
# - label: Human-readable label (e.g., "Total Net Revenues")
# - value: Display value (e.g., "$383,285,000,000")
# - numeric_value: Numeric value (e.g., 383285000000)
# - unit: Unit (e.g., "USD")
# - period_type: "instant" or "duration"
# - period_start: datetime
# - period_end: datetime
# - fiscal_year: int
# - fiscal_period: str ("FY", "Q1", "Q2", "Q3", "Q4")
```

#### Use Cases for Investment Analysis

1. **Revenue Trend Analysis** - Track revenue growth over multiple periods
2. **Margin Analysis** - Calculate gross margin, operating margin, net margin trends
3. **Balance Sheet Health** - Debt ratios, current ratio, working capital trends
4. **Cash Flow Analysis** - Operating cash flow, free cash flow, capital expenditure trends
5. **Cross-Company Comparison** - Compare metrics across multiple companies
6. **Quarterly Momentum** - Sequential quarterly growth rates
7. **Earnings Quality** - Cash flow vs earnings comparison

#### Potential MCP Tool Design

**Tool 1: `get_financial_statements`**
```python
{
  "ticker": "AAPL",
  "statement_type": "income",  # "income", "balance", "cashflow"
  "periods": 3,
  "annual": true,
  "format": "dataframe"  # "dataframe", "json", "markdown"
}
# Returns: Structured statement with 3 years of data
```

**Tool 2: `query_financial_facts`**
```python
{
  "ticker": "AAPL",
  "concepts": ["Revenue", "NetIncome"],
  "fiscal_years": [2023, 2022, 2021],
  "include_quarterly": false
}
# Returns: Specific facts across periods
```

**Tool 3: `compare_companies_financials`**
```python
{
  "tickers": ["AAPL", "MSFT", "GOOGL"],
  "metrics": ["Revenue", "NetIncome", "OperatingIncome"],
  "periods": 3
}
# Returns: Side-by-side comparison table
```

---

### 2. Institutional Holdings (13F Filings)

**Priority**: HIGH - Essential for tracking "smart money"

#### What It Does

Extracts quarterly portfolio holdings from 13F-HR filings (institutional investors with >$100M AUM). Provides detailed holdings including security name, CUSIP, shares, value, and percentage of portfolio.

#### Code Examples

**Basic 13F Access**:
```python
from edgar import Company

# Get institutional investor
berkshire = Company("BRK-A")

# Get latest 13F filing
filings_13f = berkshire.get_filings(form="13F-HR")
latest = filings_13f[0]

print(f"Filing date: {latest.filing_date}")
print(f"Period: {latest.period_of_report}")

# Parse 13F
thirteenf = latest.obj()

# Summary info
print(f"Manager: {thirteenf.management_company_name}")
print(f"Total holdings: {thirteenf.total_holdings}")
print(f"Total value: ${thirteenf.total_value:,}")
print(f"Report period: {thirteenf.report_period}")
```

**Holdings Analysis**:
```python
# Get holdings table as DataFrame
if thirteenf.has_infotable():
    holdings = thirteenf.infotable

    # DataFrame columns:
    # - nameOfIssuer: Company name
    # - titleOfClass: Security type (Common Stock, etc.)
    # - cusip: CUSIP identifier
    # - value: Value in thousands of dollars
    # - sshPrnamt: Number of shares
    # - sshPrnamtType: Share type (SH, PRN)
    # - investmentDiscretion: Sole, Shared, None
    # - votingAuthority: Sole/Shared/None counts

    print(holdings.head(10))  # Top 10 holdings

    # Analysis
    top_10 = holdings.head(10)
    print(f"Top 10 holdings represent: ${top_10['value'].sum():,}K")

    # Find specific holdings
    apple_holdings = holdings[holdings['nameOfIssuer'].str.contains('APPLE', case=False)]
    if not apple_holdings.empty:
        shares = apple_holdings.iloc[0]['sshPrnamt']
        value = apple_holdings.iloc[0]['value']
        print(f"Apple: {shares:,} shares, ${value:,}K value")
```

**Historical Analysis**:
```python
# Compare across quarters
filings_13f = berkshire.get_filings(form="13F-HR")

holdings_history = []
for filing in filings_13f[:4]:  # Last 4 quarters
    tf = filing.obj()
    if tf.has_infotable():
        holdings = tf.infotable
        holdings_history.append({
            'period': tf.report_period,
            'total_value': tf.total_value,
            'num_holdings': len(holdings),
            'holdings': holdings
        })

# Track position changes
for i, data in enumerate(holdings_history[:-1]):
    curr = data['holdings']
    prev = holdings_history[i+1]['holdings']

    # Find new positions
    new_cusips = set(curr['cusip']) - set(prev['cusip'])
    print(f"New positions in {data['period']}: {len(new_cusips)}")

    # Find increased positions
    # ... (can compare share counts)
```

**Ticker Resolution**:
```python
from edgar.reference import cusip_ticker_mapping

# Get CUSIP to ticker mapping
cusip_map = cusip_ticker_mapping(allow_duplicate_cusips=False)

# Add tickers to holdings
holdings['ticker'] = holdings['cusip'].map(cusip_map.set_index('CUSIP')['Ticker'])

# Now you can filter by ticker
holdings_with_tickers = holdings[holdings['ticker'].notna()]
print(holdings_with_tickers[['ticker', 'nameOfIssuer', 'value', 'sshPrnamt']])
```

#### Data Structures

**ThirteenF Object**:
```python
# Properties
.management_company_name  # str: Legal entity name
.filing_signer_name       # str: Person who signed
.report_period            # str: Period end date (YYYY-MM-DD)
.filing_date              # str: Filing date
.total_holdings           # int: Number of positions
.total_value              # Decimal: Total value in $1000s
.has_infotable()          # bool: Has holdings data

# Holdings table
.infotable                # DataFrame: Holdings details

# Filing metadata
.form                     # str: "13F-HR" or "13F-NT"
.accession_number         # str: SEC accession number
```

**Holdings DataFrame Columns**:
- `nameOfIssuer`: Company name
- `titleOfClass`: Security type (Common Stock, Preferred, etc.)
- `cusip`: CUSIP identifier
- `value`: Value in thousands of dollars
- `sshPrnamt`: Number of shares/principal amount
- `sshPrnamtType`: "SH" (shares) or "PRN" (principal)
- `investmentDiscretion`: "SOLE", "SHARED", or "NONE"
- `votingAuthority`: Object with sole/shared/none vote counts
- `ticker`: (if added) Stock ticker symbol

#### Use Cases for Investment Analysis

1. **Smart Money Tracking** - See what legendary investors (Buffett, Ackman, Burry) are buying/selling
2. **Position Sizing** - How much conviction does an investor have (% of portfolio)
3. **New Positions** - Identify newly initiated positions
4. **Exit Signals** - Detect when positions are sold completely
5. **Concentration Analysis** - Top 10 holdings, sector concentration
6. **Activist Detection** - Large new positions that might indicate activism
7. **Crowding Analysis** - See which stocks have multiple 13F filers
8. **Historical Performance** - Track past 13F filings to backtest strategies

#### Potential MCP Tool Design

**Tool 1: `get_13f_holdings`**
```python
{
  "ticker": "BRK-A",  # Institutional investor ticker
  "latest": true,      # or specific date
  "include_changes": true,  # Compare to prior period
  "format": "dataframe"
}
# Returns: Current holdings with period-over-period changes
```

**Tool 2: `search_13f_holdings`**
```python
{
  "security_ticker": "AAPL",  # Find who owns this
  "min_value": 1000000,       # Minimum position size ($K)
  "period": "2024-Q2"
}
# Returns: List of 13F filers holding AAPL
```

**Tool 3: `track_13f_changes`**
```python
{
  "ticker": "BRK-A",
  "periods": 4,  # Last 4 quarters
  "highlight": ["new", "sold", "increased", "decreased"]
}
# Returns: Position changes over time
```

---

### 3. Insider Trading (Forms 3/4/5)

**Priority**: MEDIUM-HIGH - Important for sentiment analysis

#### What It Does

Extracts insider transaction data from SEC Forms 3 (initial ownership), 4 (changes in ownership), and 5 (annual summary). Provides structured buy/sell transactions with shares, prices, dates, and insider details.

#### Code Examples

**Basic Form 4 Access**:
```python
from edgar import Company

company = Company("AAPL")

# Get Form 4 filings (insider transactions)
form4s = company.get_filings(form="4")

print(f"Total Form 4 filings: {len(form4s)}")

# Latest transaction
latest = form4s[0]
print(f"Filed: {latest.filing_date}")
print(f"Company: {latest.company}")
```

**Detailed Transaction Analysis**:
```python
# Parse Form 4
form4_obj = latest.obj()

# Insider information
print(f"Insider: {form4_obj.insider_name}")
print(f"Position: {form4_obj.position}")
print(f"Reporting period: {form4_obj.reporting_period}")

# Sales transactions (DataFrame)
if form4_obj.common_stock_sales is not None and not form4_obj.common_stock_sales.empty:
    sales = form4_obj.common_stock_sales

    # DataFrame columns:
    # - Security: Security type (e.g., "Common Stock")
    # - Date: Transaction date
    # - Shares: Number of shares
    # - Price: Price per share
    # - Remaining: Shares remaining after transaction
    # - Code: Transaction code ('S' = sale, 'P' = purchase)
    # - AcquiredDisposed: 'A' = acquired, 'D' = disposed

    for idx, sale in sales.iterrows():
        shares = sale['Shares']
        price = sale['Price']
        date = sale['Date']
        value = shares * price
        remaining = sale['Remaining']

        print(f"Sale on {date}:")
        print(f"  Shares: {shares:,}")
        print(f"  Price: ${price:.2f}")
        print(f"  Value: ${value:,.2f}")
        print(f"  Remaining: {remaining:,} shares")

# Purchase transactions (DataFrame)
if form4_obj.common_stock_purchases is not None and not form4_obj.common_stock_purchases.empty:
    purchases = form4_obj.common_stock_purchases

    for idx, purchase in purchases.iterrows():
        shares = purchase['Shares']
        price = purchase['Price']
        date = purchase['Date']
        value = shares * price

        print(f"Purchase on {date}: {shares:,} shares @ ${price:.2f} = ${value:,.2f}")
```

**Filtering Large Transactions**:
```python
from datetime import datetime, timedelta

# Get recent Form 4s (last 6 months)
start_date = datetime.now() - timedelta(days=180)
form4s = company.get_filings(form="4")
recent = form4s.filter(filing_date=f"{start_date.strftime('%Y-%m-%d')}:")

# Find large insider sales (>$1M)
large_sales = []
for filing in recent:
    form4 = filing.obj()

    if form4.common_stock_sales is not None and not form4.common_stock_sales.empty:
        for idx, sale in form4.common_stock_sales.iterrows():
            value = sale['Shares'] * sale['Price']

            if value > 1_000_000:
                large_sales.append({
                    'name': form4.insider_name,
                    'title': form4.position,
                    'date': sale['Date'],
                    'shares': sale['Shares'],
                    'price': sale['Price'],
                    'value': value,
                    'filing_date': filing.filing_date
                })

# Sort by value
large_sales.sort(key=lambda x: x['value'], reverse=True)

for sale in large_sales[:10]:  # Top 10 largest
    print(f"{sale['name']} ({sale['title']})")
    print(f"  {sale['date']}: ${sale['value']:,.2f}")
    print(f"  {sale['shares']:,} shares @ ${sale['price']:.2f}")
```

**Aggregate Analysis**:
```python
import pandas as pd

# Aggregate transactions over period
transactions = []

for filing in recent:
    form4 = filing.obj()

    # Add sales
    if form4.common_stock_sales is not None and not form4.common_stock_sales.empty:
        for idx, sale in form4.common_stock_sales.iterrows():
            transactions.append({
                'type': 'sale',
                'name': form4.insider_name,
                'title': form4.position,
                'date': sale['Date'],
                'shares': sale['Shares'],
                'price': sale['Price'],
                'value': sale['Shares'] * sale['Price']
            })

    # Add purchases
    if form4.common_stock_purchases is not None and not form4.common_stock_purchases.empty:
        for idx, purchase in form4.common_stock_purchases.iterrows():
            transactions.append({
                'type': 'purchase',
                'name': form4.insider_name,
                'title': form4.position,
                'date': purchase['Date'],
                'shares': purchase['Shares'],
                'price': purchase['Price'],
                'value': purchase['Shares'] * purchase['Price']
            })

df = pd.DataFrame(transactions)

# Summary statistics
print("Insider Activity Summary:")
print(f"Total sales: {len(df[df['type']=='sale'])} transactions, ${df[df['type']=='sale']['value'].sum():,.2f}")
print(f"Total purchases: {len(df[df['type']=='purchase'])} transactions, ${df[df['type']=='purchase']['value'].sum():,.2f}")
print(f"Net insider flow: ${(df[df['type']=='purchase']['value'].sum() - df[df['type']=='sale']['value'].sum()):,.2f}")

# By insider
insider_summary = df.groupby(['name', 'type'])['value'].sum().unstack(fill_value=0)
print(insider_summary)
```

#### Data Structures

**Form4 Object**:
```python
# Properties
.insider_name               # str: Insider's name
.position                   # str: Title/position
.reporting_period           # str: Period end date
.common_stock_sales         # DataFrame: Sale transactions
.common_stock_purchases     # DataFrame: Purchase transactions
.transactions               # List: All transaction objects

# Transaction DataFrames have columns:
# - Security: str
# - Date: datetime
# - Shares: float
# - Price: float
# - Remaining: float
# - Code: str ('S', 'P', 'M', 'G', etc.)
# - AcquiredDisposed: str ('A', 'D')
```

#### Use Cases for Investment Analysis

1. **Insider Sentiment** - Cluster of insider buying = bullish signal
2. **Material Sales** - Large insider sales (>$10M) = potential concern
3. **Exec Compensation** - Track stock-based comp and vesting schedules
4. **Director Activity** - Independent director purchases = high conviction
5. **10b5-1 Plans** - Identify programmatic vs discretionary trades
6. **Cluster Analysis** - Multiple insiders buying/selling in short window
7. **Historical Performance** - Track insider transaction predictive value

#### Potential MCP Tool Design

**Tool 1: `get_insider_transactions`**
```python
{
  "ticker": "AAPL",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "transaction_types": ["sale", "purchase"],
  "min_value": 100000,  # Filter small transactions
  "include_derivatives": false
}
# Returns: Filtered insider transactions
```

**Tool 2: `analyze_insider_sentiment`**
```python
{
  "ticker": "AAPL",
  "period_days": 180,
  "weight_by_value": true,
  "exclude_10b51": false  # Exclude automatic trades
}
# Returns: Aggregate buy/sell sentiment score
```

**Tool 3: `track_insider`**
```python
{
  "insider_name": "Timothy D. Cook",
  "companies": ["AAPL"],
  "periods": 4  # Last 4 quarters
}
# Returns: Specific insider's transaction history
```

---

### 4. Company Information & Search

**Priority**: MEDIUM - Essential supporting capability

#### What It Does

Provides comprehensive company profile information, search capabilities, and metadata access.

#### Code Examples

```python
from edgar import Company, find_company

# Get company by ticker or CIK
company = Company("AAPL")  # or Company(320193)

# Company information
print(f"Name: {company.name}")
print(f"CIK: {company.cik}")
print(f"Ticker: {company.tickers}")
print(f"SIC: {company.sic} - {company.sic_description}")
print(f"Exchange: {company.exchange}")
print(f"Category: {company.category}")
print(f"Fiscal year end: {company.fiscal_year_end}")

# Business address
print(f"Address: {company.business_address}")
print(f"Phone: {company.business_phone}")

# Search companies
results = find_company("Tesla")
for result in results:
    print(f"{result.name} - CIK: {result.cik}")

# Get as entity
entity = results[0].as_entity()
```

#### Use Cases

1. **Company Lookup** - Resolve ticker to CIK, get official name
2. **Industry Classification** - SIC code for sector analysis
3. **Filing History** - Access to all historical filings
4. **Company Metadata** - Phone, address, fiscal year end

---

### 5. Filing Discovery & Filtering

**Priority**: MEDIUM - Critical workflow support

#### What It Does

Provides powerful filing discovery, filtering, and search capabilities across all SEC form types.

#### Code Examples

**Company-Specific Filings**:
```python
from edgar import Company

company = Company("AAPL")

# Get all filings
all_filings = company.get_filings()

# Filter by form type
tenks = company.get_filings(form="10-K")
tenqs = company.get_filings(form="10-Q")
eightks = company.get_filings(form="8-K")
proxies = company.get_filings(form="DEF 14A")

# Filter by date range
recent = company.get_filings(filing_date="2024-01-01:2024-12-31")

# Filter by year
fy2023 = company.get_filings(year=2023, form="10-K")

# Get latest filing
latest_10k = company.get_filings(form="10-K")[0]
```

**Bulk Filing Discovery**:
```python
from edgar import get_filings

# Get all filings for a quarter
filings = get_filings(2024, 1)  # Q1 2024

# Filter by form type
ipos = get_filings(2024, 1, form="S-1")
tenks = get_filings(2024, 1, form="10-K")

# Filter by date range
feb_filings = filings.filter(filing_date="2024-02-01:2024-02-28")

# Filter by ticker
tech_filings = filings.filter(ticker=["AAPL", "MSFT", "GOOGL"])

# Filter by exchange
nasdaq_filings = filings.filter(exchange="NASDAQ")
```

**Current Filings (Real-time)**:
```python
from edgar import get_current_filings

# Get recent filings (last ~24 hours)
current = get_current_filings()

# Filter
recent_10ks = current.filter(form="10-K")
recent_insider = current.filter(form="4")
recent_8ks = current.filter(form="8-K")

# Company-specific
aapl_recent = current.filter(ticker="AAPL")
```

**Content Search**:
```python
# Search inside filing documents
filing = company.get_filings(form="10-K")[0]

# BM25 search for keywords
results = filing.search("artificial intelligence")
results = filing.search("revenue recognition")
results = filing.search("climate change")

# Results are ranked by relevance
for i, result in enumerate(results[:5]):
    print(f"{i+1}. Score: {result.score:.2f}")
    print(f"   {str(result)[:200]}...")
```

#### Use Cases

1. **Filing Monitoring** - Track new filings for watchlist companies
2. **Event Detection** - Detect 8-K filings (material events)
3. **Proxy Season** - Track DEF 14A filings
4. **IPO Pipeline** - Monitor S-1 filings
5. **Industry Screening** - Find all filings in a sector
6. **Research Workflows** - Content search across filings

---

### 6. XBRL Parsing & Fact Queries

**Priority**: MEDIUM - Advanced analysis capability

#### What It Does

Provides low-level XBRL parsing with sophisticated fact querying for custom analysis.

#### Code Examples

```python
# Get XBRL from filing
filing = company.get_filings(form="10-K")[0]
xbrl = filing.xbrl()

# Access facts
facts = xbrl.facts

# Build complex queries
query = facts.query()

# Filter by concept
revenue_facts = query.by_concept("Revenue").to_dataframe()
rd_facts = query.by_concept("ResearchAndDevelopment").to_dataframe()

# Filter by period
q2_facts = query.by_period_key("duration_2024-04-01_2024-06-30").to_dataframe()
annual_facts = query.by_fiscal_period("FY").to_dataframe()

# Filter by statement
income_facts = query.by_statement_type("IncomeStatement").to_dataframe()
balance_facts = query.by_statement_type("BalanceSheet").to_dataframe()

# Dimensional queries (segment data)
segment_revenue = query.by_dimension("ProductOrServiceAxis", "ProductA").to_dataframe()

# Chain multiple filters
custom_query = (facts.query()
                .by_concept("Revenue")
                .by_fiscal_year(2024)
                .by_statement_type("IncomeStatement")
                .limit(10)
                .to_dataframe())

# Access metadata
print(f"Total facts: {len(xbrl._facts)}")
print(f"Contexts: {len(xbrl.contexts)}")
print(f"Periods: {len(xbrl.reporting_periods)}")

# Available statements
for stmt in xbrl.get_all_statements():
    print(f"{stmt['type']}: {stmt['role']}")
```

#### Use Cases

1. **Custom Metrics** - Extract non-standard line items
2. **Segment Analysis** - Revenue/earnings by product/geography
3. **Detailed Breakdowns** - Access full XBRL hierarchies
4. **Data Quality** - Validate financial statement integrity
5. **Research Automation** - Programmatic access to any XBRL fact

---

### 7. Fund Holdings (N-PORT)

**Priority**: MEDIUM-LOW - Niche but valuable

#### What It Does

Parses N-PORT filings (monthly mutual fund holdings) with detailed position data including derivatives.

#### Code Examples

```python
from edgar import Company

# Get mutual fund
fund = Company("VTI")  # Vanguard Total Stock Market

# Get N-PORT filings
nports = fund.get_filings(form="NPORT-P")
latest = nports[0]

# Parse N-PORT
nport = latest.obj()

# Access holdings
holdings = nport.investments

# Holdings are detailed with:
# - Security name, CUSIP, ISIN, ticker
# - Quantity and value
# - Percentage of portfolio
# - Asset type classification
# - Derivatives (if applicable)

for holding in holdings[:10]:
    print(f"{holding.name}: ${holding.value:,.0f}")
```

#### Use Cases

1. **Fund Transparency** - See actual fund holdings
2. **Portfolio Overlap** - Compare fund holdings
3. **Derivative Exposure** - Track fund derivatives usage
4. **Active Share** - Compare fund vs benchmark

---

### 8. Document Parsing & Extraction

**Priority**: LOW-MEDIUM - Supporting capability

#### What It Does

Converts SEC HTML/XML documents to structured formats (markdown, text) with section extraction.

#### Code Examples

```python
filing = company.get_filings(form="10-K")[0]

# Get document
doc = filing.document()

# Extract sections
item1 = doc.get_section("Item 1")    # Business description
item1a = doc.get_section("Item 1A")  # Risk factors
item7 = doc.get_section("Item 7")    # MD&A

# Convert formats
markdown = filing.markdown()  # Full filing as markdown
text = filing.text()          # Plain text
html = filing.html()          # HTML

# Document structure
print(doc.sections)  # List all sections
```

#### Use Cases

1. **LLM Analysis** - Extract text for AI analysis
2. **Risk Factor Extraction** - Get Item 1A text
3. **MD&A Analysis** - Analyze management commentary
4. **Exhibit Extraction** - Access specific exhibits

---

## Priority Assessment

### HIGH Priority (Core MCP Tools)

**1. Financial Statements** (`get_financial_statements`)
- **Why**: Core data for investment analysis
- **Frequency**: Daily/weekly use
- **Value**: Multi-period trends, standardized format
- **Complexity**: Low - Entity Facts API is straightforward

**2. Institutional Holdings** (`get_13f_holdings`, `search_13f_holdings`)
- **Why**: Essential for tracking smart money
- **Frequency**: Weekly/monthly use
- **Value**: See what legendary investors are doing
- **Complexity**: Low-medium - DataFrame output is clean

**3. Insider Trading** (`get_insider_transactions`, `analyze_insider_sentiment`)
- **Why**: Important sentiment indicator
- **Frequency**: Weekly use
- **Value**: Early signal of material information
- **Complexity**: Medium - Form 4 parsing has edge cases

### MEDIUM Priority (Supporting Tools)

**4. Company Information** (`get_company_info`, `search_companies`)
- **Why**: Essential lookup capability
- **Frequency**: Daily use
- **Value**: Metadata, ticker resolution
- **Complexity**: Low

**5. Filing Discovery** (`search_filings`, `get_recent_filings`)
- **Why**: Workflow support
- **Frequency**: Daily use
- **Value**: Event detection, monitoring
- **Complexity**: Low

**6. XBRL Fact Queries** (`query_xbrl_facts`)
- **Why**: Advanced analysis
- **Frequency**: Weekly use (power users)
- **Value**: Custom metrics, segment data
- **Complexity**: High - XBRL is complex

### LOWER Priority (Specialized)

**7. Fund Holdings (N-PORT)** (`get_fund_holdings`)
- **Why**: Niche use case
- **Frequency**: Monthly use
- **Value**: Fund transparency
- **Complexity**: Medium

**8. Document Extraction** (`extract_filing_sections`)
- **Why**: LLM integration
- **Frequency**: As-needed
- **Value**: Enables text analysis
- **Complexity**: Medium

---

## Implementation Recommendations

### Phase 1: Core Financial Data (2-3 tools)

1. **`get_financial_statements`** - Multi-period income/balance/cashflow
   - Uses Entity Facts API (fast, reliable)
   - Returns structured DataFrames
   - Supports both annual and quarterly

2. **`query_financial_facts`** - Custom fact queries
   - Uses XBRL fact query interface
   - More flexible but more complex
   - For power users

3. **`compare_companies`** - Side-by-side comparison
   - Uses Entity Facts API
   - Returns comparison table
   - Essential for relative analysis

### Phase 2: Holdings & Insider Trading (3-4 tools)

4. **`get_13f_holdings`** - Institutional portfolio data
   - Latest or historical
   - Include period-over-period changes
   - Add ticker resolution

5. **`search_13f_holders`** - Find who owns a security
   - Reverse lookup by ticker/CUSIP
   - Minimum position size filter
   - Show concentration

6. **`get_insider_transactions`** - Form 3/4/5 data
   - Date range filtering
   - Transaction type filtering
   - Aggregate metrics

7. **`analyze_insider_sentiment`** - Sentiment scoring
   - Buy/sell ratio
   - Dollar-weighted
   - Exclude 10b5-1 plans

### Phase 3: Discovery & Advanced (2-3 tools)

8. **`search_filings`** - Filing discovery
   - By form type, date, ticker
   - Real-time monitoring
   - Content search

9. **`get_company_info`** - Company metadata
   - Profile information
   - Ticker/CIK resolution
   - Industry classification

10. **`query_xbrl_facts`** (Advanced) - Low-level XBRL access
    - Custom fact queries
    - Segment data
    - Dimensional analysis

---

## Technical Considerations

### Dependencies

**Required**:
- `httpx` - HTTP client
- `pandas` - Data manipulation
- `lxml` - XML parsing
- `beautifulsoup4` - HTML parsing
- `rich` - Terminal formatting
- `pydantic` - Data validation
- **`pyarrow`** - DataFrame operations (NOT currently installed in fork)

**Optional**:
- `openpyxl` - Excel export
- `matplotlib` - Charting

### Performance

**Caching**:
- Facts cached locally in `.edgar/company_facts/`
- Filings cached in `.edgar/filings/`
- 24-hour TTL for most data

**Rate Limiting**:
- SEC enforces 10 requests/second
- EdgarTools automatically throttles
- Batch operations can be slow

**Memory**:
- Large XBRL files (500MB+) can consume significant memory
- Consider streaming for batch operations
- Clear caches periodically

### Error Handling

**Common Issues**:
1. **Missing data** - Not all companies have all filings
2. **Parsing errors** - XBRL complexity causes edge cases
3. **Period mismatches** - Fiscal vs calendar years
4. **Rate limits** - SEC throttling
5. **Identity required** - Some operations need `set_identity()`

**Mitigation**:
```python
from edgar import Company, NoCompanyFactsFound

try:
    company = Company("TICKER")
    facts = company.get_facts()
except NoCompanyFactsFound:
    # Handle missing data
    return None
except Exception as e:
    # Log and handle errors
    logger.error(f"Error: {e}")
    return None
```

### MCP Integration Patterns

**Tool Design**:
```python
# Example MCP tool wrapper
@tool
def get_financial_statements(
    ticker: str,
    statement_type: str = "income",
    periods: int = 3,
    annual: bool = True
) -> dict:
    """Get financial statements for a company."""
    try:
        from edgar import set_identity, Company
        set_identity("MCP Server mcp@server.com")

        company = Company(ticker)

        if statement_type == "income":
            stmt = company.income_statement(periods=periods, annual=annual)
        elif statement_type == "balance":
            stmt = company.balance_sheet(periods=periods, annual=annual)
        elif statement_type == "cashflow":
            stmt = company.cash_flow_statement(periods=periods, annual=annual)
        else:
            return {"error": f"Unknown statement type: {statement_type}"}

        # Convert to JSON-serializable format
        return {
            "ticker": ticker,
            "company": company.name,
            "statement_type": statement_type,
            "data": stmt.to_dataframe().to_dict(orient="records")
        }
    except Exception as e:
        return {"error": str(e)}
```

**Response Format**:
- Always return structured data (dicts/lists)
- Include metadata (company name, dates, etc.)
- Handle errors gracefully
- Provide context in responses

---

## Summary & Next Steps

### What EdgarTools Does Best

1. ✅ **Structured Financial Data** - Multi-period statements from Entity Facts API
2. ✅ **Institutional Holdings** - Clean 13F parsing with holdings DataFrames
3. ✅ **Insider Transactions** - Form 4 parsing with buy/sell breakdown
4. ✅ **Company Metadata** - Comprehensive company profiles
5. ✅ **Filing Discovery** - Powerful search and filtering

### What It Lacks

1. ❌ **Real-time Market Data** - No prices, quotes, market cap (use yfinance-ux)
2. ❌ **Calculated Metrics** - No P/E, PEG, ROE calculations (raw data only)
3. ❌ **Analyst Estimates** - No consensus estimates or guidance
4. ❌ **News & Events** - No news feed or calendar
5. ❌ **Advanced Analytics** - No factor models, correlation analysis

### Recommended MCP Tools (Priority Order)

**Phase 1** (Must-have):
1. `get_financial_statements` - Income/balance/cashflow (3+ years)
2. `get_13f_holdings` - Institutional portfolio holdings
3. `get_insider_transactions` - Form 4 buy/sell data

**Phase 2** (Important):
4. `compare_companies` - Side-by-side financial comparison
5. `search_13f_holders` - Find who owns a security
6. `analyze_insider_sentiment` - Aggregate insider activity

**Phase 3** (Nice-to-have):
7. `search_filings` - Filing discovery and monitoring
8. `get_company_info` - Company profiles and metadata
9. `query_xbrl_facts` - Advanced XBRL queries

### Integration with Existing MCP Tools

**Complement yfinance-ux**:
- yfinance-ux: Market data, prices, options, technicals
- edgartools: SEC filings, fundamentals, holdings, insider trading

**Combined Use Cases**:
1. **13F + Market Data** - See what Buffett bought + current performance
2. **Insider Trading + Price** - Detect insider buying at support levels
3. **Financials + Valuation** - Calculate P/E from SEC filings + market cap
4. **Holdings + Factor Analysis** - Institutional positioning + risk metrics

---

**Next Actions**:
1. Fix pyarrow dependency in forked version
2. Create test scripts for core capabilities
3. Design MCP tool interfaces
4. Implement Phase 1 tools (financials, 13F, Form 4)
5. Document edge cases and error handling
