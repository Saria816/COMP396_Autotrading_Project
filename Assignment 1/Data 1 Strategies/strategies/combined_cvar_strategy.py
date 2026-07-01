"""
Combined CVaR Portfolio Strategy for Part 2
Implements a unified strategy that applies CVaR-optimized allocation 
across three different asset series using their proven strategies
"""

import backtrader as bt
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from framework.cvar_optimizer import CVaROptimizer

class CombinedCVaRStrategy(bt.Strategy):
    """
    Combined portfolio strategy using CVaR optimization to allocate capital
    among three asset series with different trading approaches.
    
    This strategy implements Part 2 requirements:
    1. Strategy combination with dynamic CVaR-based allocation
    2. Advanced risk management through CVaR minimization
    3. Dynamic position sizing based on risk-adjusted weights
    """
    
    params = (
        # CVaR optimization parameters
        ('confidence_level', 0.05),        # 95% CVaR (5% tail risk)
        ('lookback_days', 60),             # Days for CVaR calculation
        ('rebalance_frequency', 20),       # Rebalance every 20 days
        ('min_weight', 0.1),               # Minimum allocation per asset
        ('max_weight', 0.7),               # Maximum allocation per asset
        
        # Strategy-specific parameters (optimized from Part 1)
        # Series 04: Dual MA Crossover
        ('s04_fast_period', 3),
        ('s04_slow_period', 24),
        ('s04_stop_pct', 0.10),
        ('s04_target_pct', 0.20),
        
        # Series 05: Buy and Hold
        # No additional parameters needed
        
        # Series 09: Mean Reversion
        ('s09_mean_period', 30),
        ('s09_entry_threshold', 2.0),
        ('s09_exit_threshold', 0.5),
        ('s09_max_holding_days', 20),
        ('s09_stake_pct', 0.15),
        ('s09_take_profit', 0.04),
        ('s09_stop_loss', 0.05),
    )
    
    def __init__(self):
        # Initialize CVaR optimizer
        self.cvar_optimizer = CVaROptimizer(
            confidence_level=self.params.confidence_level,
            lookback_days=self.params.lookback_days
        )

        # Asset weights (equal initially, then CVaR optimized)
        self.asset_weights = np.array([1/3, 1/3, 1/3])
        self.asset_names = ['Series_04', 'Series_05', 'Series_09']
        self.asset_indices = [3, 4, 8]  # Corresponding to series 04, 05, 09

        # Track asset returns history
        self.asset_returns_history = []
        self.rebalance_dates = []

        # Track weight history for reporting
        self.weight_history = []
        self.weight_history_dates = []
        
        # Portfolio tracking
        self.last_portfolio_value = self.broker.getvalue()
        self.last_rebalance_day = 0
        
        # Asset positions tracking
        self.asset_positions = [0, 0, 0]
        
        # Setup technical indicators for each asset
        self._setup_indicators()
        
        # Strategy-specific tracking variables
        self.s04_entry_price = None
        self.s05_bought = False
        self.s09_entry_price = None
        self.s09_entry_date = None
        
    def _setup_indicators(self):
        """Setup indicators for all three assets"""
        # Series 04: Dual MA indicators
        data_04 = self.datas[self.asset_indices[0]]
        self.s04_fast_ma = bt.indicators.SMA(data_04.close, period=self.params.s04_fast_period)
        self.s04_slow_ma = bt.indicators.SMA(data_04.close, period=self.params.s04_slow_period)
        
        # Series 05: Buy and Hold - no indicators needed
        
        # Series 09: Mean Reversion indicators
        data_09 = self.datas[self.asset_indices[2]]
        self.s09_mean_price = bt.indicators.SMA(data_09.close, period=self.params.s09_mean_period)
        self.s09_std_dev = bt.indicators.StdDev(data_09.close, period=self.params.s09_mean_period)
        self.s09_rsi = bt.indicators.RSI(data_09.close, period=14)
        
    def start(self):
        self.log("Combined CVaR Portfolio Strategy started")
        self.log(f"Initial asset weights: {self.asset_weights}")

        # Record initial weights
        self.weight_history.append(self.asset_weights.copy())
        self.weight_history_dates.append('Initial')
        
    def next(self):
        current_day = len(self.data)
        current_date = self.data.datetime.date(0)
        
        # Skip initial days until we have enough data
        if current_day < max(self.params.lookback_days, self.params.s04_slow_period, self.params.s09_mean_period):
            return
            
        # Calculate daily returns for rebalancing
        current_portfolio_value = self.broker.getvalue()
        
        # Store asset returns if we have previous portfolio value
        if hasattr(self, 'prev_asset_values'):
            asset_returns = []
            for i, asset_idx in enumerate(self.asset_indices):
                data = self.datas[asset_idx]
                if len(data) > 1:
                    asset_return = (data.close[0] / data.close[-1]) - 1
                    asset_returns.append(asset_return)
                else:
                    asset_returns.append(0.0)
            self.asset_returns_history.append(asset_returns)
        
        # Store current asset values for next iteration
        self.prev_asset_values = [self.datas[i].close[0] for i in self.asset_indices]
        
        # Rebalance portfolio weights periodically
        if (current_day - self.last_rebalance_day) >= self.params.rebalance_frequency:
            self._rebalance_portfolio()
            self.last_rebalance_day = current_day
            
        # Execute trading signals for each asset
        self._execute_trading_signals()
        
    def _rebalance_portfolio(self):
        """Rebalance portfolio using CVaR optimization"""
        try:
            if len(self.asset_returns_history) < 20:
                # Not enough data for optimization, keep equal weights
                return
                
            # Prepare returns matrix for CVaR optimization
            returns_df = pd.DataFrame(self.asset_returns_history, 
                                    columns=self.asset_names)
            returns_matrix = returns_df.values
            
            # Optimize weights using CVaR
            optimal_weights, opt_result = self.cvar_optimizer.optimize_weights(
                returns_matrix[-self.params.lookback_days:],
                initial_weights=self.asset_weights,
                min_weight=self.params.min_weight,
                max_weight=self.params.max_weight
            )
            
            if opt_result.success:
                self.asset_weights = optimal_weights
                current_date = self.data.datetime.date(0)
                self.rebalance_dates.append(current_date)
                self.log(f"Portfolio rebalanced: {self.asset_weights}")

                # Record weight history
                self.weight_history.append(self.asset_weights.copy())
                self.weight_history_dates.append(current_date.isoformat())
            else:
                self.log("CVaR optimization failed, keeping current weights")
                
        except Exception as e:
            self.log(f"Rebalancing error: {e}")
            
    def _execute_trading_signals(self):
        """Execute trading signals for all assets based on allocated weights"""
        total_capital = self.broker.getvalue()
        
        # Execute Series 04: Dual MA Crossover
        self._execute_series_04(total_capital * self.asset_weights[0])
        
        # Execute Series 05: Buy and Hold
        self._execute_series_05(total_capital * self.asset_weights[1])
        
        # Execute Series 09: Mean Reversion
        self._execute_series_09(total_capital * self.asset_weights[2])
        
    def _execute_series_04(self, allocated_capital):
        """Execute Dual MA strategy for Series 04"""
        data = self.datas[self.asset_indices[0]]
        current_price = data.close[0]
        position = self.getposition(data)
        
        # Position size based on allocated capital
        target_shares = int(allocated_capital * 0.25 / current_price)  # 25% of allocation
        
        # Entry signal: Fast MA crosses above Slow MA
        if (self.s04_fast_ma[0] > self.s04_slow_ma[0] and 
            self.s04_fast_ma[-1] <= self.s04_slow_ma[-1] and
            position.size == 0):
            
            if target_shares > 0:
                self.buy(data=data, size=target_shares)
                self.s04_entry_price = current_price
                self.dlog(f"S04 BUY: {target_shares} shares at {current_price:.2f}")
                
        # Exit signals
        elif position.size > 0:
            exit_signal = False
            
            # MA cross exit
            if (self.s04_fast_ma[0] < self.s04_slow_ma[0] and 
                self.s04_fast_ma[-1] >= self.s04_slow_ma[-1]):
                exit_signal = True
                
            # Stop loss
            elif (self.s04_entry_price and 
                  current_price <= self.s04_entry_price * (1 - self.params.s04_stop_pct)):
                exit_signal = True
                
            # Take profit
            elif (self.s04_entry_price and 
                  current_price >= self.s04_entry_price * (1 + self.params.s04_target_pct)):
                exit_signal = True
                
            if exit_signal:
                self.sell(data=data, size=position.size)
                self.s04_entry_price = None
                self.dlog(f"S04 SELL: {position.size} shares at {current_price:.2f}")
                
    def _execute_series_05(self, allocated_capital):
        """Execute Buy and Hold strategy for Series 05"""
        data = self.datas[self.asset_indices[1]]
        current_price = data.close[0]
        position = self.getposition(data)
        
        # Buy once at the beginning if not already bought
        if not self.s05_bought and position.size == 0:
            target_shares = int(allocated_capital / current_price)
            if target_shares > 0:
                self.buy(data=data, size=target_shares)
                self.s05_bought = True
                self.dlog(f"S05 BUY AND HOLD: {target_shares} shares at {current_price:.2f}")
                
    def _execute_series_09(self, allocated_capital):
        """Execute Mean Reversion strategy for Series 09"""
        data = self.datas[self.asset_indices[2]]
        current_price = data.close[0]
        position = self.getposition(data)
        current_date = self.data.datetime.date(0)
        
        # Skip if indicators not ready
        if len(self.s09_std_dev) < 1:
            return
            
        # Calculate Z-score
        if self.s09_std_dev[0] > 0:
            z_score = (current_price - self.s09_mean_price[0]) / self.s09_std_dev[0]
        else:
            return
            
        # Position size based on allocated capital
        target_shares = int(allocated_capital * self.params.s09_stake_pct / current_price)
        
        # Entry signal: Z-score below threshold + RSI oversold
        if (position.size == 0 and 
            z_score <= -self.params.s09_entry_threshold and
            self.s09_rsi[0] <= 30 and
            target_shares > 0):
            
            self.buy(data=data, size=target_shares)
            self.s09_entry_price = current_price
            self.s09_entry_date = current_date
            self.dlog(f"S09 BUY: {target_shares} shares at {current_price:.2f}, Z={z_score:.2f}")
            
        # Exit signals
        elif position.size > 0:
            holding_days = (current_date - self.s09_entry_date).days if self.s09_entry_date else 0
            exit_signal = False
            
            # Mean reversion exit
            if z_score >= self.params.s09_exit_threshold:
                exit_signal = True
            # Take profit
            elif (self.s09_entry_price and 
                  current_price >= self.s09_entry_price * (1 + self.params.s09_take_profit)):
                exit_signal = True
            # Stop loss  
            elif (self.s09_entry_price and 
                  current_price <= self.s09_entry_price * (1 - self.params.s09_stop_loss)):
                exit_signal = True
            # Max holding period
            elif holding_days >= self.params.s09_max_holding_days:
                exit_signal = True
                
            if exit_signal:
                self.sell(data=data, size=position.size)
                self.s09_entry_price = None
                self.s09_entry_date = None
                self.dlog(f"S09 SELL: {position.size} shares at {current_price:.2f}")
                
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}: {txt}')
    
    def dlog(self, txt, dt=None):
        # Debug logging - can be enabled for detailed tracking
        pass
    
    def stop(self):
        """Called when strategy ends - calculate final metrics and generate visualizations"""
        self.log("Combined CVaR Portfolio Strategy completed")
        self.log(f"Final asset weights: {self.asset_weights}")
        self.log(f"Total rebalances: {len(self.rebalance_dates)}")

        # Save weight history to JSON file
        import json
        import os

        weight_history_data = {
            'asset_names': self.asset_names,
            'weight_history': [weights.tolist() for weights in self.weight_history],
            'dates': self.weight_history_dates,
            'total_rebalances': len(self.rebalance_dates),
            'final_weights': self.asset_weights.tolist()
        }

        # Save to file in output directory
        output_dir = os.environ.get('OUTPUT_DIR', 'output/combined_strategy')
        os.makedirs(output_dir, exist_ok=True)
        weight_history_file = os.path.join(output_dir, 'weight_history.json')

        with open(weight_history_file, 'w') as f:
            json.dump(weight_history_data, f, indent=2)
        self.log(f"Weight history saved to {weight_history_file}")

        # Generate weight evolution visualization
        self._create_weight_evolution_chart(weight_history_data, output_dir)
        self._create_weight_tables(weight_history_data, output_dir)

        if len(self.asset_returns_history) > 0:
            returns_df = pd.DataFrame(self.asset_returns_history,
                                    columns=self.asset_names)

            # Calculate final CVaR metrics
            final_metrics = self.cvar_optimizer.calculate_portfolio_metrics(
                returns_df.values, self.asset_weights
            )

            self.log(f"Final CVaR (5%): {final_metrics['cvar_5pct']:.4f}")
            self.log(f"Final Sharpe Ratio: {final_metrics['sharpe_ratio']:.3f}")
            self.log(f"Max Drawdown: {final_metrics['max_drawdown']:.3f}")

    def _create_weight_evolution_chart(self, data, output_dir):
        """Create weight evolution chart"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates

            # Extract data
            weight_history = np.array(data['weight_history'])
            dates = data['dates']

            # Convert dates for x-axis
            x_labels = []
            x_positions = []
            for i, date in enumerate(dates):
                if date == 'Initial':
                    x_labels.append('Initial')
                else:
                    x_labels.append(date[:10])  # YYYY-MM-DD format
                x_positions.append(i)

            # Create figure - Line Chart only
            fig, ax = plt.subplots(1, 1, figsize=(12, 7))

            # Colors for each asset
            colors = ['#2E86AB', '#A23B72', '#F18F01']

            # Plot Line Chart
            for i, asset_name in enumerate(['Series 04 (Dual MA)', 'Series 05 (Buy & Hold)', 'Series 09 (Mean Reversion)']):
                ax.plot(x_positions, weight_history[:, i] * 100,
                       marker='o', markersize=5, linewidth=2,
                       label=asset_name, color=colors[i], alpha=0.9)

            ax.set_title('CVaR Portfolio Weight Evolution', fontsize=14, fontweight='bold', pad=15)
            ax.set_xlabel('Rebalancing Date', fontsize=12)
            ax.set_ylabel('Weight Allocation (%)', fontsize=12)
            ax.set_ylim(0, 80)
            ax.grid(True, alpha=0.3, linestyle='--')

            # Add horizontal lines for min/max constraints
            ax.axhline(y=10, color='red', linestyle=':', alpha=0.5, linewidth=1.5)
            ax.axhline(y=70, color='red', linestyle=':', alpha=0.5, linewidth=1.5)

            # Add text labels for constraints
            ax.text(len(x_positions)-1, 11, 'Min Constraint (10%)',
                   ha='right', va='bottom', fontsize=9, color='red', alpha=0.7)
            ax.text(len(x_positions)-1, 69, 'Max Constraint (70%)',
                   ha='right', va='top', fontsize=9, color='red', alpha=0.7)

            ax.legend(loc='best', frameon=True, fancybox=True, shadow=True, fontsize=10)

            # Set x-axis labels (show every nth label to avoid crowding)
            n_labels = len(x_labels)
            if n_labels > 10:
                step = max(1, n_labels // 10)
                visible_positions = x_positions[::step]
                visible_labels = x_labels[::step]
                # Always include the last label
                if x_positions[-1] not in visible_positions:
                    visible_positions = list(visible_positions) + [x_positions[-1]]
                    visible_labels = list(visible_labels) + [x_labels[-1]]
            else:
                visible_positions = x_positions
                visible_labels = x_labels

            ax.set_xticks(visible_positions)
            ax.set_xticklabels(visible_labels, rotation=45, ha='right')

            plt.tight_layout()

            # Save figure
            import os
            output_path = os.path.join(output_dir, 'weight_evolution.png')
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()  # Close the figure to free memory
            self.log(f"Weight evolution chart saved to: {output_path}")

        except Exception as e:
            self.log(f"Error creating weight evolution chart: {e}")

    def _create_weight_tables(self, data, output_dir):
        """Create weight evolution tables in CSV format"""
        try:
            # Extract data
            weight_history = np.array(data['weight_history'])
            dates = data['dates']

            # Create weight evolution table
            csv_data = []
            for i, (date, weights) in enumerate(zip(dates, weight_history)):
                csv_data.append({
                    'Rebalance #': i,
                    'Date': date if date != 'Initial' else 'Initial',
                    'Series 04 (%)': f"{weights[0]*100:.1f}",
                    'Series 05 (%)': f"{weights[1]*100:.1f}",
                    'Series 09 (%)': f"{weights[2]*100:.1f}"
                })

            # Save to CSV
            import os
            csv_path = os.path.join(output_dir, 'weight_evolution_table.csv')

            # Write CSV manually to avoid pandas dependency
            with open(csv_path, 'w') as f:
                # Write header
                f.write('Rebalance #,Date,Series 04 (%),Series 05 (%),Series 09 (%)\n')
                # Write data rows
                for row in csv_data:
                    f.write(f"{row['Rebalance #']},{row['Date']},{row['Series 04 (%)']},{row['Series 05 (%)']},{row['Series 09 (%)']}\n")

            self.log(f"Weight evolution table saved to: {csv_path}")

            # Create summary statistics
            weight_array = np.array(weight_history)
            summary_path = os.path.join(output_dir, 'weight_summary_statistics.csv')

            with open(summary_path, 'w') as f:
                # Write header
                f.write('Asset,Initial Weight (%),Final Weight (%),Mean Weight (%),Std Dev (%),Min Weight (%),Max Weight (%)\n')
                # Write data for each asset
                for i, asset in enumerate(['Series 04', 'Series 05', 'Series 09']):
                    initial = f"{weight_history[0][i]*100:.1f}"
                    final = f"{weight_history[-1][i]*100:.1f}"
                    mean = f"{np.mean(weight_array[:, i])*100:.1f}"
                    std = f"{np.std(weight_array[:, i])*100:.1f}"
                    min_w = f"{np.min(weight_array[:, i])*100:.1f}"
                    max_w = f"{np.max(weight_array[:, i])*100:.1f}"
                    f.write(f"{asset},{initial},{final},{mean},{std},{min_w},{max_w}\n")

            self.log(f"Weight summary statistics saved to: {summary_path}")

        except Exception as e:
            self.log(f"Error creating weight tables: {e}")