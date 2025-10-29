We Backtested a Viral Trading Strategy. The Results Will Teach You a Lesson.
Richard Shu
Richard Shu

Follow
6 min read
·
Oct 3, 2025
294


9





From a 5,394% “Profit” to a Genuinely Robust ML System
Press enter or click to view image in full size
QQQ Price Chart
QQQ Price Chart, Image by Author
If you’ve spent any time in the world of online trading, you’ve seen them: articles and videos promising spectacular returns with a “secret” combination of indicators. They show you a backtest on a hot stock like TSLA, and the equity curve goes straight to the moon.

We recently came across one such article: “Kaufman Adaptive Moving Average and ATR Long Position Strategy.” It presented a compelling idea: use the adaptive KAMA for trend-following and the ATR for volatility-based risk control. The results on TSLA were staggering: a 5,394% profit, crushing buy-and-hold.

But as experienced engineers, we know that extraordinary claims require extraordinary evidence. So, we asked the crucial question: Does this strategy hold up under a rigorous, professional backtesting process?

This is the story of how we took that promising-but-flawed idea, subjected it to the robust testing of our open-source framework, AlphaSuite, and transformed it into a genuinely profitable machine learning strategy.

Part 1: The Inevitable Disappointment
Our first step was to replicate the article’s rule-based logic within AlphaSuite. The rules were simple:

Enter: When the price is above KAMA and volatility (ATR %) is within a “calm” range.
Exit: When the price crosses below KAMA or volatility spikes.
We ran this against QQQ using a standard walk-forward analysis. This method, unlike the article’s full-dataset optimization, simulates real-world trading by training on past data and testing on unseen future data.

The results were… underwhelming. The strategy barely made any money and had a Sharpe ratio near zero.

Why the massive difference?

The Overfitting Trap: The original article optimized its parameters on the entire historical dataset. This is a cardinal sin in quantitative finance called curve-fitting. The “perfect” parameters were tailored with perfect hindsight, making the results completely unrealistic.
Unrealistic Risk Management: The original backtest was simplistic, likely using an “all-in” approach. Our framework enforces disciplined position sizing and stop-losses, which prioritizes capital preservation over chasing lottery-ticket returns.
Cherry-Picking: The article highlighted extreme momentum stocks like TSLA and MSTR. A robust strategy must work across different assets and market conditions, not just on a few outliers.
The verdict was clear: the original rule-based strategy, as presented, was not viable for real-world trading.

Part 2: The Pivot to Machine Learning
Instead of abandoning the core concept, we decided to pivot. The idea of combining an adaptive trend (KAMA) with a volatility filter (ATR) was still sound. The problem was the rigid, over-optimized rules.

What if, instead of hard-coding rules, we used these indicators as features for a machine learning model to learn from?

This transformed our approach:

Feature Engineering: We created a set of normalized features to describe the market state.
Target Labeling: We defined what a “good” trade looks like using the Triple-Barrier Method.
Training the Model: We used the integrated ML pipeline in AlphaSuite to train a LightGBM model to find winning patterns.
The strategy was no longer a brittle set of “if-then” statements. It was now a flexible system capable of learning and adapting.

The Devil is in the Details: Key Calculations
To truly understand the transformation, let’s look at the code. The journey from a flawed rule to a robust feature involved several critical calculations.

1. Engineering Robust Features
The biggest leap came from how we created features. Raw indicator values are often useless for models learning from long-term data. For example, a MACD value of $2.00 is huge when a stock is at $50, but meaningless when it’s at $500.

We solved this by normalizing the features, creating signals that are independent of the price level.

# Normalizing MACD by price to make it comparable over time
data['feature_macdhist'] = data['macd_hist'] / data['close']

# Scaling RSI to a consistent 0-1 range
data['feature_rsi'] = data['rsi'] / 100.0

# Calculating the percentage distance from a moving average
data['feature_price_kama_dist'] = (data['close'] / data['kama']) - 1
This gives the model a consistent signal to learn from, whether it’s looking at data from 2005 or 2025.

2. Defining a “Win” with the Triple-Barrier Method
How do we teach the model what a good trade is? We use the “Triple-Barrier Method.” For each potential trade, we set three barriers into the future:

A profit target (e.g., 3x the Average True Range)
A stop-loss (e.g., 3x the Average True Range)
A time limit (e.g., 15 days)
The first barrier hit determines the outcome.

# Simplified logic for labeling a trade
profit_target = entry_price + (atr_at_entry * profit_target_multiplier)
stop_loss = entry_price - (atr_at_entry * stop_loss_multiplier)

# Look into the future N bars
future_bars = data.loc[i:].iloc[1:eval_bars + 1]

# Check if profit target was hit
pt_hit_mask = future_bars['high'] >= profit_target
pt_hit_date = future_bars.index[pt_hit_mask].min()

# Check if stop loss was hit
sl_hit_mask = future_bars['low'] <= stop_loss
sl_hit_date = future_bars.index[sl_hit_mask].min()

# A win occurs only if the profit target is hit before the stop loss.
if pd.notna(pt_hit_date) and (pd.isna(sl_hit_date) or pt_hit_date < sl_hit_date):
    target.loc[i] = 1.0  # Win
else:
    target.loc[i] = 0.0  # Loss (stop-loss or time-out)Part 3: The Results — From Hype to a Real Edge
We ran the new ML strategy through the same rigorous walk-forward optimization on QQQ. The results were a world apart.

Sharpe Ratio: A solid 0.90
Total Return (Out-of-Sample): 376%
Max Drawdown: A very manageable -16.4%
Interestingly, when we ran a full in-sample backtest (using a single set of optimized parameters over the entire 25-year period), the strategy returned 791%, handily beating the 631% buy-and-hold return for the same period. This shows the strategy’s theoretical potential under a stable parameter set.

Press enter or click to view image in full size
Equity Curve for QQQ
Equity Curve for QQQ, Image by Author
However, the more realistic 376% out-of-sample return is the number we trust. While it underperformed a perfect-hindsight buy-and-hold strategy across the test periods, it achieved this with a fraction of the risk. It successfully navigated major market downturns, preserving capital while a passive investor would have faced devastating losses. This is the trade-off at the heart of professional strategy design: sacrificing some potential upside for a massive reduction in risk.

But the most fascinating insight came from the feature importance plot, which tells us what the model “thinks” is most important:

feature_atr_pct (Highest Importance): The model's most critical factor was market volatility. It learned to be highly selective, confirming the original article's core idea in a data-driven way.
feature_price_sma200_dist: The long-term trend filter was the second most important, proving the model learned not to fight the primary trend.
feature_macdhist: The MACD histogram, a measure of momentum acceleration, was also highly valued for timing entries.
The model had validated the initial concept but had discovered a far more nuanced and robust way to execute it.

Press enter or click to view image in full size
Feature Importances (Averaged Across Folds)
Feature Importances (Averaged Across Folds), Image by Author
Your Turn: Stop Curve-Fitting, Start Building
This journey from a flawed rule-based strategy to a robust ML system highlights the core principles of modern quantitative research:

Be Skeptical: Treat “perfect” backtests with extreme suspicion.
Test Rigorously: Walk-forward analysis and realistic risk management are non-negotiable.
Iterate and Adapt: Don’t be afraid to pivot from a rigid idea to a more flexible, data-driven approach.
This entire process was made possible by our open-source project, AlphaSuite, a Python framework designed for the rapid development and rigorous testing of quantitative trading strategies. It provides the tools — from data processing and feature engineering to walk-forward optimization and ML integration — that allow you to focus on what matters: finding a genuine, durable edge. As a follow-up, we published a step-by-step guide to walk you through the entire workflow, from data preparation to signal generation, using the very same KamaAtrStrategy as example.

If you’re tired of chasing over-optimized strategies and want to start building systems that hold up in the real world, we invite you to join us.

Check out the AlphaSuite project on GitHub and begin your own journey from hype to reality.