"""
CVaR (Conditional Value at Risk) Portfolio Optimization
Used for Part 2 combined strategy design
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')

class CVaROptimizer:
    """
    CVaR-based portfolio optimization for combining multiple trading strategies.
    
    CVaR (Conditional Value at Risk) minimizes the expected loss in the worst-case scenarios,
    providing better downside risk management compared to traditional mean-variance optimization.
    """
    
    def __init__(self, confidence_level=0.05, lookback_days=60):
        """
        Initialize CVaR optimizer
        
        Parameters:
        - confidence_level: Confidence level for CVaR calculation (default 5% = 95% VaR)
        - lookback_days: Number of days to look back for returns calculation
        """
        self.confidence_level = confidence_level
        self.lookback_days = lookback_days
        
    def calculate_cvar(self, returns, weights, confidence_level=None):
        """
        Calculate CVaR for given portfolio weights
        
        CVaR = E[Loss | Loss >= VaR_α]
        Where VaR_α is Value at Risk at confidence level α
        """
        if confidence_level is None:
            confidence_level = self.confidence_level
            
        # Calculate portfolio returns
        portfolio_returns = np.dot(returns, weights)
        
        # Calculate VaR (negative because we want losses)
        var = np.percentile(portfolio_returns, confidence_level * 100)
        
        # Calculate CVaR (expected value of losses beyond VaR)
        losses_beyond_var = portfolio_returns[portfolio_returns <= var]
        
        if len(losses_beyond_var) == 0:
            return var  # If no losses beyond VaR, return VaR
        
        cvar = np.mean(losses_beyond_var)
        return cvar
    
    def objective_function(self, weights, returns):
        """
        Objective function for CVaR minimization
        We want to minimize CVaR (maximize the negative CVaR)
        """
        return -self.calculate_cvar(returns, weights)  # Minimize negative CVaR
    
    def optimize_weights(self, returns_matrix, initial_weights=None, min_weight=0.0, max_weight=1.0):
        """
        Optimize portfolio weights to minimize CVaR
        
        Parameters:
        - returns_matrix: numpy array of shape (n_periods, n_strategies)
        - initial_weights: starting weights (if None, use equal weights)
        - min_weight: minimum weight for each strategy
        - max_weight: maximum weight for each strategy
        
        Returns:
        - optimal_weights: array of optimal weights
        - optimization_result: scipy optimization result
        """
        n_strategies = returns_matrix.shape[1]
        
        # Initial weights (equal allocation if not provided)
        if initial_weights is None:
            initial_weights = np.ones(n_strategies) / n_strategies
        
        # Constraints
        constraints = [
            # Weights sum to 1
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}
        ]
        
        # Bounds (each weight between min_weight and max_weight)
        bounds = [(min_weight, max_weight) for _ in range(n_strategies)]
        
        # Optimization
        result = minimize(
            fun=self.objective_function,
            x0=initial_weights,
            args=(returns_matrix,),
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'ftol': 1e-9, 'disp': False}
        )
        
        if not result.success:
            print(f"Warning: CVaR optimization did not converge. Using equal weights.")
            return np.ones(n_strategies) / n_strategies, result
        
        return result.x, result
    
    def calculate_portfolio_metrics(self, returns_matrix, weights):
        """
        Calculate comprehensive portfolio metrics
        """
        portfolio_returns = np.dot(returns_matrix, weights)
        
        metrics = {
            'total_return': np.sum(portfolio_returns),
            'annualized_return': np.mean(portfolio_returns) * 252,
            'volatility': np.std(portfolio_returns) * np.sqrt(252),
            'sharpe_ratio': (np.mean(portfolio_returns) * 252) / (np.std(portfolio_returns) * np.sqrt(252)) if np.std(portfolio_returns) > 0 else 0,
            'max_drawdown': self.calculate_max_drawdown(portfolio_returns),
            'var_5pct': np.percentile(portfolio_returns, 5),
            'cvar_5pct': self.calculate_cvar(returns_matrix, weights, 0.05),
            'var_1pct': np.percentile(portfolio_returns, 1),
            'cvar_1pct': self.calculate_cvar(returns_matrix, weights, 0.01),
        }
        
        return metrics
    
    def calculate_max_drawdown(self, returns):
        """Calculate maximum drawdown from returns series"""
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        return np.min(drawdown)
    
    def rolling_optimization(self, returns_matrix, rebalance_frequency=20):
        """
        Perform rolling CVaR optimization with periodic rebalancing
        
        Parameters:
        - returns_matrix: numpy array of shape (n_periods, n_strategies)
        - rebalance_frequency: rebalance every N days
        
        Returns:
        - weights_history: array of weights over time
        - portfolio_returns: array of portfolio returns
        """
        n_periods, n_strategies = returns_matrix.shape
        weights_history = np.zeros((n_periods, n_strategies))
        current_weights = np.ones(n_strategies) / n_strategies
        
        for i in range(self.lookback_days, n_periods):
            # Rebalance periodically
            if i % rebalance_frequency == 0 or i == self.lookback_days:
                # Use lookback window for optimization
                start_idx = max(0, i - self.lookback_days)
                historical_returns = returns_matrix[start_idx:i]
                
                if len(historical_returns) >= 20:  # Minimum data requirement
                    optimal_weights, _ = self.optimize_weights(historical_returns, current_weights)
                    current_weights = optimal_weights
            
            weights_history[i] = current_weights
        
        # Calculate portfolio returns
        portfolio_returns = np.sum(returns_matrix * weights_history, axis=1)
        
        return weights_history, portfolio_returns
    
    def compare_strategies(self, returns_matrix, strategy_names):
        """
        Compare different allocation strategies: Equal Weight vs CVaR Optimal
        """
        n_strategies = returns_matrix.shape[1]
        
        # Equal weight allocation
        equal_weights = np.ones(n_strategies) / n_strategies
        equal_metrics = self.calculate_portfolio_metrics(returns_matrix, equal_weights)
        
        # CVaR optimal allocation
        optimal_weights, opt_result = self.optimize_weights(returns_matrix)
        cvar_metrics = self.calculate_portfolio_metrics(returns_matrix, optimal_weights)
        
        # Results summary
        comparison = {
            'strategy_names': strategy_names,
            'equal_weight': {
                'weights': equal_weights,
                'metrics': equal_metrics
            },
            'cvar_optimal': {
                'weights': optimal_weights,
                'metrics': cvar_metrics,
                'optimization_success': opt_result.success
            },
            'improvement': {
                'cvar_reduction': cvar_metrics['cvar_5pct'] - equal_metrics['cvar_5pct'],
                'return_change': cvar_metrics['total_return'] - equal_metrics['total_return'],
                'sharpe_improvement': cvar_metrics['sharpe_ratio'] - equal_metrics['sharpe_ratio']
            }
        }
        
        return comparison