from datetime import datetime, timezone, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# -------------------------
# Configuration
# -------------------------
SPY_AVG_YEARLY_RETURN = 10  # Average yearly return in percentage
UBS_AVG_YEARLY_RETURN = 0  # Average yearly return in percentage
MONTHLY_INVESTMENT = 1000
WINDOW_MONTHS = 120  # 10 years
START_DATE = datetime(2000, 1, 1, tzinfo=timezone.utc)  # Start date for simulation
INVESTMENT_MONTHS = 60  # First 5 years
BONUS_FRACTION = 1/3  # 1/3 bonus shares

# -------------------------
# Generate synthetic price series from average yearly returns
# -------------------------
def generate_price_series(start_price, yearly_return_pct, num_months):
    """
    Generate a price series based on average yearly return.
    Converts yearly return to monthly return using compound growth.
    """
    # Convert yearly return percentage to decimal
    yearly_return = yearly_return_pct / 100.0
    
    # Convert to monthly return: (1 + yearly_return)^(1/12) - 1
    monthly_return = (1 + yearly_return) ** (1/12) - 1
    
    prices = [start_price]
    for _ in range(num_months - 1):
        # Apply monthly return
        new_price = prices[-1] * (1 + monthly_return)
        prices.append(new_price)
    
    return prices

# Generate price series for both stocks for a single 6-year period
# Start with arbitrary base prices
SPY_BASE_PRICE = 100.0
UBS_BASE_PRICE = 50.0

spy_prices = generate_price_series(SPY_BASE_PRICE, SPY_AVG_YEARLY_RETURN, WINDOW_MONTHS)
ubs_prices = generate_price_series(UBS_BASE_PRICE, UBS_AVG_YEARLY_RETURN, WINDOW_MONTHS)

# Create timestamp series (monthly)
timestamps = []
dates = []
current_date = START_DATE
for _ in range(WINDOW_MONTHS):
    timestamps.append(int(current_date.timestamp()))
    dates.append(current_date)
    # Move to next month
    if current_date.month == 12:
        current_date = current_date.replace(year=current_date.year + 1, month=1)
    else:
        current_date = current_date.replace(month=current_date.month + 1)

# Create series in same format as original: (timestamp, spy_price, ubs_price)
series = [(ts, spy_price, ubs_price) for ts, spy_price, ubs_price in zip(timestamps, spy_prices, ubs_prices)]

# -------------------------
# Single 6-year simulation - SPY Strategy
# -------------------------
spy_portfolio_values = []
portfolio_value = 0.0

for i in range(1, len(series)):
    prev_spy_close = series[i - 1][1]
    curr_spy_close = series[i][1]

    monthly_return = curr_spy_close / prev_spy_close
    portfolio_value *= monthly_return
    # Only invest for the first 3 years (36 months)
    if i <= INVESTMENT_MONTHS:
        portfolio_value += MONTHLY_INVESTMENT
    
    spy_portfolio_values.append(portfolio_value)

# -------------------------
# Single 6-year simulation - UBS Bonus Strategy
# -------------------------
ubs_portfolio_values = []
ubs_shares_values = []  # Track UBS shares value separately
ubs_spy_values = []  # Track SPY value separately

# Track purchases by calendar year
# All shares bought in a calendar year mature on March 1st, 3 years later
# Dictionary: {purchase_year: total_shares}
ubs_purchases_by_year = {}  # Dict[int, float] - year -> total shares

spy_value_from_sales = 0.0  # Value from selling matured purchases and investing in SPY

for i in range(1, len(series)):
    prev_spy_close = series[i - 1][1]
    curr_spy_close = series[i][1]
    prev_ubs_close = series[i - 1][2]
    curr_ubs_close = series[i][2]
    
    # Get current date
    current_date = dates[i]
    
    # Update SPY value (from selling matured purchases)
    spy_return = curr_spy_close / prev_spy_close
    spy_value_from_sales *= spy_return
    
    # First 3 years: invest in UBS and track purchases by year
    if i <= INVESTMENT_MONTHS:
        # Calculate shares purchased this month
        # Regular shares: MONTHLY_INVESTMENT / curr_ubs_close
        # Bonus shares: 1/3 of regular shares
        regular_shares = MONTHLY_INVESTMENT / curr_ubs_close
        bonus_shares = regular_shares * BONUS_FRACTION
        total_shares = regular_shares + bonus_shares
        
        # Track this purchase by calendar year
        purchase_year = current_date.year
        if purchase_year not in ubs_purchases_by_year:
            ubs_purchases_by_year[purchase_year] = 0.0
        ubs_purchases_by_year[purchase_year] += total_shares
    
    # Check if current date is March 1st
    # If so, check if any purchases from 3 years ago should mature
    if current_date.month == 3 and current_date.day == 1:
        maturity_year = current_date.year
        purchase_year = maturity_year - 3  # Shares purchased 3 years ago
        
        # Sell all shares purchased in that year
        if purchase_year in ubs_purchases_by_year:
            shares_to_sell = ubs_purchases_by_year[purchase_year]
            current_value = shares_to_sell * curr_ubs_close
            
            # Sell ALL shares from that year and invest proceeds in SPY
            spy_value_from_sales += current_value
            
            # Remove from tracking
            del ubs_purchases_by_year[purchase_year]
    
    # Track UBS shares value and SPY value separately
    # Calculate total UBS shares value (all shares not yet matured)
    ubs_shares_value = sum(shares * curr_ubs_close for shares in ubs_purchases_by_year.values())
    portfolio_value = spy_value_from_sales + ubs_shares_value
    
    ubs_portfolio_values.append(portfolio_value)
    ubs_shares_values.append(ubs_shares_value)
    ubs_spy_values.append(spy_value_from_sales)

# -------------------------
# Output
# -------------------------
print(f"Simulation Parameters:")
print(f"  SPY Average Yearly Return: {SPY_AVG_YEARLY_RETURN}%")
print(f"  UBS Average Yearly Return: {UBS_AVG_YEARLY_RETURN}%")
print(f"  Monthly Investment: ${MONTHLY_INVESTMENT}")
print(f"  Investment Period: First {INVESTMENT_MONTHS} months (3 years)")
print(f"  Total Period: {WINDOW_MONTHS} months (6 years)")

# Summary stats
print(f"\n=== SPY Strategy Summary ===")
print(f"Final portfolio value: ${spy_portfolio_values[-1]:,.2f}")
total_invested = INVESTMENT_MONTHS * MONTHLY_INVESTMENT
spy_total_return = (spy_portfolio_values[-1] / total_invested - 1) * 100
print(f"Total return: {spy_total_return:.2f}%")
spy_annualized = ((spy_portfolio_values[-1] / total_invested) ** (1 / (WINDOW_MONTHS / 12)) - 1) * 100
print(f"Annualized return: {spy_annualized:.2f}%")

print(f"\n=== UBS Bonus Strategy Summary ===")
print(f"Final portfolio value: ${ubs_portfolio_values[-1]:,.2f}")
ubs_total_return = (ubs_portfolio_values[-1] / total_invested - 1) * 100
print(f"Total return: {ubs_total_return:.2f}%")
ubs_annualized = ((ubs_portfolio_values[-1] / total_invested) ** (1 / (WINDOW_MONTHS / 12)) - 1) * 100
print(f"Annualized return: {ubs_annualized:.2f}%")

print(f"\n=== Strategy Comparison ===")
if spy_portfolio_values[-1] > ubs_portfolio_values[-1]:
    diff = spy_portfolio_values[-1] - ubs_portfolio_values[-1]
    print(f"SPY Strategy wins by ${diff:,.2f}")
elif ubs_portfolio_values[-1] > spy_portfolio_values[-1]:
    diff = ubs_portfolio_values[-1] - spy_portfolio_values[-1]
    print(f"UBS Bonus Strategy wins by ${diff:,.2f}")
else:
    print("Both strategies have the same final value")

# -------------------------
# Chart
# -------------------------
# Use dates from the simulation (skip first month since we start tracking from month 1)
plot_dates = dates[1:]

# Create the plot
try:
    plt.style.use('seaborn-v0_8-darkgrid')
except OSError:
    try:
        plt.style.use('seaborn-darkgrid')
    except OSError:
        plt.style.use('default')
        
fig, ax = plt.subplots(figsize=(14, 7))

# Plot SPY strategy as a line
ax.plot(plot_dates, spy_portfolio_values, linewidth=2.5, color='#2E86AB', alpha=0.9, label='SPY Strategy', zorder=3)

# Plot UBS strategy as a stacked area chart
# Stack UBS shares (bottom) and SPY shares (top)
ax.fill_between(plot_dates, 0, ubs_shares_values, alpha=0.6, color='#A23B72', label='UBS Strategy - UBS Shares', zorder=1)
ax.fill_between(plot_dates, ubs_shares_values, ubs_portfolio_values, alpha=0.6, color='#F18F01', label='UBS Strategy - SPY Shares', zorder=1)

# Add a vertical line at 3 years to show when investments stop
investment_end_date = dates[INVESTMENT_MONTHS]
ax.axvline(x=investment_end_date, color='gray', linestyle='--', linewidth=1.5, alpha=0.6, label='Investment Period Ends', zorder=2)

# Formatting
ax.set_xlabel('Date', fontsize=12, fontweight='bold')
ax.set_ylabel('Portfolio Value ($)', fontsize=12, fontweight='bold')
title = f'Portfolio Value Comparison: SPY ({SPY_AVG_YEARLY_RETURN}% avg) vs UBS Bonus ({UBS_AVG_YEARLY_RETURN}% avg)\n(6-Year Investment Period)'
ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
ax.grid(True, alpha=0.3)
ax.legend(loc='best', fontsize=11, framealpha=0.9)

# Format x-axis dates
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax.xaxis.set_major_locator(mdates.YearLocator(1))  # Show every year
plt.xticks(rotation=45, ha='right')

# Format y-axis as currency
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'${y:,.0f}'))

# Tight layout for better appearance
plt.tight_layout()

# Save and show
plt.savefig('portfolio_values_chart.png', dpi=300, bbox_inches='tight')
print("\nChart saved as 'portfolio_values_chart.png'")
plt.show()

