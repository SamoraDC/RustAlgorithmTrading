The $400M Gain, $165M Loss: How Two Sigma’s Model Governance Failures Created Asymmetric P&L Impact
Navnoor Bawa
Navnoor Bawa

Following
8 min read
·
Aug 19, 2025
1


1





A forensic analysis of how poor model governance simultaneously generated $400M+ in client gains and $165M in client losses
Press enter or click to view image in full size

In August 2023, Two Sigma discovered that a single employee had been making unauthorized changes to their algorithmic trading models for nearly two years. The result? Some client funds overperformed by more than $400 million while others underperformed by $165 million — all from the same governance failure.

On January 16, 2025, the SEC settlement revealed the shocking details: vulnerabilities identified in March 2019 went unaddressed for over four years, allowing unauthorized parameter modifications across 14 different trading models. The firm paid $90 million in penalties and voluntarily returned $165 million to affected clients.

But here’s the critical question every quantitative researcher should ask: How did identical governance failures produce such asymmetric P&L outcomes?

While the SEC documents don’t specify the exact mechanism, the case reveals fundamental questions about model risk, parameter sensitivity, and algorithmic trading system vulnerabilities. This isn’t just a compliance story — it’s a masterclass in how technical governance failures can create massive client impact.

The Technical Mechanism: Inside the celFS Vulnerability
The Infrastructure Weakness
Two Sigma’s vulnerability centered on their celFS database — a filesystem storing critical model parameters used by their algorithmic trading systems. The SEC found that “Model parameters stored in celFS were accessible by certain modelers and a variety of other Two Sigma personnel, each of whom had unrestricted read and write access to celFS and the parameters stored therein.”

The Critical Flaw:

No access controls: Personnel had “unrestricted read and write access” to live trading parameters
No approval process: Parameter changes bypassed PAM/Mini-PAM procedures required for model changes
No real-time monitoring: Changes went “undetected until August 2023”
No systematic oversight: The SEC found policies “contained no mechanism to check whether all changes to Model parameters stored in celFS that required a PAM or Mini-PAM were in fact made pursuant to a PAM or Mini-PAM”
Background: The Architectural Decision
Originally, Two Sigma stored model code in a secure file called the “Jar” that “only members of an engineering team can update”. However, “beginning with the advent of machine learning-based Models, the parameters necessary to run such Models outgrew the data size constraints of the Jar”. This led modelers to use celFS for storing larger parameters, but without transferring the security controls from the Jar system.

The Parameter Changes: What the SEC Found
The unauthorized changes specifically targeted decorrelation parameters. According to the SEC Order, Modeler A “changed Model decorrelation parameters stored in celFS” and “by adjusting these Model parameters, in many cases to zero (i.e., nullifying the parameter), Modeler A increased these Models’ expected correlation to Two Sigma’s other Models without detection.”

Technical Impact: The SEC found that modelers “used Model parameters stored in celFS to increase or decrease the impact of specific Model code contained in the Jar, including decreasing one Model’s correlation to other existing Models”. The SEC noted this was “important to Two Sigma because it removed redundancy that could result in Two Sigma buying or selling more or less of a specific security than it otherwise desired or intended”.

Note: The SEC documents provide the factual details above but do not elaborate on the specific quantitative mechanics of how decorrelation parameter changes translate to portfolio construction decisions.

The May 2022 Incident: When Everything Went Wrong
The most dramatic failure occurred on May 9, 2022 when “a TSI employee inadvertently overwrote an entire volume in celFS containing several Models’ parameters before certain markets opened for trading that day”. The SEC found that “this change prevented the Models from generating the forecasts that Two Sigma used to make investment decisions on behalf of certain of its client funds and SMAs.”

Crucially, “although Two Sigma was able to reverse these changes before markets opened, this incident reinforced the validity of the concerns expressed by Two Sigma employees about the vulnerabilities to the celFS database beginning in 2019.”

The Delayed Response
Despite identifying these vulnerabilities in March 2019, Two Sigma “made no changes to the controls governing Model parameters stored in celFS in 2019 or 2020”. Even after a senior engineer warned in January 2022 that the practice was “dangerous”, changes weren’t implemented until after the May 2022 incident.

The June 2022 fix was insufficient: Two Sigma implemented a ticket system that “automatically — i.e., without review or analysis by the engineers who received the tickets — implemented the Model parameter changes reflected on a modeler’s ticket”. Real monitoring didn’t begin until August 2023.

The P&L Impact: Asymmetric Outcomes from Identical Failures
The Documented Financial Impact
Verified Facts from SEC Settlement:

Some client funds overperformed by more than $400 million
Other client funds underperformed by approximately $165 million
Changes affected 14 different trading models
Unauthorized modifications occurred from November 2021 to August 2023
The responsible employee received “millions of dollars” in additional compensation
Analyzing the Asymmetric Impact
The central puzzle: How did identical parameter manipulation produce opposite outcomes for different funds?

Potential Explanations (Analytical Framework): The following analysis represents my technical interpretation of how such parameter changes might produce asymmetric outcomes. The SEC documents confirm the $400M/$165M split but do not explain the underlying mechanism.

Several factors could potentially explain the asymmetric impact:

Different Strategy Exposures:

Funds running momentum strategies might benefit from increased correlation
Market-neutral strategies might suffer from reduced diversification
Different factor exposures could respond differently to parameter changes
Timing and Market Regimes:

Parameter changes during trending markets vs. volatile periods
Different funds’ exposure to regime-dependent strategies
Varying rebalancing frequencies and risk management approaches
Model Architecture Differences:

Different funds using different subsets of the 14 affected models
Varying parameter sensitivities across different algorithmic strategies
Different position sizing methodologies responding to correlation changes
Important: These explanations represent analytical interpretations. The SEC settlement documents do not provide specific details about why some funds gained while others lost.

The Compensation Distortion
The SEC documents reveal that the employee responsible (“Modeler A”) received “millions of dollars” in additional compensation based on the manipulated performance metrics. This creates a perverse feedback loop:

Unauthorized changes boost fund performance
Performance bonuses increase based on inflated returns
Incentive to continue manipulation grows
Risk to client capital compounds
This compensation structure violated Two Sigma’s fiduciary duty by rewarding behavior that put client interests at risk.

Timeline of Value Creation and Destruction
March 2019: Vulnerabilities identified, risk warnings issued

Action taken: None
Client impact: Risk building silently
January 2022: Senior engineer warns practice is “dangerous”

Action taken: Ticket system implemented (but automatically approved changes)
Client impact: Risk warnings ignored
May 2022: Critical incident — entire celFS volume overwritten

Action taken: Manual recovery, no structural fixes
Client impact: Immediate trading disruption
November 2021 — August 2023: Period of unauthorized changes

Action taken: None — changes went undetected
Client impact: $400M+ gains for some funds, $165M losses for others
August 2023: Monitoring finally detects unauthorized changes

Action taken: Comprehensive fixes implemented
Client impact: Damage already done
The Risk Management Failure: What Two Sigma Missed
1. Environmental Controls
The Failure: No separation between development and production systems The Fix: Strict environment segregation with approval gates

2. Change Management
The Failure: Direct parameter modifications bypassed all oversight The Fix: Multi-level approval for any production parameter changes

3. Real-Time Monitoring
The Failure: Unauthorized changes went undetected for nearly two years The Fix: Automated alerts for any parameter modifications

4. Audit Trails
The Failure: No systematic tracking of who changed what parameters when The Fix: Complete audit logging with regular reconciliation

Key Lessons for Quantitative Professionals
1. Parameter Sensitivity Analysis Is Critical
The Two Sigma case demonstrates how seemingly minor parameter changes can create massive P&L swings. Every quant should regularly stress-test their models by:

Running sensitivity analysis on all key parameters
Understanding the P&L impact of parameter changes
Identifying which parameters have asymmetric risk profiles
2. Infrastructure Risk Is Model Risk
Two Sigma’s failure wasn’t in their mathematical models — it was in their technology infrastructure. Model risk management must include:

Database access controls
Change management processes
Environmental segregation
Real-time monitoring systems
3. Governance Can’t Be Automated Away
Two Sigma implemented a ticket system in June 2022, but it automatically approved changes without human review. True governance requires:

Human oversight at critical decision points
Multiple approval levels for production changes
Regular governance process audits
Clear escalation procedures
4. Compensation Alignment Matters
The “millions of dollars” in additional compensation paid to Modeler A shows how misaligned incentives can amplify risk. Compensation structures should:

Include long-term risk-adjusted metrics
Penalize risk management violations
Reward sustainable performance over short-term gains
Include clawback provisions for governance failures
Industry Implications: Likely Regulatory Evolution
The following represents analytical extrapolation from the Two Sigma enforcement action and broader SEC trends, rather than explicit regulatory guidance.

The Two Sigma settlement likely establishes new SEC expectations for algorithmic trading oversight:

Mandatory Requirements:

Formal model governance frameworks
Regular vulnerability assessments
Documented change management processes
Real-time monitoring and alerting systems
Enforcement Focus:

Model parameter controls
Employee access management
Whistleblower protection compliance
Fiduciary duty in automated systems
Financial Consequences:

$90M penalty sends clear message about enforcement priorities
$165M client repayment shows SEC focus on investor protection
Industry-wide compliance costs will increase significantly
The Bottom Line
Two Sigma’s governance failure resulted in a $90 million SEC penalty and $165 million in voluntary client repayments — not caused by market moves, model predictions, or trading strategy failures, but by basic infrastructure governance failures that allowed unauthorized parameter changes to persist for years.

The core lesson: In algorithmic trading, infrastructure risk is existential risk. The difference between a $400M client gain and a $165M client loss can be as simple as who has access to change a correlation parameter in your database.

For quantitative professionals, this case provides a crucial reminder: the most sophisticated mathematical models in the world are only as reliable as the governance systems that protect them. In an industry where microseconds matter for execution, Two Sigma took four years to address a known vulnerability.

Key Takeaway: Model governance isn’t a compliance checkbox — it’s a critical risk management function that can impact client performance by hundreds of millions of dollars.

Sources
Primary Sources:

SEC Release No 34–102207 (January 16, 2025)
SEC Press Release 2025–15
Secondary Sources:

Bloomberg, Reuters, Financial Times coverage of settlement
Two Sigma public statements
Industry analysis and commentary