QOADRS Mathematical Implementation: A Step-by-Step Breakdown of Quantum Options Anomaly Detection
Navnoor Bawa
Navnoor Bawa

Following
6 min read
·
Jun 12, 2025
13






How we achieved 90.7% accuracy processing 9,462 real options contracts using quantum-enhanced machine learning

Press enter or click to view image in full size

GitHub Repository: https://github.com/NavnoorBawa/Quantum-Options-Anomaly-Detection-Research-System-QOADRS-/tree/main

Disclaimer: This project is purely educational. No part of this article constitutes financial or investment advice. The strategies discussed are demonstrated for educational purposes only.

After building and deploying QOADRS (Quantum Options Anomaly Detection Research System) on live S&P 500 options data, I’m sharing the complete mathematical implementation that enabled us to achieve genuine quantum advantage in financial anomaly detection. This technical deep dive walks through every mathematical transformation in our production system.

This article builds upon my previous work detailing the complete system results and performance analysis. Here, we focus exclusively on the mathematical foundations and step-by-step implementation.

System Overview: From Raw Data to Quantum Detection
QOADRS processes real-time options data through a 13-phase mathematical pipeline, transforming financial contracts into quantum states for anomaly detection. Here’s what we actually built:

Performance Metrics (June 9, 2025 Analysis):

Stocks Analyzed: 50 S&P 500 companies
Options Contracts: 9,462 processed
Model Accuracy: 90.7% (exceeding 90% quantum advantage threshold)
Data Quality: 100% (multi-source validation)
Processing Time: 93 minutes training + real-time analysis
Phase 1: Multi-Source Data Integration Mathematics
Professional Data Pipeline
Our system integrates three data sources with mathematical quality scoring:

data_quality = (yfinance_score × 0.4) + (polygon_score × 0.4) + (alphavantage_score × 0.2)
Asset-Specific Bounds Implementation:

SPY/QQQ/DIA: IV ∈ [0.08, 0.50] (8%-50%)
AAPL/MSFT/GOOGL: IV ∈ [0.10, 0.70] (10%-70%)
Individual Stocks: IV ∈ [0.10, 1.00] (10%-100%)
Real Result Example (AAPL):

YFinance: 317 contracts, IV: 0.43 ✓
Polygon.io: 80 contracts ✓
Alpha Vantage: 70 contracts ✓
Combined: 166 contracts, Quality Score: 1.0
Phase 2: Advanced Feature Engineering Mathematics
12-Feature Extraction Pipeline
For each options contract, we extract these mathematically defined features:

Input Contract Example:

Strike (K) = 120, Spot (S) = 150, IV = 0.35, T = 60 days
Volume = 800, OI = 50, Bid = 1.5, Ask = 1.8
Mathematical Transformations:

1. Moneyness: f₁ = K/S = 120/150 = 0.80

2. Bid-Ask Spread:

f₅ = ((ask - bid) / ((ask + bid)/2)) × 100
f₅ = (1.8-1.5) / 1.65 × 100 = 18.18%
3. Log Volume: f₄ = log(volume + 1) = log(801) = 6.685

4. Time to Expiration: f₃ = days/365 = 60/365 = 0.164

5. Greeks (Black-Scholes):

Delta: f₆ = N(d₁) ≈ 0.65
Gamma: f₇ = φ(d₁)/(S₀σ√T) ≈ 0.05
Theta: f₈ = -S₀φ(d₁)σ/(2√T) ≈ -0.05
Vega: f₉ = S₀φ(d₁)√T ≈ 0.15
Phase 3: Quantum Volatility Surface Encoding
6-Qubit Quantum State Preparation
The core innovation: encoding options data into quantum rotation angles using volatility surface mathematics.

Quantum Encoding Formula:

θᵢⱼ = arctan(V(Kᵢ,Tⱼ) × √(Tⱼ) × |M - 1|)
Where:

V(K,T) = implied volatility
T = time to expiration
M = moneyness
For our example:

θ = arctan(0.35 × √0.164 × |0.80 - 1|)
θ = arctan(0.35 × 0.405 × 0.20) = 0.0283 radians
6-Qubit State Encoding:

|ψ⟩ = R_Y(f₁) ⊗ R_Y(f₂) ⊗ R_Y(f₃) ⊗ R_Y(f₄) ⊗ R_Y(f₅) ⊗ R_Y(f₆)
Variational Quantum Circuit Implementation
3-Layer Processing: For each layer l ∈ {1,2,3} and qubit i ∈ {0,1,2,3,4,5}:

U_l(θ) = R_X(θₗᵢ₁) · R_Y(θₗᵢ₂) · R_Z(θₗᵢ₃)
Entanglement Pattern:

CNOT(q₀,q₁) → CNOT(q₁,q₂) → CNOT(q₂,q₃) → CNOT(q₃,q₄) → CNOT(q₄,q₅)
Total Parameters: 3 layers × 6 qubits × 3 rotations = 54 trainable parameters

Phase 4: SWAP Test Anomaly Detection
Mathematical Implementation
The SWAP test measures quantum fidelity between states for anomaly detection:

Circuit Implementation:

Initialize auxiliary qubit: H|0⟩ = (|0⟩ + |1⟩)/√2
Controlled SWAP operations:
CSWAP(aux, q₀, q₃) → CSWAP(aux, q₁, q₄) → CSWAP(aux, q₂, q₅)
3. Final Hadamard on auxiliary: H

4. Measure auxiliary qubit

Probability Calculation:

P(0) = (1 + |⟨ψ_encoded|ψ_reference⟩|²) / 2
Fidelity Measurement:

F = 2P(0) - 1
Real Training Results:

Training Duration: 93 minutes 37 seconds (150 epochs)
Best Accuracy: 90.7%
Quantum Fidelity: 0.85+ average across measurements
Phase 5: Ensemble Detection Mathematics
Three-Model Architecture
1. Quantum SVM Processing

Quantum Kernel Function:

K_quantum(x₁, x₂) = |⟨φ(x₁)|φ(x₂)⟩|²
Decision Function:

f(x) = sign(∑ᵢ αᵢ yᵢ K_quantum(xᵢ, x) + b)
2. Quantum K-Means Clustering

Quantum Distance Metric:

d_quantum(x, cₖ) = ||φ(x) - φ(cₖ)||²
Percentile Threshold: 95th percentile = 0.65

3. Quantum Autoencoder Scoring

Reconstruction Error:

MSE = (1/n) ∑ᵢ (xᵢ - x̂ᵢ)²
Anomaly Threshold: 0.5 (learned during training)

Ensemble Voting Mathematics
Example Decision Process:

Models: [QSVM, K-Means, Autoencoder]
Votes: [True, True, False]
Majority Decision: count(True)/3 = 2/3 > 0.5 → ANOMALOUS
Confidence Weighting:

weighted_score = (qsvm_conf × qsvm_result + kmeans_conf × kmeans_result + 
                 autoenc_conf × autoenc_result) / (qsvm_conf + kmeans_conf + autoenc_conf)
Phase 6: Market Sentiment Integration
Put/Call Ratio Analysis
For each stock:

put_volume = ∑(volume where optionType == 'P')
call_volume = ∑(volume where optionType == 'C')  
pcr = put_volume / max(call_volume, 1)
Sentiment Classification:

pcr < 0.7: Bullish
0.7 ≤ pcr ≤ 1.3: Neutral
pcr > 1.3: Bearish
Real Result: Average PCR = 1.69 → Bearish Market Sentiment

Fear & Greed Index Calculation
Mathematical Components:

IV Component: iv_score = (0.5 - avg_iv) / 0.35 × 50 + 50
PCR Component: pcr_score = (1.5 - avg_pcr) / 1.0 × 50 + 50
Combined Score: fear_greed = (iv_score + pcr_score) / 2
Real Result: Fear & Greed Score = 65.9 (Greed level)

Phase 7: Dynamic Threshold System
Adaptive Threshold Mathematics
Historical Analysis:

Recent_scores = [0.12, 0.15, 0.18, 0.36, 0.09]
μ = moving_average(scores) = 0.18
σ = moving_std(scores) = 0.10
z_score = 1.96 (95% confidence)
Dynamic Threshold:

threshold_t = μₜ + z_α × σₜ = 0.18 + 1.96 × 0.10 = 0.376
Market Regime Adjustment:

High Volatility: threshold × 1.2
Normal Volatility: threshold × 1.0
Low Volatility: threshold × 0.8
Real-World Performance Results
Comprehensive Analysis (June 9, 2025)
Market Conditions Detected:

Market Sentiment: Fearful (elevated put/call ratios)
Volatility Regime: High Volatility Crisis
Put/Call Ratio: 1.69 (bearish institutional positioning)
Market Stress Indicator: High Stress
Sector Analysis Results:

Financial Services: Score = 14.86, Sentiment = Bullish
Technology: Score = 12.36, Sentiment = Neutral
Communication Services: Score = 11.82, Sentiment = Neutral
Risk Assessment:

Overall Risk Score: 43% (Moderate Risk)
Risk Dimensions: [Market: 65, Volatility: 45, Liquidity: 25, Model: 15, Concentration: 55]
Mathematical Pipeline Summary
The complete data transformation:

Raw Options Data (50 stocks × ~190 contracts each)
↓ [Multi-source integration & validation]
Professional Dataset (9,462 clean contracts)  
↓ [12-feature engineering pipeline]
Normalized Feature Matrix (9,462 × 12)
↓ [6-qubit quantum encoding]
Quantum State |ψ⟩ (64-dimensional Hilbert space)
↓ [Variational quantum processing]  
Entangled Quantum Features (54 parameters)
↓ [SWAP test fidelity measurement]
Quantum Anomaly Scores (fidelity-based)
↓ [3-model ensemble voting]
Binary Anomaly Classifications
↓ [Dynamic threshold validation]
Validated Anomaly Predictions
↓ [Professional research generation]
Complete Institutional-Grade Analysis Report
Implementation Realities
Data Quality Challenges
Working with real options data revealed critical implementation requirements:

Quality Score Components:

Source Diversity: len(unique_sources) / 3
Contract Coverage: valid_contracts / total_available
Spread Quality: contracts_with_tight_spreads / total_contracts
Volume Adequacy: contracts_with_volume > min_threshold / total
Time Freshness: (current_time — last_update) < max_staleness
Performance Constraints
R² Values: 0.001–0.01 range (typical for financial prediction) Signal Strength: 20–53 basis points across different assets Market Efficiency Recognition: Consistent alpha generation remains challenging

Technical Achievements
Quantifiable Results:

90.7% anomaly detection accuracy with quantum advantage
Real-time processing of 9,462 options contracts
Professional-grade research generation with actionable insights
Multi-source data validation ensuring institutional quality
Mathematical Innovation:

First implementation of the SWAP test for financial anomaly detection
Successful quantum-classical hybrid architecture
Volatility surface encoding into quantum rotation angles
Dynamic threshold adaptation based on market regimes
Conclusion
QOADRS demonstrates that quantum computing can provide measurable advantages in options market analysis when properly implemented with rigorous mathematical foundations. The system achieved genuine quantum advantage through careful encoding of financial features into quantum states and leveraging quantum interference effects for enhanced pattern detection.

Key Technical Learning: Quantum advantage in finance requires careful implementation of quantum-specific algorithms (like SWAP tests), realistic performance expectations, and rigorous validation against classical baselines. The 90.7% accuracy represents genuine predictive capability on real market data, not academic toy problems.

The complete mathematical pipeline processes each contract through 50+ formulas across quantum computing, financial mathematics, statistical analysis, and machine learning — all integrated into a production-ready quantitative research system that generates institutional-grade analysis reports.

All code and mathematical implementations are available in the GitHub repository for verification and extension by the quantitative research community.

Contact Information: For discussions or suggestions, feel free to contact me, Navnoor Bawa, via LinkedIn. I’m open to feedback! Please send me a direct message on LinkedIn if you’d like to suggest additional features or if you spot any errors that need correction.

Disclaimer: This project is purely educational. The strategies discussed are for demonstration purposes only. Always consult with a financial advisor before making investment decisions.

GitHub Repository: https://github.com/NavnoorBawa/Quantum-Options-Anomaly-Detection-Research-System-QOADRS-/tree/main