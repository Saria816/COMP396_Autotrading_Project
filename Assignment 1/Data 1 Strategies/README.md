# BT396 Backtester Framework

BT001 is the **Backtest Framework**.
It is built on [Backtrader](https://www.backtrader.com/) and provides a controlled environment where student strategies are run under standardised rules (slippage, bankruptcy checks, overspend guards, etc.).

---

## 🚀 Quick Start for BT001 Assignment Submission

**This project contains the complete BT001 assignment submission with 3 individual trading strategies and 1 combined CVaR-optimized portfolio strategy.**

### Prerequisites

- Python 3.10+ installed
- Virtual environment `.venv` is already included in this submission
- All dependencies are pre-installed in `.venv`

### Option 1: Run All Strategies at Once 

**For full period backtest (Days 1-1000):**

```bash
# Linux/macOS
source .venv/bin/activate
python run_all_strategies.py

# Windows
.venv\Scripts\activate
python run_all_strategies.py
```

This single command will:
- Run all 3 individual strategies (S1, S2, S3)
- Run the combined CVaR portfolio strategy
- Generate performance comparison charts
- Create a summary report in `output/all_strategies_summary.md`

**For test period only (Days 701-1000) (Recommended):**

```bash
python run_all_strategies.py --test-period
```

### Option 2: Run Individual Strategies

If you prefer to run strategies separately:

```bash
# Activate virtual environment first
source .venv/bin/activate  # Linux/macOS
# OR
.venv\Scripts\activate     # Windows

# Strategy 1: Dual Moving Average Crossover (Series 04)
python main.py --strategy s1_dual_ma_crossover --output-dir output/individual_strategies/s1_dual_ma

# Strategy 2: Buy and Hold (Series 05)
python main.py --strategy s2_buy_and_hold --output-dir output/individual_strategies/s2_buy_hold

# Strategy 3: Statistical Mean Reversion (Series 09)
python main.py --strategy s3_mean_reversion --output-dir output/individual_strategies/s3_mean_reversion

# Combined CVaR Portfolio Strategy
python main.py --strategy combined_cvar_strategy --output-dir output/combined_strategy
```

### View Results

After running, check these files:

1. **Performance Summary**: `output/all_strategies_summary.md`
2. **Individual Strategy Results**: `output/individual_strategies/<strategy_name>/run_summary.json`
3. **Combined Strategy Results**: `output/combined_strategy/run_summary.json`
4. **Comparison Charts**: `output/all_strategies_*.png`
5. **Academic Report**: `report.md` (main deliverable)
6. **Data Documentation**: `shuoming.md` (Chinese documentation with data verification)

### Project Documentation

- **report.md** - Main academic report with all strategies, data analysis, and performance results
- **shuoming.md** - Data documentation and verification procedures (in Chinese)
- **CLAUDE.md** - Project development and maintenance documentation
- **README.md** - This file (framework and quick start guide)

### Expected Output (Full Period - Days 1-1000)

| Strategy | Final Value | Total Return | Annualized Sharpe | Max Drawdown |
|----------|------------|--------------|-------------------|--------------|
| S1: Dual MA | £1,006,722 | +0.67% | 0.102 | -2.12% |
| S2: Buy & Hold | £1,355,940 | +35.59% | 0.999 | -10.12% |
| S3: Mean Reversion | £1,007,367 | +0.74% | 0.423 | -0.59% |
| Combined CVaR | £1,129,321 | +12.93% | 1.061 | -3.86% |

**Note**: These are the verified results from the full backtest period. Test period results (Days 701-1000) will differ.

### Troubleshooting

**If virtual environment doesn't work:**

```bash
# Create new virtual environment
python -m venv venv_new

# Activate it
source venv_new/bin/activate  # Linux/macOS
# OR
venv_new\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Run strategies
python run_all_strategies.py
```

**If you get "module not found" errors:**

```bash
pip install -r requirements.txt
```

---

## 📚 Framework Documentation (For Reference)

The sections below provide detailed documentation about the BT001 framework itself.

---

## Installation (Windows)

Follow these steps on a **fresh Windows machine**:

1. **Install Python**  
   - Download and install [Python 3.10+](https://www.python.org/downloads/).  
   - During installation, **tick "Add Python to PATH"**.

2. **Install Git (optional)**  
   - If you want to clone the repository directly, install [Git for Windows](https://git-scm.com/download/win).  
   - Otherwise, you can just unzip the provided `BT001.zip`.

3. **Unzip / Clone the Framework**  
   - Place the folder somewhere convenient, e.g. `C:\Users\<YourName>\BT001`.

4. **Open Command Prompt (cmd) or PowerShell**  
   - Navigate to the project root folder:
     ```bash
     cd C:\Users\<YourName>\BT001
     ```

5. **Create a Virtual Environment (recommended)**  
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

6. **Install Dependencies**  
   ```bash
   pip install --upgrade pip
   pip install backtrader pandas matplotlib pyyaml
   ```

   These are the core requirements:
   - `backtrader` – backtesting engine  
   - `pandas` – data handling  
   - `matplotlib` – plotting  
   - `pyyaml` – config file support (optional, falls back to JSON)

---

## Running the Backtester

The entry point is **`main.py`**.  
It takes a strategy (from the `strategies/` folder) and runs it against sample data in `DATA/`.

Basic usage:

```bash
python main.py --strategy <name>
```

---

##  Example Runs

### 1. Run the **Copycat** strategy
This is a simple demo strategy that goes long if yesterday’s close > open, otherwise short:

```bash
python main.py --strategy copycat
```

### 2. Run with **debug logging** enabled
This prints order fills, slippage, and trade PnL to the console:

```bash
python main.py --strategy copycat --debug
```

### 3. Run with a different dataset
If you have your own CSVs in a folder (must contain at least 10 aligned OHLCV files):

```bash
python main.py --strategy copycat --data-dir ./DATA/MYCSV
```

### 4. Run the **Portfolio Bankrupt Demo**
This shows what happens with extreme leverage and bad allocation:

```bash
python main.py --strategy p_bankrupt
```

---

## Structure

```
BT396/
│── main.py                 # Entry point
│── framework/              # Core framework (rules, analyzers, plotting)
│── strategies/             # Example + strategies
│── DATA/                   # Sample CSV data
│── output/                 # Results are saved here
│── config.yaml             # Default config file
```

- Results (equity curves, JSON summaries, plots) are saved into the `output/` folder.
- You can override most settings via command line arguments (cash, commission, policies, etc.).

---

## Next Steps for Students

- Copy `strategies/template_strategy.py` and start building your own trading ideas.  
- Always test with:
  ```bash
  python main.py --strategy <your_strategy>
  ```
- Check the `output/` folder for plots and summaries.

---

## Notes

- Market orders include slippage, overspending cancels all trades for the day, and bankruptcy halts your run.  
- Plots include portfolio equity curves, per-series PnL, activity ratios, and realized PnL dashboards.  

---

Happy Backtesting

---

Distribution / Packaging
------------------------

If you want to zip this project for distribution, it is safe to exclude or delete the following from the archive:

- .git/ (Git repository metadata)
- .idea/ (JetBrains/IDE project files)
- __pycache__/ (Python bytecode caches) — these will be re-created automatically
- .pytest_cache/, .mypy_cache/ (tool caches)
- OS junk files like .DS_Store, Thumbs.db

Optionally exclude generated outputs to keep the archive small:

- output/ (plots and run summaries created by main.py)

Nothing in the list above is required to run the backtester.

Quick way to create a clean ZIP:

- From the project root, run:
  
  ```bash
  python scripts/make_dist.py           # creates BT001-dist.zip in the project root
  python scripts/make_dist.py --no-output  # also excludes the output/ folder
  python scripts/make_dist.py --name BT001_0.1.0_win.zip
  ```

When a user unzips the archive, they can run:

```bash
python main.py               # shows project version and date
python main.py --strategy copycat
```
-------
# Writing a Backtester Strategy in the BT396 Framework
The BT001 Backtester Framework uses Backtrader with some extra rules.
You provide a strategy via a Backtrader Strategy subclass.

## What you write (and where)
Create a file under `strategies/` with **one** Backtrader strategy class (e.g., `TemplateStrategy`) that inherits from `bt.Strategy`.
```python
# strategies/template_strategy.py
import backtrader as bt

class TemplateStrategy(bt.Strategy):
    params = (
        ('stake', 10),
        ('series_index', 0),
        ('use_limits', False),
        ('limit_offset', 0.01),
    )

    def start(self):
        # Initialize indicators / state here
        # e.g., self.counter = 0
        pass

    def next(self):
        # Runs once per bar (day)
        d = self.datas[self.p.series_index]

        # Example: buy once if flat, but only if budget allows
        if not self.getposition(d):
            intents = [(d, self.p.stake)]  # (data, signed_size)
            if self.overspend_guard(intents):  # required before MARKETs
                self.place_market(d, self.p.stake)
            else:
                self.log("Overspend! No trades today")

        # Example: place daily limit orders (max 1 buy + 1 sell per series/day)
        if self.p.use_limits:
            o = float(d.open[0])
            self.place_limit(d, +self.p.stake, price=o * (1 - self.p.limit_offset))  # buy below open
            self.place_limit(d, -self.p.stake, price=o * (1 + self.p.limit_offset))  # sell above open

    def notify_order(self, order):
        if order.status == order.Completed:
            side = "BUY" if order.isbuy() else "SELL"
            self.log(f"{side} filled @ {order.executed.price:.2f} size={order.executed.size}")
```
**Quick rules-of-thumb:**
Put all your parameters in `params` and access via `self.p.name`.
Do **not** call `super().next()` — the wrapper handles framework logic.
Use BT001 helpers: `overspend_guard`, `place_market`, `place_limit`, `log`.

## What the Framework does for you
1. Runs framework `start()` / `next()` first, then calls your `start()` / `next()`.
2. Buffers **MARKET** orders during your `next()` and flushes them after a single overspend (budget) check.
3. Cancels all prior-day **LIMIT** orders at the start of each trading day; you re-place them daily if needed.
4. Enforces **LIMIT** cap: max 1 buy + 1 sell per series per day.
5. Applies the **slippage model** automatically to fills.
6. Handles **final-day policy** (auto-liquidate or hold) and **bankruptcy** safety stop.
You write plain Backtrader; the framework enforces uniform execution rules.

## The three hooks you actually use
1. `params = (...)`: user-tunable knobs (sizes, thresholds, which series to trade, etc.).
2. `start(self)`: set up indicators, arrays, counters (runs once at the beginning).
3. `next(self)`: per-day decision logic (choose instruments, compute signals, guard budget, place orders).
Optional but useful: notify_order(self, order) to log fills or record metrics (slippage already applied).

## Helpers & safety rules
### Market Orders & Overspend Guard
BT001 prevents negative cash by **blocking all new market orders for the day** if they would overspend. Always declare your intended market orders and call `overspend_guard` before placing them.
#### Correct usage:
```python
def next(self):
    d = self.datas[0]
    size = 50

    # Declare what you're about to submit as MARKET orders:
    intents = [(d, size)]  # (data, signed_size)

    if self.overspend_guard(intents):
        self.place_market(d, size)
    else:
        self.log("Overspend! No trades today.") 
```
#### Incorrect usage (will be blocked by framework):
```python
def next(self):
    d = self.datas[0]
    # Missing budget guard; framework may block this trade
    self.place_market(d, 50)
```
####  What `overspend_guard()` actually does:
In BT001, **all market orders are checked against your available cash.**
Before you can place any market orders, you must call:
```python
if self.overspend_guard(intents):
    self.place_market(d, size)
```
where `intents` is a list of `(data, size)` tuples representing your planned trades for that bar.
The guard simulates your intended trades at the next open (including slippage) and checks if you’d run out of cash or go negative.

If **yes**, it cancels **all** your pending market orders for that day.

If **no**, your trades are passed to the backtester for execution.

### Limit Orders (Daily, Capped)
Limit orders are **daily** and capped at **1 buy + 1 sell per series per day**. They are cancelled automatically at the start of the next trading day.
#### Placing daily limits:
```python
def next(self):
    d = self.datas[0]
    o = float(d.open[0])

    # Buy below today's open
    self.place_limit(d, +10, price=o * 0.99)

    # Sell above today's open
    self.place_limit(d, -10, price=o * 1.01)
```
#### Exceeding the cap (extra limits rejected):
```python
def next(self):
    d = self.datas[0]
    o = float(d.open[0])
    # First buy limit accepted; subsequent ones logged/rejected
    self.place_limit(d, +10, price=o * 0.99)
    self.place_limit(d, +5, price=o * 0.98)
    self.place_limit(d, +2, price=o * 0.97)
```

### Slippage Model (Automatic for Market Fills)
On each market fill, BT001 applies a slippage adjustment based on a fraction of the overnight gap (|Open[t] − Close[t−1]|), multiplied by your size. You don’t implement this yourself.
#### Conceptual example:
```python
# Yesterday's close = 100, today's open = 101 (gap = 1)
# Slippage multiplier (example) = 0.2
# Buying 10 units → extra cash cost = 0.2 * 1 * 10 = 2.0

def next(self):
    d = self.datas[0]
    # The slippage is automatically applied on fill:
    self.place_market(d, 10)
```

### End-of-run Policy
The framework enforces a clean finish. Choose via CLI:
1. `--end-policy liquidate` -> auto-closes all positions at the final day’s open. (Use this one)
2. `--end-policy hold` -> positions remain open. (Don't use this)
#### Example command:
python3 main.py --strategy my_strategy --data-dir DATA/PART1 --output-dir output --end-policy liquidate

### Bankruptcy Stop
If net worth (cash + positions marked at open) goes negative, BT001 **force-liquidates** at the open and terminates the run. This is automatic — no strategy code needed.
#### Example scenario:
```python
def next(self):
    d = self.datas[0]
    # Aggressive sizing may drive net worth below zero over time:
    self.place_market(d, 1000)  # too big for the budget
# Framework will eventually liquidate at open and stop the backtest.
```

## Summary Table
| Feature | Function / Flag | Purpose&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Example |
| :---------- | :---: | :--- | :---|
| Budget check | `overspend_guard(intents)` | Block MARKET orders if they would overspend | `if self.overspend_guard([(d,10)]): self.place_market(d,10)` |
| Market orders | `place_market(data,size)` | Buffered during `next()`; flushed after budget check | `self.place_market(d, 10)` |
| Limit orders | `place_limit(data,size,price)` | Daily; 1 buy + 1 sell per series per day | `self.place_limit(d, -5, price=101.0)` |
| Slippage | (automatic) | Adjusts market fills by fraction of overnight gap | Applied on `place_market` fills |
| End policy | `--end-policy` | Auto liquidate or hold positions at end | `--end-policy liquidate` |
| Bankruptcy | (automatic) | Force-liquidate & stop when net worth < 0 | Triggered by excessive sizing |

Tip: Combine these rules in your next() as a checklist — compute intended sizes, guard budget, place orders (market or limit), and let BT001 handle slippage, caps, daily cancellations, and end-of-run behavior.

## Data feeds you’ll see (`self.datas`)
1. Loader ingests up to 10 CSVs and aligns by date.
2. Access by index (`self.datas[0]`) or by common names (e.g., `"series_1"`, `"series_2"`).
3. Standard OHLCV fields available; e.g., `d.open[0]`, `d.close[0]`.

## Built-in analyzers (automatic)
1. **Open** -> **Open PnL** per series and portfolio.
2. **Max drawdown** and **PD ratio** (final cumulative PnL ÷ max drawdown).
3. **Activity** (% days with non-zero positions).
4. Optional plots and JSON summaries are created if enabled.

## How to run your strategy
python3 main.py --strategy template_strategy --param stake=25 -param series_index=0 -data-dir DATA/PART1 --output-dir output --end-policy liquidate --s-mult 1.0 --debug

**Notes:** `--param key=value` maps to your `params` (types auto-coerced). `--debug` enables verbose logging (orders, fills, slippage, cancellations).

## One-minute checklist for `next()`
1. Pick instrument(s): `d = self.datas[i]`.
2. Compute signals & decide signed size(s).
3. For MARKETs, build `intents` and call `overspend_guard`.
4. Place with `place_market` / `place_limit`.
5. Expect: daily limit cancel; limit cap; buffered market flush; auto slippage; end-policy; bankruptcy guard.