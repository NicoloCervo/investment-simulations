import json
from datetime import datetime, timezone
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# -------------------------
# Configuration
# -------------------------
SPY_JSON_FILE = "spy_monthly_30y.json"
UBS_JSON_FILE = "ubs_monthly_max.json"
MONTHLY_INVESTMENT = 1000
WINDOW_MONTHS = 72  # 6 years
START_EPOCH = 959832000  # 2000-06-01 UTC
INVESTMENT_MONTHS = 36  # First 3 years
BONUS_FRACTION = 1/3  # 1/3 bonus shares
YEARLY_WINDOWS = True  # Set to True to start windows only at the beginning of each year

# -------------------------
# Load Yahoo Finance data
# -------------------------
# Load SPY data
with open(SPY_JSON_FILE, "r") as f:
    spy_data = json.load(f)

spy_result = spy_data["chart"]["result"][0]
spy_timestamps = spy_result["timestamp"]
spy_closes = spy_result["indicators"]["quote"][0]["close"]

# Load UBS data
with open(UBS_JSON_FILE, "r") as f:
    ubs_data = json.load(f)

ubs_result = ubs_data["chart"]["result"][0]
ubs_timestamps = ubs_result["timestamp"]
ubs_closes = ubs_result["indicators"]["quote"][0]["close"]

# Filter out null closes and align by timestamp
spy_series = [
    (ts, close)
    for ts, close in zip(spy_timestamps, spy_closes)
    if close is not None and ts >= START_EPOCH
]

ubs_series = [
    (ts, close)
    for ts, close in zip(ubs_timestamps, ubs_closes)
    if close is not None and ts >= START_EPOCH
]

# Create dictionaries for quick lookup by timestamp
spy_dict = {ts: close for ts, close in spy_series}
ubs_dict = {ts: close for ts, close in ubs_series}

# Get common timestamps (where both have data)
common_timestamps = sorted(set(spy_dict.keys()) & set(ubs_dict.keys()))
series = [(ts, spy_dict[ts], ubs_dict[ts]) for ts in common_timestamps]

# -------------------------
# Helper
# -------------------------
def to_utc(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc)

# -------------------------
# Determine window start indices
# -------------------------
if YEARLY_WINDOWS:
    # Only start windows at the beginning of each year (January)
    window_start_indices = []
    for start_idx in range(len(series) - WINDOW_MONTHS):
        start_ts = series[start_idx][0]
        start_date = to_utc(start_ts)
        # Only include windows that start in January (month == 1)
        if start_date.month == 1:
            window_start_indices.append(start_idx)
else:
    # Start windows every month
    window_start_indices = list(range(len(series) - WINDOW_MONTHS))

# -------------------------
# Rolling 6-year simulation - SPY Strategy
# -------------------------
spy_portfolio_results = []

for start_idx in window_start_indices:
    window = series[start_idx : start_idx + WINDOW_MONTHS]

    portfolio_value = 0.0

    for i in range(1, len(window)):
        prev_spy_close = window[i - 1][1]
        curr_spy_close = window[i][1]

        monthly_return = curr_spy_close / prev_spy_close
        portfolio_value *= monthly_return
        # Only invest for the first 3 years (36 months)
        if i <= INVESTMENT_MONTHS:
            portfolio_value += MONTHLY_INVESTMENT

    start_ts = window[0][0]
    end_ts = window[-1][0]
    
    # Calculate annualized return
    total_invested = INVESTMENT_MONTHS * MONTHLY_INVESTMENT
    total_return = portfolio_value / total_invested
    annualized_return = (total_return ** (1 / (WINDOW_MONTHS / 12))) - 1

    start_date = to_utc(start_ts)
    spy_portfolio_results.append({
        "start_date": start_date,
        "start_date_str": start_date.strftime("%Y-%m"),
        "end_date": to_utc(end_ts).strftime("%Y-%m"),
        "final_value": round(portfolio_value, 2),
        "annualized_return": round(annualized_return * 100, 2)  # As percentage
    })

# -------------------------
# Rolling 6-year simulation - UBS Bonus Strategy
# -------------------------
ubs_portfolio_results = []

for start_idx in window_start_indices:
    window = series[start_idx : start_idx + WINDOW_MONTHS]
    
    # Track purchases by calendar year
    # All shares bought in a calendar year mature on March 1st, 3 years later
    # Dictionary: {purchase_year: total_shares}
    ubs_purchases_by_year = {}  # Dict[int, float] - year -> total shares
    
    spy_value_from_sales = 0.0  # Value from selling matured purchases and investing in SPY

    for i in range(1, len(window)):
        prev_spy_close = window[i - 1][1]
        curr_spy_close = window[i][1]
        prev_ubs_close = window[i - 1][2]
        curr_ubs_close = window[i][2]
        
        # Get current date from timestamp
        current_ts = window[i][0]
        current_date = to_utc(current_ts)
        
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
        
        # Note: We don't need to track UBS shares value separately anymore
        # because all shares are sold after 3 years. The only remaining value
        # is from SPY investments made from selling matured purchases.
    
    # Final portfolio value = SPY from selling matured purchases
    # (All UBS shares have been sold after 3 years)
    portfolio_value = spy_value_from_sales

    start_ts = window[0][0]
    end_ts = window[-1][0]
    
    # Calculate annualized return
    total_invested = INVESTMENT_MONTHS * MONTHLY_INVESTMENT
    total_return = portfolio_value / total_invested
    annualized_return = (total_return ** (1 / (WINDOW_MONTHS / 12))) - 1

    start_date = to_utc(start_ts)
    ubs_portfolio_results.append({
        "start_date": start_date,
        "start_date_str": start_date.strftime("%Y-%m"),
        "end_date": to_utc(end_ts).strftime("%Y-%m"),
        "final_value": round(portfolio_value, 2),
        "annualized_return": round(annualized_return * 100, 2)  # As percentage
    })

# -------------------------
# Output
# -------------------------
print(f"Total 6y windows simulated: {len(spy_portfolio_results)}")

# Summary stats for SPY strategy
spy_returns = [r["annualized_return"] for r in spy_portfolio_results]
print("\n=== SPY Strategy Summary ===")
print(f"Min annualized return: {min(spy_returns):.2f}%")
print(f"Max annualized return: {max(spy_returns):.2f}%")
print(f"Average annualized return: {sum(spy_returns)/len(spy_returns):.2f}%")

# Summary stats for UBS Bonus strategy
ubs_returns = [r["annualized_return"] for r in ubs_portfolio_results]
print("\n=== UBS Bonus Strategy Summary ===")
print(f"Min annualized return: {min(ubs_returns):.2f}%")
print(f"Max annualized return: {max(ubs_returns):.2f}%")
print(f"Average annualized return: {sum(ubs_returns)/len(ubs_returns):.2f}%")

# -------------------------
# Strategy Comparison
# -------------------------
spy_wins = 0
ubs_wins = 0
ties = 0

for spy_result, ubs_result in zip(spy_portfolio_results, ubs_portfolio_results):
    spy_return = spy_result["annualized_return"]
    ubs_return = ubs_result["annualized_return"]
    
    if spy_return > ubs_return:
        spy_wins += 1
    elif ubs_return > spy_return:
        ubs_wins += 1
    else:
        ties += 1

window_type = "years" if YEARLY_WINDOWS else "months"
print(f"\n=== Strategy Comparison ===")
print(f"SPY Strategy wins: {spy_wins} {window_type}")
print(f"UBS Bonus Strategy wins: {ubs_wins} {window_type}")
if ties > 0:
    print(f"Ties: {ties} {window_type}")
print(f"SPY win rate: {spy_wins/len(spy_portfolio_results)*100:.1f}%")
print(f"UBS Bonus win rate: {ubs_wins/len(spy_portfolio_results)*100:.1f}%")

# -------------------------
# Chart
# -------------------------
# Extract dates and returns for plotting
start_dates = [r["start_date"] for r in spy_portfolio_results]
spy_annualized_returns = [r["annualized_return"] for r in spy_portfolio_results]
ubs_annualized_returns = [r["annualized_return"] for r in ubs_portfolio_results]

# Create the plot
try:
    plt.style.use('seaborn-v0_8-darkgrid')
except OSError:
    try:
        plt.style.use('seaborn-darkgrid')
    except OSError:
        plt.style.use('default')
        
fig, ax = plt.subplots(figsize=(14, 7))

# Plot both strategies
ax.plot(start_dates, spy_annualized_returns, linewidth=2, color='#2E86AB', marker='o', markersize=3, alpha=0.7, label='SPY Strategy')
ax.plot(start_dates, ubs_annualized_returns, linewidth=2, color='#A23B72', marker='s', markersize=3, alpha=0.7, label='UBS Bonus Strategy')

# Add a horizontal line at 0% for reference
ax.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)

# Formatting
ax.set_xlabel('Window Start Date', fontsize=12, fontweight='bold')
ax.set_ylabel('Annualized Return (%)', fontsize=12, fontweight='bold')
ax.set_title('Annualized Returns Comparison: SPY vs UBS Bonus Strategy\n(Rolling 6-Year Investment Windows)', fontsize=14, fontweight='bold', pad=20)
ax.grid(True, alpha=0.3)
ax.legend(loc='best', fontsize=11, framealpha=0.9)

# Format x-axis dates
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax.xaxis.set_major_locator(mdates.YearLocator(2))  # Show every 2 years
plt.xticks(rotation=45, ha='right')

# Format y-axis as percentage
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.1f}%'))

# Tight layout for better appearance
plt.tight_layout()

# Save and show
plt.savefig('annualized_returns_chart.png', dpi=300, bbox_inches='tight')
print("\nChart saved as 'annualized_returns_chart.png'")
plt.show()
