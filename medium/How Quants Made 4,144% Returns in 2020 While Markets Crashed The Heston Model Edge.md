How Quants Made 4,144% Returns in 2020 While Markets Crashed: The Heston Model Edge
Navnoor Bawa
Navnoor Bawa

Following
7 min read
·
Sep 1, 2025
125


3





The mathematical model that revealed volatility’s true nature — and turned market panic into massive profits
📖 Read this article FREE on Substack: How Quants Made 4,144% Returns in 2020 While Markets Crashed: The Heston Model Edge

Press enter or click to view image in full size

Bottom Line Up Front: While most traders lost fortunes during March 2020’s market crash, Mark Spitznagel’s hedge fund generated 4,144% returns in a single quarter by understanding what the Heston model reveals about volatility’s true behavior. The model’s core insight — that volatility itself is volatile and mean-reverting — enabled sophisticated quants to profit from the market’s fundamental mispricing of tail risk.

On March 16, 2020, the VIX exploded to 82.69 — one of the highest readings in its history, with an even more extreme intraday peak of 85.47 reached on March 18. The S&P 500 lost one-third of its value between February 20 and March 23, 2020, while implied volatility skyrocketed to levels previously thought impossible. Most investors panicked. But quantitative researchers who truly understood the Heston model saw something else entirely: the largest volatility arbitrage opportunity in a generation.

Mark Spitznagel’s Universa Investments hedge fund posted a 4,144% return in Q1 2020 using strategies that fundamentally depend on the Heston model’s insights about stochastic volatility. This wasn’t luck — it was the mathematical inevitability of understanding how volatility really behaves.

Why Black-Scholes Failed When It Mattered Most
The traditional Black-Scholes model assumes constant volatility — a fatal flaw that becomes glaringly obvious during market stress. The volatility smile was considered rare before the 1987 crash. However, after the crash, traders realised that out-of-the-money options, although rare, could occur. Black-Scholes simply couldn’t explain why options with identical underlying assets but different strikes traded at vastly different implied volatilities.

The March 2020 Reality Check:

VIX reached extreme levels during mid-March 2020, with 82.69 on March 16 and an intraday peak of 85.47 on March 18
Options across all strikes exhibited severe volatility smile distortions
These volatility spikes coincided almost perfectly with the market bottom
Black-Scholes couldn’t capture any of these phenomena. The Heston model, however, was built specifically for moments like these.

The Heston Model’s Revolutionary Insight
The Heston model assumes that the volatility of the asset is not constant, nor even deterministic, but follows a random process. More specifically, it models volatility using three key properties that proved crucial during COVID-19:

1. Volatility Clustering
Volatility comes in waves. High volatility periods cluster together, followed by calm periods. The model captures this through its stochastic volatility process:


Where:

κ controls the speed of mean reversion
θ represents the long-term variance level
σ captures the volatility of volatility (“vol-of-vol”)
2. Mean Reversion with Leverage Effect
The correlation parameter ρ in the model captures the “leverage effect” — a drop in the asset price will see an increase in volatility. During March 2020, this correlation went strongly negative as falling stocks drove volatility higher.

3. The Vol-of-Vol Parameter
The σ parameter — volatility of volatility — becomes critical during crises. It determines the variance of νt and allows the model to capture extreme volatility movements that Black-Scholes simply cannot handle.

How the Trade Actually Worked: Variance Swaps and Volatility Arbitrage
The key to understanding how quants made massive profits lies in variance swaps — derivatives that allow direct betting on realized vs. implied volatility. The quoted strike is determined by the implied volatility smile in the options market, whereas the ultimate payout will be based upon actual realized variance.

The Setup (Pre-March 2020):
Historically, implied variance has been above realized variance, a phenomenon known as the variance risk premium
Most hedge funds were systematically short volatility, collecting this premium
Volatility arbitrage strategies can differ greatly in their implementation, influenced by factors such as whether the approach is discretionary or systematic
The Heston Model’s Warning Signals:
February 2020: Calibrating the Heston model to market prices revealed:

Extremely low vol-of-vol pricing: The market was pricing future volatility moves as unusually constrained
Compressed volatility surface: Out-of-the-money puts were relatively cheap compared to historical patterns
Mean reversion parameter breakdown: The model indicated that volatility was due for a major regime shift
The Execution:
Sophisticated funds like Universa didn’t just buy VIX calls. They implemented complex strategies that the Heston model made possible:

Variance Swap Long Positions: Using the Heston model, a closed-form solution can be derived for the fair variance swap rate. When market implied variance was trading below the Heston model’s predicted fair value, smart money went long variance.

Volatility Surface Arbitrage: The Heston model revealed mispricing across the entire options surface. Traders attempt to buy volatility when it is low and sell volatility when it is high by constructing delta-neutral portfolios that profit from volatility changes regardless of directional moves.

Dynamic Hedging: Monte Carlo simulations indicate that the Heston model significantly improves hedging performance at weekly and longer hedging intervals, when compared to continuous time hedging procedures.

The Payoff: When Math Met Market Panic
Mid-March 2020: As the VIX spiked to historic levels — reaching 82.69 on March 16 and an intraday peak of 85.47 on March 18 — sophisticated traders who had positioned for increased volatility captured massive profits.

How the Numbers Worked:
Variance swap payoffs: If you bought a 1-month variance swap at 400 (20% annualized vol) in February, and March realized variance hit 6,400 (80% annualized), the payoff was 6,000 basis points per $1 million notional
Options positions: Deep out-of-the-money puts that cost pennies suddenly became worth dollars
VIX futures: Front-month contracts that traded at 15 in January spiked to over 80
The Heston Edge:
What separated the winners from the losers wasn’t just holding volatility — it was understanding how volatility behaves. The Heston model became particularly relevant with its ability to capture stochastic volatility and the correlation between asset price and volatility during volatile market conditions.

Specific Trading Applications: Beyond Theory
Variance Swap Pricing and Hedging
The calibration of the Heston model is often formulated as a least squares problem, with the objective function minimizing the squared difference between the prices observed in the market and those calculated from the model. Real-world implementation requires:

Daily recalibration: Parameters κ (mean reversion speed), θ (long-term variance), σ (vol-of-vol), and ρ (correlation) updated based on market data
Greeks calculation: Real-time sensitivity analysis for delta-neutral portfolio management
Term structure modeling: Forward-start variance swaps with discrete sampling times
Dispersion Trading
Dispersion trading aims to profit from pricing differences between index options and options on individual stocks within the same index. The Heston model enables:

Identifying when index volatility is rich/cheap relative to single-stock volatilities
Constructing correlation trades that profit from volatility regime changes
Managing the complex Greeks in multi-name volatility portfolios
VIX and Vol-of-Vol Strategies
Some managers engage in strategies trading the S&P 500 index against the VIX, capitalizing on the historical correlation between the indices. Advanced strategies include:

VIX options trading: “Vol of vol” instruments enable trading second-order volatility movements
Term structure arbitrage: Exploiting mispricing between VIX futures of different maturities
Systematic volatility strategies: Algorithmically shorting volatility during low-vol regimes while maintaining tail hedges
Risk Management: When Models Break Down
The Heston model isn’t perfect. It assumes frictionless markets with perfect liquidity, which may not reflect the reality of financial markets. During March 2020:

Model Limitations Exposed:
Liquidity constraints: Bid-ask spreads widened dramatically during the crisis
Jump risk: The Heston model does not explicitly account for sudden jumps in asset prices
Parameter instability: Rapid regime changes made real-time calibration challenging
Risk Management Protocols:
Position sizing: Universa’s approach used approximately 3.33% allocation to tail-risk strategies
Diversification: Volatility arbitrage strategies exhibit the lowest intra-strategy correlations relative to other hedge fund strategies
Dynamic hedging: Even sophisticated tail-risk strategies require continuous risk management
The Broader Lesson: Mathematical Models as Competitive Advantages
The March 2020 crisis demonstrated a fundamental truth: sophisticated mathematical models aren’t just academic exercises — they’re competitive advantages that can generate extraordinary returns when markets stress-test every assumption.

COVID-19 created profitable opportunities for traders and speculators, benefiting those who had plenty of liquidity at hand. But more importantly, it rewarded those who understood the mathematical reality underlying market volatility.

The Heston model’s success during this period wasn’t about predicting the pandemic — it was about understanding that volatility is itself an asset class with predictable statistical properties. When the market panicked and abandoned rational pricing, quants who understood these properties were positioned to profit enormously.

Key Takeaways for Building Quantitative Edge:
Mathematical sophistication matters: Simple models fail during the most profitable opportunities

Implementation is everything: Having the model is just the beginning — execution determines P&L

Risk management enables opportunity: Proper position sizing allows you to survive until the big payoffs arrive

Market structure awareness: Understanding how volatility products actually trade is crucial

Continuous learning: Markets evolve, and models must evolve with them

What This Means for Today’s Quant Researchers
The Heston model’s triumph in March 2020 offers crucial lessons for building quantitative depth:

Model sophistication creates opportunity: When everyone else relies on Black-Scholes, understanding stochastic volatility becomes a competitive moat.

Parameter sensitivity matters: The difference between κ = 2.0 and κ = 3.0 can mean the difference between profit and loss in volatility arbitrage.

Real-time calibration is critical: Markets don’t wait for your monthly parameter updates. The quants who win are those who can recalibrate in real-time.

Cross-asset applications: The principles that worked in equity volatility during COVID-19 apply to FX options, commodity volatility, and crypto derivatives.

The next time volatility spikes — and it will — remember that behind the chaos lies mathematical structure. The quants who understand that structure, through models like Heston, will be the ones collecting extraordinary returns while others panic.

About this series: I’m building a public archive of technical finance case studies that explain how hedge funds actually make money. Each post emphasizes conceptual depth, mathematical rigor, and real-world profit drivers. Follow for more quantitative insights that cut through the noise.