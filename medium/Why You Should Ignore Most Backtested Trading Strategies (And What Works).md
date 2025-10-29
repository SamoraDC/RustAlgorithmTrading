Why You Should Ignore Most Backtested Trading Strategies (And What Works)
Mr. Q
Mr. Q

Follow
5 min read
·
Jun 18, 2025
300


7





To be more precise, while the title is limited in length, what I truly mean are strategies driven by daily price data — whether through technical indicators or time-series-based machine learning techniques.

Press enter or click to view image in full size

Let’s cut to the chase: if you come across a shiny backtest based solely on price data and technical indicators — or worse, a machine learning model that claims to predict future prices — close the tab.

As someone who spent over a decade at the world’s largest financial data provider, I’ve seen it all. These models look impressive on paper, but they’re riddled with bias, overfitting, and most importantly, fantasy. Here’s the truth: price data alone is not enough. It never has been, and it never will be.

The Harsh Truth About Price-Based Strategies
Don’t get me wrong. If you’re a student or hobbyist, experimenting with moving averages or neural nets on price data is a great learning exercise. You’re sharpening your coding skills, learning about time series, and that’s all valuable. But if you think you’re building a system that can consistently beat the market? You’re not.

Here’s why:

1. Price Doesn’t Tell the Whole Story
Price reflects past decisions, not future insights. It’s noisy, delayed, and missing crucial market signals. By the time you “see” something in price, it’s already been seen and acted on by pros with much better tools.

2. Time Series Prediction Is a Dead End
Every time someone talks about “predicting future prices,” it’s a clear signal that they don’t understand how real trading works. Prices behave like a random walk — this is finance 101. Most professional quants don’t forecast price; they estimate relative expected returns for portfolio construction.

Trying to predict where the price will go next is like trying to predict the next coin toss after ten heads. It looks like there’s a pattern — but there isn’t.

3. Free Data Is Garbage
Download free data from Yahoo Finance, and you’ll quickly find bad prints, incorrect dividend adjustments, and mismatched timestamps. Your model may be working off fiction, not facts.

4. Backtests Don’t Include Real Costs
Slippage, spread, commissions, liquidity constraints, currency conversion — none of that is captured in a naive backtest. Once you account for real-world trading friction, that dreamy 35% CAGR collapses below the S&P 500.

5. Most Indicators Are Regime-Dependent
Technical indicators work… until they don’t. A strategy built on RSI or MACD may do great in a trending market and crash during a choppy one. You can’t “adapt” fast enough without bleeding through the regime shift. And by the time your model figures out the regime has changed, you’ve already lost your gains.

But Don’t Give Up — Here’s What Does Work
Despite all that, there are strategies that work. And not just for billion-dollar hedge funds. One in particular has stood the test of time:

Press enter or click to view image in full size

See this tiny bit of 10.11% (circled in blue). This is Stat Arb performance. 10.11% is the performance and it’s small because it only counts $12bln AUM, which is also why our opportunity.

Statistical Arbitrage
Stat arb isn’t about predicting prices. It’s about identifying temporary mispricings between correlated instruments — pairs, baskets, sectors — and betting they’ll revert. You’re not trying to outguess the market. You’re making a probabilistic bet that historical relationships will hold over the short term.

Why Stat Arb Makes Sense for Retail Traders
Limited Opportunity = Limited Competition
Institutions don’t dominate this space because stat arb doesn’t scale. You can’t deploy billions into a pair trade without affecting the market. That’s great news for individuals. It means the pond is still fishable — if you use the right bait.
High Alpha Density
When done right — with rigorous data cleaning, modelling, and execution — stat arb delivers real alpha. It’s not a magic bullet, but it’s one of the few retail-accessible strategies that can generate positive expectancy after costs.
The Data Problem
One caveat: some stat arb requires granular data — think tick-by-tick, venue-level trade data, and more. This stuff isn’t free. It costs hundreds of thousands per year for professionals. So let’s try those strategies that we can do with limited data, but ideally, data from the trading platform directly, not Yahoo Finance.

NOT Silver Bullet
Stat Arb is good at performing consistently, although it requires sophisticated knowledge of maths and statistics, as well as good programming skills to quickly identify the opportunities from a large universe. But we can do it, and it should be good news for us, i.e. not all people can do so.

However, Stat Arb is NOT good at taking the big waves, i.e. when we see other strategies taking advantage of the market directional move, Stat Arb is not likely to take off. For example, 2024 Nov. Or put in this way, it’s more Alpha, not much Beta.

Press enter or click to view image in full size

Final Thoughts
If you’re day trading off free data and 14-day RSI, hoping for a breakout, you’re not trading — you’re gambling. If you want to play the real game, you need to respect the rules of professional quant trading:

Garbage in = garbage out.
Backtest realism matters more than backtest returns.
Strategies should be built on robust market behaviours, not visual patterns.
The market is smarter than you, faster than you, and better funded than you. So go where the institutions can’t. Trade where the inefficiencies still exist. And remember: the edge isn’t in the tool or the chart — it’s in your understanding of the market’s structure.