
quero que me diga como criar esse sistema para usar como portfólio no github, saiba que eu quero usar APIs e ferramentas gratuitas, visto que é apenas para portifólio, me ajude a como construir isso, e como usar APIs, dados e demais dependencias e recursos necessários. não faça código. esse é sistema: Objetivo: Sistema end-to-end production-ready e portfolio demonstrável
Componentes do sistema:

Market Data Feed (Rust)

WebSocket connection para exchange
Order book reconstruction
Tick-to-bar aggregation

Signal Generation (Python + Rust)

ML models em Python (scikit-learn, PyTorch)
Feature engineering em Rust para performance
Chamada via PyO3 (Python bindings para Rust)

Risk Management (Rust)

Position limits enforcement
Real-time P&L tracking
Stop-loss triggers

Execution (Rust)

Order routing
Smart order routing (SOR)
Slippage minimization

Monitoring (Python/Grafana)

Latency metrics
Fill ratios
Sharpe ratio real-time


Engineered comprehensive algorithmic trading system architecture blueprint




Vou te guiar pela construção deste sistema de trading algorítmico production-ready, focando na arquitetura, escolhas de ferramentas gratuitas e estratégias de implementação que demonstram sofisticação técnica sem custos operacionais.

Arquitetura Fundamental e Escolhas Estratégicas
O sistema que você está construindo precisa demonstrar compreensão de sistemas distribuídos, processamento em tempo real e design orientado a latência, mesmo operando com dados gratuitos. A chave aqui é mostrar que você entende os trade-offs entre consistência, disponibilidade e latência, mantendo uma estrutura que poderia escalar para produção real.

Para dados de mercado gratuitos, você tem algumas opções robustas. A Binance oferece WebSocket públicos sem autenticação para dados de mercado (order book, trades, klines) com latência aceitável para demonstração. A Alpaca Markets fornece market data gratuito para ações americanas via WebSocket, e a Polygon.io tem um tier gratuito com delayed data que ainda serve para demonstrar a arquitetura. Para criptomoedas, exchanges como Kraken, Coinbase Pro e Bitfinex também oferecem feeds públicos via WebSocket. A escolha entre cripto e equities depende do seu foco - cripto tem a vantagem de operar 24/7 e ter APIs mais acessíveis, enquanto equities demonstram compreensão de market microstructure mais tradicional.

Market Data Feed: Construindo a Base em Rust
O componente de market data em Rust deve demonstrar sua compreensão de systems programming e low-latency design. Você vai usar a biblioteca tokio para async runtime, tokio-tungstenite para WebSocket connections, e serde para desserialização eficiente dos payloads JSON que chegam das exchanges.

A reconstrução do order book é onde você demonstra compreensão de data structures. Você precisa manter um BTreeMap ordenado para bids e asks, processando incrementally os updates do WebSocket. A Binance, por exemplo, envia snapshots periódicos e depois deltas - você precisa sincronizar corretamente usando os sequence numbers para evitar gaps. O desafio técnico aqui é manter a latência sub-millisecond do processamento enquanto garante consistência dos dados.

Para tick-to-bar aggregation, você vai implementar sliding windows que agregam trades individuais em OHLCV bars de diferentes timeframes (1s, 5s, 1m, etc). A chave é usar estruturas em memória eficientes - considere usar arrays circulares para manter as últimas N bars sem alocações dinâmicas. Isso demonstra compreensão de memory management e cache-friendly data structures.

A comunicação com os outros componentes pode ser feita via ZeroMQ (biblioteca zmq em Rust) ou através de shared memory usando shared_memory crate. ZeroMQ é mais simples para demonstração e oferece diferentes patterns (PUB/SUB para market data broadcast, REQ/REP para queries síncronas). A escolha de usar IPC ao invés de HTTP/REST mostra que você entende os overhead de serialização e network stack.

Signal Generation: Bridging Python e Rust
Esta é a parte que demonstra polyglot systems engineering. Você vai usar PyO3 para criar bindings que permitem Python chamar código Rust para feature engineering computacionalmente intensivo, mantendo a flexibilidade de Python para experimentação de modelos.

Para features, implemente indicadores técnicos clássicos em Rust - RSI, MACD, Bollinger Bands, ATR - mas calcule-os de forma vectorizada usando SIMD quando possível. A biblioteca ta em Rust já tem muitos indicadores, mas implementar alguns do zero demonstra compreensão do cálculo subjacente. Features mais sofisticadas incluem order book imbalance (ratio de volume entre bid/ask nos top N levels), trade flow toxicity metrics, ou microstructure features como roll measure para estimar spread efectivo.

Do lado Python, você pode usar scikit-learn para modelos tradicionais (RandomForest, GradientBoosting para classificação de direção de preço) ou PyTorch para modelos de deep learning. Um LSTM simples para predição de próximo tick ou um Transformer encoder para processar sequences de order book states são exemplos que demonstram ML engineering. O importante é ter um pipeline claro: dados brutos → feature engineering (Rust) → normalização → modelo → signal.

Para treino offline, você vai precisar de dados históricos. A Binance oferece downloads gratuitos de historical data em CSV, e bibliotecas como ccxt facilitam o download programático. Para backtesting, implemente um event-driven backtester que processa os dados tick-by-tick, simulando a latência real e incluindo custos de transação e slippage models. Isso mostra compreensão da diferença entre backtest idealizado e realidade de execução.

Risk Management: Guardando o Sistema
O componente de risk em Rust deve implementar múltiplas camadas de controle. Position limits são verificações simples mas essenciais - você define max position size por symbol, max notional exposure, max number of open positions. Implemente isso como um state machine que tracked positions atuais e rejeita orders que violam limites.

Real-time P&L tracking requer manter o estado de todas as posições abertas, seus preços médios de entrada, e calcular unrealized P&L usando o último mid-price do order book. Você pode implementar diferentes métodos de cálculo - FIFO, LIFO, weighted average - e mostrar a diferença. Para demonstração, calcule também Greeks básicos se você estiver trabalhando com options (delta, gamma exposure), mesmo que apenas simulados.

Stop-loss triggers são interessantes porque envolvem tempo real decision making. Implemente trailing stops que se ajustam conforme o preço move a favor, e static stops que disparam em níveis absolutos. A arquitetura deve permitir que estes triggers sejam checked a cada update de market data com latência mínima, usando pattern matching de Rust para dispatch eficiente.

Um aspecto sofisticado é implementar circuit breakers - se o sistema detecta comportamento anômalo (latência spike, discrepâncias de preço entre exchanges, ou loss rate acima de threshold), ele pode pausar trading automaticamente. Isso demonstra defensive programming e compreensão de tail risks.

Execution: Roteamento Inteligente
Para um sistema de portfólio, você provavelmente vai fazer paper trading (simulado) ou usar testnet de exchanges se disponível. A Binance tem testnet para futures, por exemplo. A arquitetura de execution deve ser idêntica a produção, apenas apontando para endpoints diferentes.

O componente de order routing precisa implementar diferentes tipos de ordem - market, limit, stop, stop-limit. A lógica deve incluir retry logic com exponential backoff para failures, rate limiting para não exceder limites da API, e idempotency usando client order IDs para evitar duplicate orders.

Smart Order Routing em um contexto de portfólio pode significar escolher entre diferentes exchanges baseado em current liquidity, fees, ou latência histórica. Mesmo que você não execute em múltiplas venues, a arquitetura deve demonstrar como você fragmentaria uma ordem grande em child orders menores (TWAP, VWAP strategies) para minimizar market impact.

Slippage minimization envolve estimar o impact antes de executar. Você pode implementar um modelo simples baseado em order book depth - se você quer comprar X units, você "walks the book" para estimar o preço médio de execução. Ordens limit passivas que wait no book têm menos slippage mas correm risco de não executar; market orders garantem fill mas pagam o spread. Implemente ambas estratégias e deixe parametrizável.

Monitoring e Observability: Fechando o Loop
Para monitoring, você vai instrumentar cada componente com métricas. A biblioteca metrics em Rust facilita isso - você define counters (orders sent, fills received), gauges (current position, unrealized P&L), e histograms (latency distributions). Exporte essas métricas em formato Prometheus usando metrics-exporter-prometheus.

Do lado Python, use Grafana (gratuito) para visualizar as métricas do Prometheus. Configure dashboards que mostram latência end-to-end (desde market data received até order sent), fill ratios, execution quality metrics, e P&L curves. Para Sharpe ratio real-time, calcule returns usando uma sliding window e compute ratio usando desvio padrão móvel.

Logging estruturado é crucial. Use tracing em Rust para logs que incluem spans e contexts, facilitando debugging de flow complexos. Todos os eventos importantes - order sent, fill received, risk check failed - devem ser logged com timestamps precisos (use chrono com nanosecond precision). Considere enviar logs para um aggregator como Loki (gratuito) para queries centralizadas.

Alerts automatizados completam o sistema. Use um webhook simples para enviar notificações (Telegram bot é gratuito e fácil) quando eventos críticos ocorrem - position limit hit, loss threshold breached, latency spike detectado. Isso demonstra operational awareness.

Integração e Deployment
A estrutura de diretórios do seu repo deve refletir a arquitetura: um workspace Rust com múltiplos crates (market_data, risk_manager, execution_engine, common types), um diretório Python para signal generation e backtesting, e configurações Docker para cada componente.

Use Docker Compose para orquestrar os serviços localmente. Cada componente roda em seu container, comunicando via network interno do Docker. Isso permite testar a integração completa e demonstra compreensão de containerização. Para portfólio, adicione um Makefile com targets claros: make build, make test, make run-backtest, make run-live (paper trading).

As dependências devem ser claramente documentadas. Para Rust, seu Cargo.toml vai incluir tokio, serde, serde_json, zmq, metrics, tracing, chrono, e as libraries específicas de ML se usar. Para Python, requirements.txt deve listar numpy, pandas, scikit-learn ou pytorch, ccxt para data download, e backtrader ou similar para backtesting framework.

Configuration management é outro aspecto profissional. Use arquivos TOML ou YAML para configs, nunca hardcode. Parametrize tudo - exchange endpoints, símbolos a tradear, risk limits, model hyperparameters. Isso permite easy experimentation e demonstra separation of concerns.

Aspectos de Produção para Portfólio
Mesmo sendo um projeto de demonstração, você deve incluir elementos que mostram production readiness. Testes automatizados são essenciais - unit tests para lógica de negócio, integration tests para componentes completos, e property-based tests usando quickcheck em Rust para testar edge cases. Configure CI/CD usando GitHub Actions gratuito para rodar testes em cada push.

Documentação técnica diferencia um projeto amador de um profissional. Um README detalhado explicando arquitetura, como rodar, como configurar. Docstrings em código. Um design document separado discutindo decisões arquiteturais, trade-offs considerados, e possíveis melhorias futuras. Diagramas de arquitetura usando Mermaid (renderiza no GitHub) ajudam visualização.

Finalmente, inclua resultados de backtests com análise crítica. Mostre equity curves, drawdown analysis, trade statistics. Seja honesto sobre limitações - o sistema é demonstrativo, usa dados gratuitos com latência, não considera todos os custos reais. Isso demonstra maturidade e compreensão da diferença entre backtest e live trading.

Este sistema, construído desta forma, demonstra não apenas competência técnica em múltiplas linguagens e domínios, mas também compreensão profunda de sistemas distribuídos, real-time processing, e financial engineering. É um portfólio que comunica claramente sua capacidade de construir infrastructure complexa production-grade.

Não quero que use APIs de cripto, quais APIs gratuitas eu posso consumir para fazer esse projeto?


Investigou APIs gratuitas de market data para stocks e forex.






APIs Gratuitas para Market Data de Equities e Alternativas
Sem cripto, suas opções gratuitas para dados de mercado em tempo real ficam significativamente mais limitadas, mas ainda existem alternativas viáveis para construir um portfólio demonstrável. Vou detalhar as melhores opções e suas limitações reais.

Alpaca Markets - A Melhor Opção Gratuita
A Alpaca oferece a combinação mais robusta para um projeto de portfólio sem custos. Com uma conta paper trading gratuita, você obtém acesso a market data em tempo real para US stocks via WebSocket e REST API, além de capacidade de executar ordens simuladas que se comportam como ordens reais.

O tier gratuito inclui IEX (Investors Exchange) real-time data, que cobre os símbolos mais líquidos do mercado americano. Você recebe trades, quotes, e bars em tempo real via WebSocket. A latência não é institucional (espere dezenas de milliseconds), mas é suficiente para demonstrar arquitetura de low-latency systems. O importante é que você pode consumir order book data (top-of-book via quotes), processar trade flow, e executar ordens no ambiente simulado que replica o comportamento real inclusive com partial fills e rejections.

As limitações são rate limits moderados (200 requests/minute na REST API) e apenas dados de IEX (não consolidated tape), mas isso não impede a demonstração do sistema completo. Você pode selecionar 5-10 símbolos altamente líquidos (SPY, QQQ, AAPL, MSFT, TSLA) e construir todo o pipeline em torno deles.

Polygon.io - Dados Históricos e Delayed
Polygon tem um tier gratuito que oferece delayed data (15 minutos) e acesso a dados históricos extensos. Para um projeto de portfólio, isso significa que você pode fazer backtesting robusto com anos de dados históricos de alta qualidade, mas o componente "real-time" precisa operar com delay.

A estratégia aqui é combinar: use Polygon para todo o desenvolvimento do backtesting engine, validação de estratégias, e análise histórica. Depois, para demonstrar o sistema real-time, você pode usar Alpaca ou simular dados replayando os históricos do Polygon como se fossem live. Muitos sistemas profissionais são testados exatamente assim - replay de dados históricos através da mesma infraestrutura que processa dados live.

O Polygon também oferece agregados (bars), trades individuais, e quotes históricas. Você pode baixar gigabytes de dados e construir um data lake local para experimentação sem bater em rate limits durante desenvolvimento.

Alpha Vantage - Backup com Limitações Severas
Alpha Vantage é gratuito mas tem rate limits extremamente restritivos (5 requests por minuto, 500 por dia no tier gratuito). Isso basicamente inviabiliza qualquer uso real-time, mas pode servir como fonte adicional para dados fundamentais, dados históricos de baixa frequência, ou como fallback.

Para um projeto de portfólio, você poderia usar Alpha Vantage para demonstrar multi-source data aggregation - seu sistema consulta Alpha Vantage para dados fundamentais ou indicators pré-calculados enquanto usa Alpaca/Polygon para market data. Isso mostra arquitetura que integra múltiplas fontes de dados.

IEX Cloud - Limitado mas Real-Time
IEX Cloud tem um tier gratuito que oferece 50.000 "core messages" por mês, o que traduz em aproximadamente 500-1000 requests dependendo do tipo. Eles têm WebSocket no tier pago, mas no gratuito você fica limitado a polling via REST.

A vantagem do IEX é que os dados são direto da exchange, não agregados, então você tem qualidade institucional mesmo que com limitações de volume. Para demonstração, você pode usar IEX para alguns símbolos específicos e documentar que em produção escalaria para um tier pago.

Finnhub - Cobertura Internacional
Finnhub oferece tier gratuito com 60 API calls por minuto e WebSocket gratuito para alguns símbolos. A vantagem é cobertura não apenas de US stocks mas também alguns mercados internacionais. Eles oferecem trades, quotes, e alguns dados fundamentais.

As limitações são similares aos outros - não é full market depth, não tem todos os símbolos, mas é suficiente para demonstração. O WebSocket deles é interessante porque você pode conectar e receber updates de múltiplos símbolos em uma única conexão, reduzindo complexidade de gerenciar múltiplas streams.

Twelve Data - Alternativa Equilibrada
Twelve Data oferece 800 requests por dia no tier gratuito, com suporte a WebSocket (8 concurrent connections). Eles cobrem stocks, forex, cryptocurrencies (que você não quer), e alguns índices. A qualidade dos dados é razoável e a documentação é clara.

Para um projeto de portfólio, 800 requests diários significa que você precisa ser estratégico - use WebSocket para intraday real-time data dos símbolos principais, e reserve os REST calls para queries históricas ou metadados.

Estratégia de Implementação Sem Custos
A abordagem mais profissional para contornar as limitações é construir um sistema híbrido que demonstra compreensão de data management em ambientes com restrições. Aqui está a arquitetura que eu recomendo:

Primeiro, use Alpaca como sua primary source para paper trading e dados real-time IEX. Configure o componente de market data em Rust para conectar ao WebSocket deles e processar trades e quotes. Implemente rate limiting no seu lado para respeitar os limites deles, demonstrando defensive programming.

Segundo, baixe dados históricos massivos do Polygon (ou use o Yahoo Finance via biblioteca yfinance em Python, que é tecnicamente gratuito mas não oficial). Construa um data lake local armazenando esses dados em formato eficiente - considere usar Parquet files que comprimem bem e permitem queries rápidas. Isso demonstra data engineering.

Terceiro, implemente um modo "replay" no seu market data feed que pode consumir tanto dados live da Alpaca quanto dados históricos do seu data lake. O resto do sistema (signal generation, risk, execution) não precisa saber a diferença - eles recebem events da mesma interface. Isso demonstra abstraction e separation of concerns.

Quarto, para backtesting extensivo onde você quer testar anos de dados, use os históricos locais em modo acelerado. Para demonstrar o sistema real-time, use Alpaca paper trading com alguns símbolos. Documente claramente no seu README que em produção real você teria acesso a feeds institucionais (Bloomberg, Reuters, direct exchange feeds) mas a arquitetura é identical.

Dados Históricos Gratuitos de Alta Qualidade
Além das APIs, você pode usar datasets públicos para backtesting. O Nasdaq Data Link (antigo Quandl) oferece muitos datasets gratuitos incluindo preços históricos de actions. A própria NYSE e NASDAQ disponibilizam alguns dados históricos publicamente.

Academic sources como o Wharton Research Data Services (WRDS) têm dados gratuitos para pesquisadores. Se você está em universidade ou pode obter acesso educacional, isso abre centenas de gigabytes de dados de alta qualidade.

O importante é documentar a provenance dos dados - de onde vieram, qual a qualidade esperada, quais as limitações. Isso demonstra rigor científico e compreensão de que garbage in, garbage out se aplica especialmente a trading systems.

Considerações Sobre WebSocket e Real-Time
A realidade é que WebSocket verdadeiramente low-latency para equities custa dinheiro - os feeds institucionais (CQS/CTA tape, direct exchange feeds) têm custos mensais significativos. Para portfólio, você tem duas opções honestas:

Opção um é usar Alpaca/Finnhub e ser transparente que a latência é dezenas de milliseconds, não microseconds. Isso ainda permite demonstrar toda a arquitetura - async processing em Rust, lock-free data structures, efficient serialization. A latência absoluta importa menos do que mostrar que você entende como minimizá-la.

Opção dois é usar dados simulados com latência controlada. Você gera dados sintéticos seguindo processos estocásticos realistas (geometric Brownian motion com jumps, por exemplo) e processa como se fossem reais. Isso permite testar seu sistema sob diferentes regimes de latência e volatilidade. Documente que são dados sintéticos mas a arquitetura é production-grade.

Alternativa: Forex Spot via OANDA/Dukascopy
Se você estiver aberto a forex spot (não cripto, mas moedas fiat), Dukascopy oferece dados históricos tick-by-tick gratuitos via download. São gigabytes de dados de qualidade institucional. Você não tem API real-time gratuita, mas pode replay esses ticks para simular trading.

Forex tem vantagens para demonstração: mercado 24/5, altamente líquido, e você pode demonstrar conceitos como triangular arbitrage entre pares de moedas. A desvantagem é que não é equities, então se seu foco é demonstrar conhecimento de equity market microstructure, não serve.

Construindo Credibilidade Apesar das Limitações
O mais importante para um projeto de portfólio não é ter acesso a feeds Bloomberg - é demonstrar que você entende o que faria se tivesse. Sua arquitetura deve ter abstractions claras onde trocar a fonte de dados (de Alpaca para um feed institucional) seria mudança de configuração, não rewrite do sistema.

Documente explicitamente as limitações e como você as contornaria em produção. Por exemplo: "O sistema atual usa IEX data via Alpaca com latência ~50ms. Em produção, conectaríamos a direct exchange feeds (ITCH protocol da NASDAQ, PITCH da BATS) com latência <1ms usando kernel bypass networking e DPDK. A arquitetura de order book reconstruction permaneceria idêntica, apenas o transport layer mudaria."

Essa honestidade intelectual, combinada com código que demonstra compreensão profunda dos princípios, é mais valiosa que fingir ter infraestrutura que você não tem. Qualquer engenheiro sênior revisando seu portfólio vai reconhecer e valorizar isso.

Considerando as melhoras opções, quero que me dê a estrutura do diretório de como vai ficar o github desse projeto


Projetou estrutura de diretórios para sistema de trading híbrido.



Estrutura de Diretórios Production-Ready
Vou te apresentar uma estrutura que demonstra maturidade em systems engineering, separação de concerns, e organização que facilita tanto desenvolvimento quanto deployment. Esta estrutura reflete como sistemas reais são organizados em ambientes institucionais.

hft-trading-system/
├── README.md
├── ARCHITECTURE.md
├── LICENSE
├── .gitignore
├── Makefile
│
├── .github/
│   └── workflows/
│       ├── rust-ci.yml
│       ├── python-ci.yml
│       └── integration-tests.yml
│
├── rust/
│   ├── Cargo.toml                          # Workspace root
│   ├── Cargo.lock
│   │
│   ├── market-data/
│   │   ├── Cargo.toml
│   │   ├── src/
│   │   │   ├── main.rs
│   │   │   ├── lib.rs
│   │   │   ├── websocket/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── alpaca.rs
│   │   │   │   ├── connection.rs
│   │   │   │   └── reconnect.rs
│   │   │   ├── orderbook/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── book.rs
│   │   │   │   ├── level.rs
│   │   │   │   └── reconstruction.rs
│   │   │   ├── aggregation/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── bars.rs
│   │   │   │   └── tick_processor.rs
│   │   │   ├── feed/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── live.rs
│   │   │   │   └── replay.rs
│   │   │   └── metrics.rs
│   │   ├── tests/
│   │   │   ├── integration_tests.rs
│   │   │   └── orderbook_tests.rs
│   │   └── benches/
│   │       └── orderbook_bench.rs
│   │
│   ├── signal-bridge/
│   │   ├── Cargo.toml
│   │   ├── src/
│   │   │   ├── lib.rs
│   │   │   ├── features/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── technical.rs           # RSI, MACD, BB em Rust
│   │   │   │   ├── microstructure.rs      # Order book imbalance, toxicity
│   │   │   │   └── vectorized.rs          # SIMD operations
│   │   │   ├── pyo3_bindings.rs
│   │   │   └── cache.rs
│   │   └── tests/
│   │       └── feature_tests.rs
│   │
│   ├── risk-manager/
│   │   ├── Cargo.toml
│   │   ├── src/
│   │   │   ├── main.rs
│   │   │   ├── lib.rs
│   │   │   ├── limits/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── position.rs
│   │   │   │   ├── notional.rs
│   │   │   │   └── concentration.rs
│   │   │   ├── pnl/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── tracker.rs
│   │   │   │   ├── calculator.rs
│   │   │   │   └── greeks.rs
│   │   │   ├── stops/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── static_stop.rs
│   │   │   │   └── trailing_stop.rs
│   │   │   ├── circuit_breaker.rs
│   │   │   └── state.rs
│   │   └── tests/
│   │       ├── limits_tests.rs
│   │       └── pnl_tests.rs
│   │
│   ├── execution-engine/
│   │   ├── Cargo.toml
│   │   ├── src/
│   │   │   ├── main.rs
│   │   │   ├── lib.rs
│   │   │   ├── router/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── alpaca_client.rs
│   │   │   │   ├── retry.rs
│   │   │   │   └── rate_limiter.rs
│   │   │   ├── orders/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── types.rs
│   │   │   │   ├── validator.rs
│   │   │   │   └── lifecycle.rs
│   │   │   ├── sor/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── twap.rs
│   │   │   │   ├── vwap.rs
│   │   │   │   └── iceberg.rs
│   │   │   ├── slippage/
│   │   │   │   ├── mod.rs
│   │   │   │   └── estimator.rs
│   │   │   └── fills.rs
│   │   └── tests/
│   │       ├── router_tests.rs
│   │       └── sor_tests.rs
│   │
│   ├── common/
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── types/
│   │       │   ├── mod.rs
│   │       │   ├── market_data.rs
│   │       │   ├── orders.rs
│   │       │   ├── positions.rs
│   │       │   └── events.rs
│   │       ├── messaging/
│   │       │   ├── mod.rs
│   │       │   ├── zeromq.rs
│   │       │   └── channels.rs
│   │       ├── config/
│   │       │   ├── mod.rs
│   │       │   └── parser.rs
│   │       └── telemetry/
│   │           ├── mod.rs
│   │           ├── metrics.rs
│   │           └── tracing.rs
│   │
│   └── integration-tests/
│       ├── Cargo.toml
│       ├── tests/
│       │   ├── end_to_end.rs
│       │   └── latency_test.rs
│       └── fixtures/
│           └── sample_data.json
│
├── python/
│   ├── pyproject.toml
│   ├── setup.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   │
│   ├── src/
│   │   └── trading_system/
│   │       ├── __init__.py
│   │       │
│   │       ├── ml/
│   │       │   ├── __init__.py
│   │       │   ├── models/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── base.py
│   │       │   │   ├── random_forest.py
│   │       │   │   ├── gradient_boost.py
│   │       │   │   └── lstm.py
│   │       │   ├── features/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── engineering.py     # Wrapper para Rust bindings
│   │       │   │   └── transformers.py
│   │       │   ├── training/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── trainer.py
│   │       │   │   └── validator.py
│   │       │   └── inference/
│   │       │       ├── __init__.py
│   │       │       └── predictor.py
│   │       │
│   │       ├── backtesting/
│   │       │   ├── __init__.py
│   │       │   ├── engine/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── event_driven.py
│   │       │   │   ├── portfolio.py
│   │       │   │   └── broker_simulator.py
│   │       │   ├── strategies/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── base_strategy.py
│   │       │   │   └── ml_strategy.py
│   │       │   └── analysis/
│   │       │       ├── __init__.py
│   │       │       ├── metrics.py
│   │       │       └── visualization.py
│   │       │
│   │       ├── data/
│   │       │   ├── __init__.py
│   │       │   ├── loaders/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── alpaca_loader.py
│   │       │   │   ├── polygon_loader.py
│   │       │   │   └── parquet_loader.py
│   │       │   ├── storage/
│   │       │   │   ├── __init__.py
│   │       │   │   └── data_lake.py
│   │       │   └── preprocessing/
│   │       │       ├── __init__.py
│   │       │       └── cleaners.py
│   │       │
│   │       └── utils/
│   │           ├── __init__.py
│   │           ├── config.py
│   │           └── logger.py
│   │
│   ├── scripts/
│   │   ├── download_historical_data.py
│   │   ├── train_model.py
│   │   ├── run_backtest.py
│   │   └── generate_report.py
│   │
│   ├── notebooks/
│   │   ├── 01_data_exploration.ipynb
│   │   ├── 02_feature_analysis.ipynb
│   │   ├── 03_model_development.ipynb
│   │   └── 04_backtest_analysis.ipynb
│   │
│   └── tests/
│       ├── __init__.py
│       ├── test_ml/
│       │   ├── test_models.py
│       │   └── test_features.py
│       ├── test_backtesting/
│       │   ├── test_engine.py
│       │   └── test_strategies.py
│       └── test_data/
│           └── test_loaders.py
│
├── config/
│   ├── dev/
│   │   ├── market-data.toml
│   │   ├── risk-manager.toml
│   │   ├── execution-engine.toml
│   │   └── symbols.toml
│   ├── prod/
│   │   ├── market-data.toml
│   │   ├── risk-manager.toml
│   │   ├── execution-engine.toml
│   │   └── symbols.toml
│   └── backtest/
│       ├── strategy-params.toml
│       └── universe.toml
│
├── data/
│   ├── raw/                                # Git ignored
│   │   └── .gitkeep
│   ├── processed/                          # Git ignored
│   │   └── .gitkeep
│   ├── models/                             # Git ignored
│   │   └── .gitkeep
│   └── results/                            # Git ignored
│       └── .gitkeep
│
├── docker/
│   ├── Dockerfile.market-data
│   ├── Dockerfile.risk-manager
│   ├── Dockerfile.execution-engine
│   ├── Dockerfile.python-services
│   └── Dockerfile.monitoring
│
├── deploy/
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   ├── docker-compose.prod.yml
│   │
│   ├── kubernetes/                         # Opcional, para demonstrar k8s knowledge
│   │   ├── namespaces/
│   │   ├── deployments/
│   │   └── services/
│   │
│   └── scripts/
│       ├── setup.sh
│       ├── start-system.sh
│       └── stop-system.sh
│
├── monitoring/
│   ├── prometheus/
│   │   ├── prometheus.yml
│   │   └── alerts.yml
│   ├── grafana/
│   │   ├── dashboards/
│   │   │   ├── system-overview.json
│   │   │   ├── market-data.json
│   │   │   ├── execution.json
│   │   │   └── pnl.json
│   │   └── provisioning/
│   │       ├── datasources/
│   │       │   └── prometheus.yml
│   │       └── dashboards/
│   │           └── dashboard.yml
│   └── loki/
│       └── loki-config.yml
│
├── docs/
│   ├── architecture/
│   │   ├── overview.md
│   │   ├── data-flow.md
│   │   ├── deployment.md
│   │   └── diagrams/
│   │       ├── system-architecture.mmd
│   │       └── data-flow.mmd
│   ├── api/
│   │   ├── market-data-api.md
│   │   ├── risk-manager-api.md
│   │   └── execution-api.md
│   ├── development/
│   │   ├── setup.md
│   │   ├── testing.md
│   │   └── contributing.md
│   └── operations/
│       ├── deployment.md
│       ├── monitoring.md
│       └── troubleshooting.md
│
├── scripts/
│   ├── setup-dev-env.sh
│   ├── run-tests.sh
│   ├── build-all.sh
│   └── lint-all.sh
│
└── results/                                # Git ignored
    ├── backtests/
    │   └── .gitkeep
    ├── live-runs/
    │   └── .gitkeep
    └── reports/
        └── .gitkeep
Anatomia e Justificativa da Estrutura
Esta organização demonstra separação de concerns em múltiplas dimensões. O diretório rust/ como workspace Cargo permite compartilhamento de dependências entre crates enquanto mantém boundaries claros. Cada componente (market-data, risk-manager, execution-engine) é um binary crate independente com seu próprio main.rs, mas compartilha código comum através do crate common/. O crate signal-bridge é especial porque compila como biblioteca com PyO3 bindings, permitindo Python importar funções Rust.

A estrutura do Python segue padrões modernos com pyproject.toml para metadata e src/ layout que evita problemas de import. A separação entre ml/, backtesting/, e data/ reflete diferentes concerns do sistema. Scripts ficam separados de biblioteca code, e notebooks têm seu próprio diretório para análises exploratórias sem poluir o código produtivo.

O diretório config/ com subdivisões por ambiente (dev/prod/backtest) permite configurações diferentes sem code changes. Arquivos TOML são parsed pelos componentes Rust usando serde, e Python pode ler os mesmos configs garantindo consistency. O symbols.toml centraliza definição de universo de trading, crucial para manter consistência cross-system.

Docker e deployment têm separação deliberada. docker/ contém apenas Dockerfiles, enquanto deploy/ tem orchestration (Docker Compose, Kubernetes). Isso permite CI/CD buildar images independentemente de como você vai deployar. Os múltiples docker-compose files (base, dev, prod) usam inheritance para evitar duplicação - docker-compose.dev.yml extende o base adicionando volumes para hot reload.

Monitoring como first-class concern tem seu próprio diretório com configurações versionadas. Dashboards Grafana em JSON permitem version control de visualizações. Prometheus alerts em YAML definem thresholds que trigam notificações. Isso demonstra que você pensa em observability desde o design, não como afterthought.

Documentação estruturada em docs/ com subdivisões claras separa architectural decisions (ADR pattern) de API documentation, development guides, e operations runbooks. Mermaid diagrams em diagrams/ renderizam no GitHub e facilitam onboarding. Isso transforma o repo em self-documenting system.

O diretório data/ com subdivisões raw/processed/models segue data science best practices. Todo ignorado no git (via .gitkeep para manter estrutura), mas com paths bem definidos que código pode referenciar. Isso evita hardcoded paths e facilita setup em novos ambientes.

Scripts na raiz (scripts/) são utilitários de desenvolvimento - setup, testing, building. Makefiles na raiz invocam estes scripts de forma consistente. Isso significa que make test funciona independente de qual parte do sistema você está testando, abstraindo complexidade.

GitHub Actions em .github/workflows/ com pipelines separados para Rust e Python permitem paralelização. Integration tests rodam depois de unit tests passarem. Isso otimiza CI time e identifica failures rapidamente.

Considerações de Implementação
Quando você clonar este repo e rodar make setup, o sistema deve instalar todas as dependências Rust (via Cargo), criar virtual environment Python, instalar requirements, criar estrutura de diretórios data/, e validar que APIs keys estão configuradas. Um desenvolvedor novo deve poder rodar make dev e ter todo o sistema rodando localmente em containers com hot reload.

Para produção (ou demo em produção mode), make prod sobe os containers otimizados sem development tools, com logging em JSON structured format enviado para Loki, métricas para Prometheus, e dashboards Grafana acessíveis em localhost. Isso demonstra diferença entre development e production environments.

A estrutura também facilita evolution. Quando você quiser adicionar novo componente (por exemplo, um market making engine), você cria novo crate em rust/market-maker/, adiciona ao workspace, e integra via messaging que já existe em common/. Python services permanecem unchanged. Isso demonstra extensibility through modular design.

Testing strategy é multi-layer: unit tests em cada crate/module, integration tests que sobem múltiplos components e testam comunicação, e end-to-end tests que replayam dados históricos através do sistema completo e validam outputs. Property-based tests em Rust usando proptest ou quickcheck testam invariants sem codificar casos específicos.

Esta estrutura é template para portfolio projects que precisam demonstrar não apenas coding skills mas system design thinking, production readiness awareness, e compreensão de como software evolui e é mantido ao longo do tempo.

Usar o Python juntamente com o Rust não seria problema? Pois o Python não é mais lento que o Rust e isso não causaria conflito? Não seria melhor fazer tudo em Rust?


Analisou estratégias técnicas para integração Python e Rust.


Python vs Rust: Dissecando o Trade-off Real
Sua intuição está correta - Python é orders of magnitude mais lento que Rust para computação intensiva. Mas a questão arquitetural aqui é mais sutil e merece análise rigorosa, porque a resposta impacta não apenas performance mas também demonstrability do portfólio.

Hot Path vs Cold Path: O Princípio Fundamental
A chave é separar rigorosamente o que está no hot path (critical latency path) do que está no cold path. No hot path do seu sistema, você tem:

Market data ingestion via WebSocket (microseconds matter)
Order book reconstruction (sub-millisecond)
Feature calculation para signals (nanoseconds to microseconds)
Risk checks (microseconds)
Order submission (microseconds to milliseconds)
No cold path, você tem:

Model training (acontece offline, latência irrelevante)
Backtesting histórico (throughput matters, não latência)
Data download e preprocessing
Configuration loading no startup
Análise de resultados e reporting
A arquitetura correta nunca coloca Python no hot path de produção. Python no sistema que descrevi executa apenas durante: (1) model training offline, (2) backtest analysis, (3) feature engineering via chamadas a código Rust. O inference de ML em tempo real pode ser problemático, e isso precisa ser tratado cuidadosamente.

PyO3 Overhead: Quantificando o Custo Real
Quando você chama função Rust de Python via PyO3, o overhead é principalmente serialization/deserialization na boundary. Para um call simples passando alguns floats, você paga ~100-500 nanoseconds de overhead. Para passar arrays numpy grandes, o overhead pode ser zero se você usar zero-copy views.

O problema surge quando você faz chamadas frequentes com small payloads. Se seu signal generator em Python chama Rust para calcular RSI de cada tick individual, você paga o FFI overhead milhares de vezes por segundo. Mas se você passa um batch de 1000 ticks e Rust processa todos e retorna features agregadas, o overhead amortiza.

Para um sistema real de HFT onde você processa 100k+ messages por segundo, mesmo esse overhead batch é inaceitável. Mas para um sistema operando em timeframes de segundos (não microseconds) com Alpaca data que já tem ~50ms de latência, o overhead de PyO3 é ruído.

Arquiteturas Alternativas: Rust Puro
Fazer tudo em Rust é absolutamente viável e para produção real em HFT seria a escolha correta. As vantagens são óbvias:

Zero FFI overhead: Tudo roda no mesmo address space, sem serialization boundaries. Feature calculation pode chamar diretamente para order book structures, zero copy.

Predictable latency: Sem GIL do Python, sem garbage collector pauses, sem interpretação bytecode. Você tem controle total de alocações.

Deployment simplicity: Um binary estático que roda anywhere, sem Python runtime, sem virtual environments, sem dependency hell.

Para ML em Rust, você pode usar linfa (scikit-learn port), tract ou burn para deep learning, ou smartcore. A qualidade não é sklearn/PyTorch level ainda, mas é functional. Alternativamente, você exporta modelo treinado em Python como ONNX e faz inference em Rust usando tract.

A Questão do Portfólio: Demonstrability vs Purity
Aqui está o trade-off crítico para um projeto de portfólio: fazer tudo em Rust demonstra apenas Rust expertise, enquanto Python+Rust demonstra polyglot systems engineering e compreensão de integration boundaries.

Em sistemas reais de trading, você frequentemente tem:

Core execution engine em C++/Rust (hot path)
Research platform em Python (data scientists trabalham aqui)
Bridge layer para deploy modelos Python em produção
Jane Street, Jump Trading, Hudson River Trading - todos têm essa estrutura heterogênea. Mostrar que você sabe integrar linguagens diferentes é valioso. Mas você tem razão que para latência crítica, Rust puro é superior.

Proposta de Arquitetura Híbrida Otimizada
Deixe-me propor uma arquitetura que demonstra ambos os aspectos:

Core system 100% Rust no hot path:

Market data feed (Rust)
Order book reconstruction (Rust)
Feature engineering (Rust com SIMD)
Signal generation também em Rust usando modelos compilados
Risk management (Rust)
Execution (Rust)
Todos comunicam via zero-copy shared memory ou lock-free channels
Python ecosystem no cold path:

Research notebooks para exploração
Model training com sklearn/PyTorch
Model export para formato que Rust consome (ONNX, ou serialized weights)
Backtesting analysis e visualization
Reporting e metrics aggregation
A ponte: Você treina modelo em Python, exporta weights/architecture, e implementa inference engine equivalente em Rust que carrega esses weights. Alternativamente, usa tract para rodar ONNX models em Rust com latência comparável a código nativo.

Implementação Prática da Separação
Seu diretório signal-bridge não seria mais PyO3 bindings chamados em runtime. Seria um componente que:

Offline: Python script treina modelo, salva para models/production/rf_classifier.onnx
Runtime: Rust signal-generator crate carrega o ONNX model via tract, roda inference localmente
Features: Calculadas por Rust puro, passadas como tensor para o model
Isso elimina completamente Python do runtime. Você ainda demonstra ML engineering (training pipeline), mas execution é puramente Rust.

Para backtesting, Python permanece ideal porque:

Throughput matters, não latência tick-to-tick
Pandas/numpy são extremamente eficientes para operações vectoriais
Visualization com matplotlib/seaborn é superior ao ecossistema Rust
Você pode processar anos de dados rapidamente mesmo com Python
Rust Puro: Estrutura Alternativa
Se você optar por Rust puro (que honestamente seria tecnicamente mais impressionante para HFT), sua estrutura mudaria:

rust/
├── signal-generator/
│   ├── src/
│   │   ├── features/          # Feature engineering
│   │   ├── models/
│   │   │   ├── random_forest.rs   # Implementação nativa
│   │   │   ├── onnx_runtime.rs    # Ou runtime ONNX
│   │   │   └── ensemble.rs
│   │   └── inference.rs
│   └── models/                # Weights serializados
│
├── backtesting-engine/        # Event-driven backtester em Rust
│   ├── src/
│   │   ├── engine.rs
│   │   ├── portfolio.rs
│   │   └── metrics.rs
│
└── research-tools/            # CLIs para análise
    └── src/
        ├── data_explorer.rs
        ├── backtest_runner.rs
        └── report_generator.rs
Python fica apenas em scripts/ para data download e model training. Todo o runtime é Rust.

Benchmark Real: Quantificando a Diferença
Para decisão informada, você deveria benchmark. Implemente um feature calculator simples (RSI, MACD, Bollinger) em ambas linguagens processando 100k ticks:

Python puro: ~500ms-1s Python + Rust via PyO3 (batch calls): ~50-100ms Rust puro: ~5-10ms

Para signal generation baseada em ML: Python sklearn RandomForest inference: ~1-5ms por prediction Rust tract ONNX: ~0.1-0.5ms por prediction Rust native implementation: ~0.05-0.2ms

Se você está operando em timeframes de 1+ segundos e processando dados que já têm 50ms+ de latência do Alpaca, diferença entre 1ms e 0.1ms é academica. Mas se você quer demonstrar understanding de real HFT constraints, Rust puro é a escolha.

Minha Recomendação Pragmática
Para portfólio com objetivo de demonstrar range completo de skills:

Opção 1 - Híbrida (mais ampla demonstração):

Core Rust para todo hot path
Python para training, backtesting, analysis
Bridge via model serialization (não runtime calls)
Documenta claramente que em prod ultra-low-latency, seria full Rust
Opção 2 - Rust Puro (mais tecnicamente pura):

Tudo em Rust incluindo backtesting
Scripts Python apenas para data download utilities
Demonstra deep Rust expertise e commitment to performance
Requer implementar mais infraestrutura (plotting, etc)
Opção 3 - Melhor dos Dois Mundos:

Dois branches: main com arquitetura híbrida educacional
Branch rust-pure com implementação full Rust otimizada
README compara performance e demonstra você entende trade-offs
Pessoalmente, para HFT portfolio específico, eu iria com Rust puro e documentaria o processo de portagem de modelos Python treinados para inference Rust. Isso demonstra que você entende que Python é ferramenta de research, não production runtime para latency-critical systems.

Mas honestamente, qualquer abordagem bem executada e bem documentada é valiosa. O importante é demonstrar que você conscientemente escolheu a arquitetura baseado em requirements claros, não por default ou desconhecimento das implicações.

Irei optar por 2 branchs uma com a arquitetura híbrida, e outra com Rust puro

Me diga como construir, quais APIs usar, e depois me dê as estruturas dos diretórios das duas bbranchs e comente brevemente o que é e como funcionam cada pasta e arquivos


Mapped out hybrid and pure Rust branch architectures comprehensively.




Estratégia de Construção e APIs
APIs e Data Sources Definidos
Para este sistema, vou especificar exatamente quais APIs e como usar cada uma:

Alpaca Markets será sua fonte primária para dados real-time e paper trading. Você precisa criar uma conta gratuita em alpaca.markets, obter API keys (key ID e secret key), e usar o endpoint paper trading https://paper-api.alpaca.markets. Para market data, você usará https://data.alpaca.markets com o tier gratuito IEX. O WebSocket endpoint é wss://stream.data.alpaca.markets/v2/iex para trades e quotes em tempo real. A Alpaca fornece trades (execuções individuais no mercado), quotes (bid/ask top-of-book), e bars (OHLCV agregados). Para paper trading, o WebSocket de updates de conta é wss://paper-api.alpaca.markets/stream onde você recebe confirmações de fills, updates de posições, e order status changes.

Polygon.io será usado exclusivamente para dados históricos massivos no backtesting. O tier gratuito oferece 5 API calls por minuto, suficiente para download batch de dados históricos. Você usará os endpoints de agregados /v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from}/{to} para baixar anos de bars históricos. O Polygon tem qualidade institucional e você pode baixar tick data se necessário (no tier pago, mas documente que seria usado em produção). Para o projeto, foque em daily/minute bars que o tier gratuito oferece.

Yahoo Finance via yfinance (biblioteca Python não-oficial) serve como backup e source alternativo para validação cruzada de dados históricos. Não tem API oficial, mas a biblioteca yfinance scrapes os dados de forma confiável. Use apenas para download histórico offline, nunca para dados real-time. Útil para ter anos de dados sem rate limits estritos.

Construção do Sistema: Workflow e Fases
A construção segue fases incrementais que permitem testar cada componente isoladamente antes de integração completa.

Fase 1 - Market Data Foundation: Comece implementando o market data feed que conecta ao WebSocket da Alpaca, processa mensagens JSON, e reconstrói order book. Este componente deve rodar standalone, logar todas as mensagens recebidas, e expor métricas de latência. Teste com 2-3 símbolos altamente líquidos (SPY, QQQ, AAPL). O objetivo é garantir conexão estável, reconnect automático em caso de disconnect, e processamento eficiente do stream. Implemente também o modo replay que lê dados históricos de arquivos Parquet e os envia como se fossem live data. Isso permite desenvolver outros componentes sem depender de mercado aberto.

Fase 2 - Feature Engineering e Storage: Implemente as features técnicas (RSI, MACD, etc) e microstructure (order book imbalance). Teste unitariamente cada indicador contra implementações conhecidas (ta-lib em Python como referência). Construa pipeline que persiste features calculadas em formato eficiente (Parquet com compressão) para uso posterior em training. Esta fase estabelece o vocabulário de features que ML models consumirão.

Fase 3 - ML Training Pipeline (Branch Híbrida) / Model Implementation (Branch Rust): Na branch híbrida, construa todo o pipeline de training em Python - data loading, feature preprocessing, model training, validation, hyperparameter tuning. Exporte modelos treinados para ONNX ou serialize weights. Na branch Rust pura, implemente os algoritmos de ML nativamente ou integre tract para ONNX runtime. Esta fase é onde as branches divergem significativamente.

Fase 4 - Backtesting Engine: Implemente event-driven backtester que processa dados históricos tick-by-tick, executa strategy logic, simula ordem execution com models de slippage realísticos, e tracked portfolio state. O backtester deve produzir métricas detalhadas - Sharpe ratio, maximum drawdown, win rate, average trade duration. Este componente valida se as estratégias funcionam antes de considerar paper trading.

Fase 5 - Risk Management e Execution: Integre risk manager que intercepta todos os signals antes de virarem orders, aplica position limits e stop-loss logic. O execution engine converte approved signals em orders Alpaca, tracked order lifecycle, e reconcilia fills esperados vs reais. Esta fase completa o loop de trading.

Fase 6 - Integration e Observability: Conecte todos os componentes via messaging (ZeroMQ), adicione instrumentação completa com métricas Prometheus, configure dashboards Grafana, e implemente structured logging com distributed tracing. Deploy com Docker Compose e teste end-to-end com replay de dados históricos.

Dependências e Ferramentas Específicas
Rust Dependencies que você vai usar extensivamente:

tokio (1.x) - async runtime, fundamental para tudo
tokio-tungstenite - WebSocket client para conectar Alpaca
serde e serde_json - serialization/deserialization de JSON
reqwest - HTTP client para REST API calls
zmq - ZeroMQ bindings para inter-process communication
chrono - date/time handling com nanosecond precision
tracing e tracing-subscriber - structured logging
metrics e metrics-exporter-prometheus - instrumentação
config - parsing de TOML config files
anyhow e thiserror - error handling ergonômico
arrow e parquet - leitura/escrita de Parquet files para dados históricos
ndarray - arrays N-dimensionais para cálculos numéricos
tract-onnx (branch híbrida) - ONNX runtime para rodar modelos Python
linfa (branch Rust pura) - ML algorithms nativos
smartcore (branch Rust pura) - alternativa para ML
Python Dependencies:

alpaca-py - SDK oficial Alpaca
websocket-client - WebSocket para consumir streams
pandas e numpy - data manipulation
scikit-learn - ML models tradicionais
pytorch ou tensorflow - deep learning se necessário
ta-lib ou pandas-ta - technical indicators
backtrader ou custom backtester
pyarrow - interface para Parquet files
matplotlib e seaborn - visualização
pytest - testing framework
maturin (branch híbrida) - build PyO3 extensions
Branch Híbrida: Estrutura Completa
hft-trading-system/  (branch: main)
│
├── README.md                                   # Overview completo, quickstart, arquitetura high-level
├── ARCHITECTURE.md                             # Deep dive em design decisions, data flow, componentes
├── HYBRID_APPROACH.md                          # Documenta rationale da abordagem híbrida
├── LICENSE                                     # MIT ou Apache 2.0
├── .gitignore                                  # Ignora target/, data/, .env, etc
├── Makefile                                    # Targets: setup, build, test, dev, prod, clean
├── .env.example                                # Template com ALPACA_API_KEY, ALPACA_SECRET, etc
│
├── .github/
│   └── workflows/
│       ├── rust-ci.yml                         # Cargo build, test, clippy, fmt para todos os crates
│       ├── python-ci.yml                       # pytest, flake8, black, mypy
│       ├── integration-tests.yml               # Sobe sistema completo e testa end-to-end
│       └── docker-build.yml                    # Build e push de images Docker
│
├── rust/                                       # Rust workspace root
│   ├── Cargo.toml                              # Workspace definition, shared dependencies
│   ├── Cargo.lock                              # Lockfile commitado para reproducibilidade
│   │
│   ├── market-data/                            # Binary crate: market data ingestion
│   │   ├── Cargo.toml                          # Dependencies: tokio, tungstenite, serde, zmq
│   │   ├── src/
│   │   │   ├── main.rs                         # Entry point, setup tracing, load config, start WebSocket
│   │   │   ├── lib.rs                          # Exports public API deste crate
│   │   │   │
│   │   │   ├── websocket/
│   │   │   │   ├── mod.rs                      # Module exports
│   │   │   │   ├── alpaca.rs                   # Alpaca WebSocket client, message parsing
│   │   │   │   ├── connection.rs               # Connection management, heartbeat handling
│   │   │   │   └── reconnect.rs                # Exponential backoff reconnect logic
│   │   │   │
│   │   │   ├── orderbook/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── book.rs                     # OrderBook struct com BTreeMap de levels
│   │   │   │   ├── level.rs                    # PriceLevel struct (price, size, timestamp)
│   │   │   │   └── reconstruction.rs           # Aplica updates incrementais, valida consistency
│   │   │   │
│   │   │   ├── aggregation/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── bars.rs                     # OHLCV bar generation de trades
│   │   │   │   ├── tick_processor.rs           # Processa individual trades, calcula derived metrics
│   │   │   │   └── windows.rs                  # Sliding time windows para aggregation
│   │   │   │
│   │   │   ├── feed/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── live.rs                     # Live data source via WebSocket
│   │   │   │   ├── replay.rs                   # Replay historical data de Parquet files
│   │   │   │   └── source.rs                   # Trait abstração para live vs replay
│   │   │   │
│   │   │   ├── publisher.rs                    # ZeroMQ PUB socket, broadcast market data
│   │   │   └── metrics.rs                      # Prometheus metrics: latency, msg/sec, reconnects
│   │   │
│   │   ├── tests/
│   │   │   ├── integration_tests.rs            # Testa WebSocket mock, orderbook updates
│   │   │   └── orderbook_tests.rs              # Unit tests para book reconstruction
│   │   │
│   │   └── benches/
│   │       └── orderbook_bench.rs              # Criterion benchmarks para hot path
│   │
│   ├── signal-bridge/                          # Library crate com PyO3 bindings
│   │   ├── Cargo.toml                          # Dependencies: pyo3, ndarray, serde
│   │   ├── pyproject.toml                      # Metadata para build com maturin
│   │   ├── src/
│   │   │   ├── lib.rs                          # PyO3 module definition, exports para Python
│   │   │   │
│   │   │   ├── features/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── technical.rs                # RSI, MACD, BB, ATR implementados com SIMD
│   │   │   │   ├── microstructure.rs           # Order book imbalance, spread, depth
│   │   │   │   ├── flow.rs                     # Trade flow toxicity, volume metrics
│   │   │   │   └── vectorized.rs               # SIMD operations usando std::simd
│   │   │   │
│   │   │   ├── bindings.rs                     # PyO3 wrappers, conversões numpy <-> ndarray
│   │   │   └── cache.rs                        # Cache de features calculadas para evitar recompute
│   │   │
│   │   └── tests/
│   │       ├── feature_tests.rs                # Valida features contra ta-lib reference
│   │       └── python_tests.py                 # Tests Python chamando Rust bindings
│   │
│   ├── signal-generator/                       # Binary crate: ML inference real-time
│   │   ├── Cargo.toml                          # Dependencies: tract-onnx, ndarray, zmq
│   │   ├── src/
│   │   │   ├── main.rs                         # Subscribe market data, run inference, publish signals
│   │   │   ├── lib.rs
│   │   │   │
│   │   │   ├── inference/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── onnx_runtime.rs             # Load ONNX model, run inference com tract
│   │   │   │   ├── ensemble.rs                 # Combina multiple models (voting, averaging)
│   │   │   │   └── preprocessor.rs             # Feature normalization, transformations
│   │   │   │
│   │   │   ├── signal.rs                       # Signal struct (action, confidence, timestamp)
│   │   │   └── models/                         # Directory com .onnx files carregados em runtime
│   │   │
│   │   └── tests/
│   │       └── inference_tests.rs              # Test inference com model fixtures
│   │
│   ├── risk-manager/                           # Binary crate: risk checks pre-trade
│   │   ├── Cargo.toml                          # Dependencies: zmq, serde, chrono
│   │   ├── src/
│   │   │   ├── main.rs                         # Subscribe signals, apply checks, publish approved orders
│   │   │   ├── lib.rs
│   │   │   │
│   │   │   ├── limits/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── position.rs                 # Max shares/contracts per symbol
│   │   │   │   ├── notional.rs                 # Max dollar exposure total e per symbol
│   │   │   │   ├── concentration.rs            # Diversification checks
│   │   │   │   └── validator.rs                # Valida order contra todos limits
│   │   │   │
│   │   │   ├── pnl/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── tracker.rs                  # Tracked current positions, avg entry prices
│   │   │   │   ├── calculator.rs               # Calcula unrealized/realized P&L
│   │   │   │   └── greeks.rs                   # Greeks simulation para options (demo)
│   │   │   │
│   │   │   ├── stops/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── static_stop.rs              # Stop-loss fixo
│   │   │   │   ├── trailing_stop.rs            # Trailing stop que adjust com price
│   │   │   │   └── time_stop.rs                # Exit position após N seconds/minutes
│   │   │   │
│   │   │   ├── circuit_breaker.rs              # Pausa trading se loss > threshold ou anomaly
│   │   │   ├── state.rs                        # In-memory state: positions, orders, P&L
│   │   │   └── persistence.rs                  # Persiste state para recovery após restart
│   │   │
│   │   └── tests/
│   │       ├── limits_tests.rs
│   │       └── pnl_tests.rs
│   │
│   ├── execution-engine/                       # Binary crate: order routing e fills
│   │   ├── Cargo.toml                          # Dependencies: reqwest, zmq, tokio
│   │   ├── src/
│   │   │   ├── main.rs                         # Subscribe approved orders, route to Alpaca, track fills
│   │   │   ├── lib.rs
│   │   │   │
│   │   │   ├── router/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── alpaca_client.rs            # REST API calls para submit orders
│   │   │   │   ├── order_builder.rs            # Constrói payloads Alpaca-specific
│   │   │   │   ├── retry.rs                    # Retry logic com exponential backoff
│   │   │   │   └── rate_limiter.rs             # Token bucket para respeitar API limits
│   │   │   │
│   │   │   ├── orders/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── types.rs                    # Order types: Market, Limit, Stop, Stop-Limit
│   │   │   │   ├── validator.rs                # Valida order parameters antes de submit
│   │   │   │   └── lifecycle.rs                # State machine: Pending -> Submitted -> Filled/Rejected
│   │   │   │
│   │   │   ├── sor/                            # Smart Order Routing strategies
│   │   │   │   ├── mod.rs
│   │   │   │   ├── twap.rs                     # Time-Weighted Average Price slicing
│   │   │   │   ├── vwap.rs                     # Volume-Weighted Average Price slicing
│   │   │   │   ├── iceberg.rs                  # Iceberg orders (show small, hide large)
│   │   │   │   └── adaptive.rs                 # Adaptive strategy baseada em market conditions
│   │   │   │
│   │   │   ├── slippage/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── estimator.rs                # Estima slippage baseado em order book depth
│   │   │   │   └── models.rs                   # Models de market impact
│   │   │   │
│   │   │   ├── fills.rs                        # Processa fill notifications via WebSocket
│   │   │   └── reconciliation.rs               # Reconcilia expected vs actual fills
│   │   │
│   │   └── tests/
│   │       ├── router_tests.rs
│   │       └── sor_tests.rs
│   │
│   ├── common/                                 # Library crate compartilhado
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       │
│   │       ├── types/                          # Domain types usados cross-system
│   │       │   ├── mod.rs
│   │       │   ├── market_data.rs              # Trade, Quote, Bar structs
│   │       │   ├── orders.rs                   # Order, Fill structs
│   │       │   ├── positions.rs                # Position, Portfolio structs
│   │       │   ├── events.rs                   # Event enums para messaging
│   │       │   └── symbol.rs                   # Symbol, Exchange enums
│   │       │
│   │       ├── messaging/
│   │       │   ├── mod.rs
│   │       │   ├── zeromq.rs                   # ZeroMQ wrapper, PUB/SUB/REQ/REP
│   │       │   ├── serialization.rs            # MessagePack ou bincode serialization
│   │       │   └── topics.rs                   # Topic definitions para PUB/SUB
│   │       │
│   │       ├── config/
│   │       │   ├── mod.rs
│   │       │   ├── parser.rs                   # Parse TOML configs usando config crate
│   │       │   └── validation.rs               # Valida configs carregados
│   │       │
│   │       ├── telemetry/
│   │       │   ├── mod.rs
│   │       │   ├── metrics.rs                  # Prometheus metrics helpers
│   │       │   ├── tracing.rs                  # Tracing setup, log formatting
│   │       │   └── spans.rs                    # Distributed tracing spans
│   │       │
│   │       └── time.rs                         # Time utilities, timezone handling
│   │
│   └── integration-tests/                      # Integration tests cross-crates
│       ├── Cargo.toml
│       ├── tests/
│       │   ├── end_to_end.rs                   # Sobe todos services, envia mock data, valida output
│       │   ├── latency_test.rs                 # Mede latency end-to-end
│       │   └── recovery_test.rs                # Test crash recovery, state persistence
│       │
│       └── fixtures/
│           ├── sample_trades.json              # Mock trade data para tests
│           ├── sample_quotes.json
│           └── test_config.toml
│
├── python/                                     # Python package
│   ├── pyproject.toml                          # PEP 518 build system, metadata
│   ├── setup.py                                # Fallback setup para compatibility
│   ├── requirements.txt                        # Runtime dependencies
│   ├── requirements-dev.txt                    # Development dependencies (pytest, black, etc)
│   │
│   ├── src/
│   │   └── trading_system/                     # Main package
│   │       ├── __init__.py
│   │       │
│   │       ├── ml/                             # Machine learning components
│   │       │   ├── __init__.py
│   │       │   │
│   │       │   ├── models/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── base.py                 # BaseModel abstract class
│   │       │   │   ├── random_forest.py        # RF wrapper com train/predict/export
│   │       │   │   ├── gradient_boost.py       # GBM wrapper
│   │       │   │   ├── lstm.py                 # PyTorch LSTM para sequences
│   │       │   │   └── ensemble.py             # Ensemble multiple models
│   │       │   │
│   │       │   ├── features/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── engineering.py          # Wrapper para chamar signal_bridge Rust
│   │       │   │   ├── transformers.py         # Sklearn transformers custom
│   │       │   │   └── selection.py            # Feature selection algorithms
│   │       │   │
│   │       │   ├── training/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── trainer.py              # Training loop, logging, checkpointing
│   │       │   │   ├── validator.py            # Cross-validation, time-series split
│   │       │   │   └── hyperopt.py             # Hyperparameter tuning com optuna
│   │       │   │
│   │       │   └── inference/
│   │       │       ├── __init__.py
│   │       │       ├── predictor.py            # Inference wrapper para models treinados
│   │       │       └── onnx_export.py          # Export models para ONNX format
│   │       │
│   │       ├── backtesting/                    # Backtesting framework
│   │       │   ├── __init__.py
│   │       │   │
│   │       │   ├── engine/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── event_driven.py         # Event-driven backtester core
│   │       │   │   ├── portfolio.py            # Portfolio state, position tracking
│   │       │   │   ├── broker_simulator.py     # Simula fills, slippage, commissions
│   │       │   │   └── data_handler.py         # Feed historical data como events
│   │       │   │
│   │       │   ├── strategies/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── base_strategy.py        # BaseStrategy abstract class
│   │       │   │   ├── ml_strategy.py          # Strategy usando ML predictions
│   │       │   │   └── mean_reversion.py       # Exemplo: mean reversion strategy
│   │       │   │
│   │       │   └── analysis/
│   │       │       ├── __init__.py
│   │       │       ├── metrics.py              # Sharpe, Sortino, max drawdown, etc
│   │       │       ├── visualization.py        # Plot equity curves, drawdowns
│   │       │       └── reports.py              # Generate HTML/PDF reports
│   │       │
│   │       ├── data/                           # Data management
│   │       │   ├── __init__.py
│   │       │   │
│   │       │   ├── loaders/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── alpaca_loader.py        # Download data via Alpaca API
│   │       │   │   ├── polygon_loader.py       # Download data via Polygon API
│   │       │   │   ├── parquet_loader.py       # Load/save Parquet files
│   │       │   │   └── csv_loader.py           # Load CSV files
│   │       │   │
│   │       │   ├── storage/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── data_lake.py            # Manage local data lake (Parquet organized)
│   │       │   │   └── cache.py                # Cache frequently accessed data
│   │       │   │
│   │       │   └── preprocessing/
│   │       │       ├── __init__.py
│   │       │       ├── cleaners.py             # Clean raw data, handle missing values
│   │       │       └── alignment.py            # Align multiple data sources temporalmente
│   │       │
│   │       └── utils/
│   │           ├── __init__.py
│   │           ├── config.py                   # Load Python configs, env vars
│   │           ├── logger.py                   # Setup Python logging
│   │           └── notifications.py            # Telegram/email notifications
│   │
│   ├── scripts/                                # Standalone scripts
│   │   ├── download_historical_data.py         # Download anos de data de Polygon/Alpaca
│   │   ├── train_model.py                      # Train ML model, export to ONNX
│   │   ├── run_backtest.py                     # Run full backtest com config file
│   │   ├── evaluate_model.py                   # Evaluate model performance
│   │   └── generate_report.py                  # Generate backtest report HTML
│   │
│   ├── notebooks/                              # Jupyter notebooks para research
│   │   ├── 01_data_exploration.ipynb           # Explore raw data, visualize
│   │   ├── 02_feature_analysis.ipynb           # Analyze features, correlations
│   │   ├── 03_model_development.ipynb          # Develop e tune models
│   │   ├── 04_backtest_analysis.ipynb          # Analyze backtest results
│   │   └── 05_live_monitoring.ipynb            # Monitor live system (read logs/metrics)
│   │
│   └── tests/                                  # Python tests
│       ├── __init__.py
│       ├── conftest.py                         # Pytest fixtures
│       │
│       ├── test_ml/
│       │   ├── test_models.py
│       │   ├── test_features.py
│       │   └── test_training.py
│       │
│       ├── test_backtesting/
│       │   ├── test_engine.py
│       │   ├── test_strategies.py
│       │   └── test_metrics.py
│       │
│       └── test_data/
│           ├── test_loaders.py
│           └── test_preprocessing.py
│
├── config/                                     # Configuration files
│   ├── dev/                                    # Development environment
│   │   ├── market-data.toml                    # Market data config: symbols, WebSocket URL
│   │   ├── signal-generator.toml               # Model paths, inference params
│   │   ├── risk-manager.toml                   # Risk limits, stop-loss levels
│   │   ├── execution-engine.toml               # Alpaca endpoints, retry config
│   │   └── symbols.toml                        # Trading universe definition
│   │
│   ├── prod/                                   # Production (paper trading)
│   │   ├── market-data.toml
│   │   ├── signal-generator.toml
│   │   ├── risk-manager.toml
│   │   ├── execution-engine.toml
│   │   └── symbols.toml
│   │
│   └── backtest/                               # Backtesting configs
│       ├── strategy-params.toml                # Strategy hyperparameters
│       ├── universe.toml                       # Symbols para backtest
│       └── simulation.toml                     # Slippage models, commission rates
│
├── data/                                       # Data directory (gitignored)
│   ├── raw/                                    # Raw downloaded data
│   │   ├── alpaca/
│   │   ├── polygon/
│   │   └── yahoo/
│   │
│   ├── processed/                              # Processed Parquet files
│   │   ├── bars/                               # OHLCV bars por symbol
│   │   ├── trades/                             # Individual trades
│   │   └── features/                           # Computed features
│   │
│   ├── models/                                 # Trained models
│   │   ├── production/                         # Production-ready models
│   │   │   └── rf_classifier_v1.onnx
│   │   └── experiments/                        # Experimental models
│   │
│   └── results/                                # Results de backtests/live runs
│       ├── backtests/
│       └── live-runs/
│
├── docker/                                     # Dockerfiles
│   ├── Dockerfile.market-data                  # Multi-stage build: Rust build + runtime
│   ├── Dockerfile.signal-generator             # Rust binary + ONNX runtime
│   ├── Dockerfile.risk-manager
│   ├── Dockerfile.execution-engine
│   ├── Dockerfile.python-services              # Python environment para scripts
│   └── Dockerfile.monitoring                   # Prometheus + Grafana
│
├── deploy/                                     # Deployment orchestration
│   ├── docker-compose.yml                      # Base compose file
│   ├── docker-compose.dev.yml                  # Override para dev: volumes, hot reload
│   ├── docker-compose.prod.yml                 # Override para prod: resource limits
│   │
│   └── scripts/
│       ├── setup.sh                            # Initial setup: create dirs, download base data
│       ├── start-system.sh                     # Start all services via compose
│       ├── stop-system.sh                      # Graceful shutdown
│       └── logs.sh                             # Tail logs de todos services
│
├── monitoring/                                 # Observability stack
│   ├── prometheus/
│   │   ├── prometheus.yml                      # Scrape configs para todos services
│   │   └── alerts.yml                          # Alert rules: high latency, loss threshold
│   │
│   ├── grafana/
│   │   ├── dashboards/                         # JSON dashboards
│   │   │   ├── system-overview.json            # High-level metrics
│   │   │   ├── market-data.json                # Market data latency, msg rate
│   │   │   ├── execution.json                  # Orders, fills, slippage
│   │   │   └── pnl.json                        # P&L, positions, Sharpe
│   │   │
│   │   └── provisioning/                       # Auto-provision datasources/dashboards
│   │       ├── datasources/
│   │       │   └── prometheus.yml
│   │       └── dashboards/
│   │           └── dashboard.yml
│   │
│   └── loki/                                   # Log aggregation (opcional)
│       └── loki-config.yml
│
├── docs/                                       # Documentation
│   ├── architecture/
│   │   ├── overview.md                         # System architecture overview
│   │   ├── data-flow.md                        # Data flow diagrams, sequence diagrams
│   │   ├── hybrid-design.md                    # Why hybrid Python+Rust
│   │   ├── deployment.md                       # Deployment architecture
│   │   └── diagrams/
│   │       ├── system-architecture.mmd         # Mermaid diagram
│   │       └── component-interaction.mmd
│   │
│   ├── api/                                    # API documentation
│   │   ├── market-data-api.md                  # ZeroMQ topics, message formats
│   │   ├── risk-manager-api.md
│   │   └── execution-api.md
│   │
│   ├── development/
│   │   ├── setup.md                            # Como setup dev environment
│   │   ├── building.md                         # Como buildar cada componente
│   │   ├── testing.md                          # Testing strategy, como rodar tests
│   │   ├── adding-features.md                  # Como adicionar novas features
│   │   └── contributing.md                     # Contribution guidelines
│   │
│   ├── operations/
│   │   ├── deployment.md                       # Como deployar sistema
│   │   ├── monitoring.md                       # Como usar Grafana dashboards
│   │   ├── troubleshooting.md                  # Common issues e solutions
│   │   └── performance-tuning.md               # Tuning tips
│   │
│   └── research/
│       ├── feature-engineering.md              # Features implementadas
│       ├── model-selection.md                  # Models testados, results
│       └── backtesting-methodology.md          # Backtesting approach
│
├── scripts/                                    # Utility scripts
│   ├── setup-dev-env.sh                        # Install Rust, Python, dependencies
│   ├── run-tests.sh                            # Run all tests (Rust + Python)
│   ├── build-all.sh                            # Build all Rust crates
│   ├── lint-all.sh                             # Run linters (clippy, flake8)
│   └── check-apis.sh                           # Verify API keys são válidos
│
└── results/                                    # Runtime results (gitignored)
    ├── backtests/
    │   └── 2025-01-15_strategy_v1/
    │       ├── config.toml
    │       ├── trades.csv
    │       ├── equity_curve.png
    │       └── report.html
    │
    └── live-runs/
        └── 2025-01-16_paper_trading/
            ├── orders.csv
            ├── fills.csv
            └── metrics.json
```

### Explicação dos Componentes Críticos - Branch Híbrida

**Rust Market Data**: Este é o coração do sistema real-time. O `main.rs` inicializa tracing, carrega configs de TOML, estabelece conexão WebSocket com Alpaca usando `tokio-tungstenite`, e spawna async tasks para processar mensagens. O módulo `websocket/alpaca.rs` parseia JSON messages específicos do Alpaca (trades, quotes) usando `serde_json` e converte para tipos internos definidos em `common/types/market_data.rs`. O `orderbook/book.rs` mantém dois BTreeMaps (bids e asks) ordenados por price, com métodos para inserir, atualizar, e deletar levels. Reconstruction logic aplica updates sequencialmente validando sequence numbers. O `aggregation/bars.rs` usa sliding time windows para acumular trades e gerar OHLCV bars de diferentes timeframes. O `feed/replay.rs` implementa a mesma interface que `live.rs` mas lê de Parquet files, permitindo testar todo downstream sem mercado aberto. O `publisher.rs` usa ZeroMQ PUB socket para broadcast de todos market events - outros componentes subscrevem topics específicos (e.g., "trades.SPY", "orderbook.AAPL").

**Signal Bridge (PyO3)**: Este crate compila para shared library que Python importa. O `lib.rs` define `#[pymodule]` com funções expostas para Python. Features em `features/technical.rs` implementam indicadores usando loops otimizados ou SIMD instructions via `std::simd`. Funções recebem numpy arrays (convertidos para `ndarray` via PyO3), processam em Rust com zero-copy quando possível, e retornam numpy arrays. O `cache.rs` usa HashMap com LRU eviction para cachear features já calculadas, evitando recomputação desnecessária. Build via `maturin build --release` gera wheel que instala no Python environment.

**Signal Generator (Rust)**: Subscribes a ZeroMQ topic de market data, usa features do signal-bridge para calcular indicators, carrega ONNX model via `tract` no startup (model está em `models/production/`), e roda inference a cada novo bar ou tick. O `onnx_runtime.rs` wrappea tract para simplificar loading e inference. Features são normalizadas usando stats salvos durante training (mean/std de cada feature), passadas como tensor para o model, e output (probabilidade de up/down) é convertido em Signal struct com action (Buy/Sell/Hold) e confidence. Signals são published via ZeroMQ para o risk manager.

**Risk Manager**: Subscribes signals do signal generator, mantém state de posições atuais em `state.rs` (HashMap de symbol para Position), aplica cada check sequencialmente (position limits, notional limits, stop-loss). Se signal passa todos checks, é aprovado e forwarded para execution engine. Se falha, é rejeitado e logged. O `pnl/tracker.rs` atualiza unrealized P&L a cada market data update usando current mid price. Circuit breaker em `circuit_breaker.rs` monitora loss rate - se perder mais que X% em Y minutes, entra em pause mode e rejeita todos signals até manual reset.

**Execution Engine**: Subscribes approved orders, constrói payload Alpaca-specific em `router/order_builder.rs`, submete via HTTP POST usando `reqwest` com retry logic. O `rate_limiter.rs` usa token bucket algorithm para não exceder 200 requests/minute da Alpaca. Submitted orders são tracked em HashMap com lifecycle state. O `fills.rs` subscribes ao WebSocket de updates da Alpaca e processa fill notifications, updating order state e publishando fill events para risk manager atualizar positions. SOR strategies em `sor/` sliceiam orders grandes em child orders menores executados ao longo do tempo ou baseado em volume.

**Python ML Pipeline**: O `scripts/train_model.py` carrega dados históricos de `data/processed/`, chama `signal_bridge` para calcular features em batch (muito mais rápido que Python puro), treina RandomForest ou GradientBoosting usando sklearn com cross-validation temporal, tuning de hyperparameters com `optuna`, e exporta model final para ONNX usando `skl2onnx`. O `backtesting/engine/event_driven.py` simula trading: lê historical bars, chama strategy para gerar signals, simula broker fills com slippage model, tracked portfolio state, e calcula metrics no final. Results são salvos em `results/backtests/` com plots de equity curve, drawdown, e HTML report.

**Docker Compose**: O `docker-compose.yml` define services para cada componente Rust, Prometheus, Grafana. Cada Rust service tem `depends_on` declarando dependencies (e.g., signal-generator depends on market-data). Networks são definidas para isolar services. Volumes mapeiam `config/` read-only e `data/` read-write. O `docker-compose.dev.yml` adiciona volumes para source code permitindo rebuild sem rebuild image, e expõe portas adicionais para debugging.

---

## Branch Rust Puro: Estrutura Completa
```
hft-trading-system/  (branch: rust-pure)
│
├── README.md                                   # Foca em performance pura, all-Rust approach
├── ARCHITECTURE.md                             # Documenta decisões de usar Rust puro
├── RUST_PURE_RATIONALE.md                      # Por que Rust puro, benchmarks vs híbrido
├── LICENSE
├── .gitignore
├── Makefile                                    # Targets similares mas sem Python
├── .env.example
│
├── .github/
│   └── workflows/
│       ├── rust-ci.yml                         # Comprehensive Rust testing
│       ├── integration-tests.yml
│       └── benchmarks.yml                      # Run benchmarks, track performance over time
│
├── rust/                                       # Rust workspace
│   ├── Cargo.toml                              # Workspace com todos crates
│   ├── Cargo.lock
│   │
│   ├── market-data/                            # Identical à branch híbrida
│   │   ├── Cargo.toml
│   │   ├── src/
│   │   │   ├── main.rs
│   │   │   ├── lib.rs
│   │   │   ├── websocket/
│   │   │   ├── orderbook/
│   │   │   ├── aggregation/
│   │   │   ├── feed/
│   │   │   ├── publisher.rs
│   │   │   └── metrics.rs
│   │   ├── tests/
│   │   └── benches/
│   │
│   ├── features/                               # Native Rust feature engineering
│   │   ├── Cargo.toml                          # Dependencies: ndarray, ndarray-stats
│   │   ├── src/
│   │   │   ├── lib.rs                          # Public API para outros crates
│   │   │   │
│   │   │   ├── technical/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── momentum.rs                 # RSI, ROC, MOM
│   │   │   │   ├── trend.rs                    # SMA, EMA, MACD, ADX
│   │   │   │   ├── volatility.rs               # Bollinger Bands, ATR, Keltner
│   │   │   │   └── volume.rs                   # OBV, Volume Profile
│   │   │   │
│   │   │   ├── microstructure/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── imbalance.rs                # Order book imbalance metrics
│   │   │   │   ├── spread.rs                   # Bid-ask spread, effective spread
│   │   │   │   ├── depth.rs                    # Market depth metrics
│   │   │   │   └── toxicity.rs                 # VPIN, order flow toxicity
│   │   │   │
│   │   │   ├── statistical/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── returns.rs                  # Log returns, realized volatility
│   │   │   │   ├── correlation.rs              # Rolling correlations
│   │   │   │   └── distribution.rs             # Skewness, kurtosis
│   │   │   │
│   │   │   ├── vectorized/
│   │   │   │   ├── mod.rs
│   │   │   │   └── simd_ops.rs                 # SIMD-accelerated operations
│   │   │   │
│   │   │   └── cache.rs                        # Feature cache para evitar recalc
│   │   │
│   │   ├── tests/
│   │   │   └── technical_tests.rs              # Valida features contra known values
│   │   │
│   │   └── benches/
│   │       └── feature_bench.rs                # Benchmark cada feature
│   │
│   ├── ml/                                     # Native Rust ML implementation
│   │   ├── Cargo.toml                          # Dependencies: linfa, smartcore, ndarray
│   │   ├── src/
│   │   │   ├── lib.rs
│   │   │   │
│   │   │   ├── models/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── random_forest.rs            # RF usando linfa ou smartcore
│   │   │   │   ├── gradient_boost.rs           # GBM implementation
│   │   │   │   ├── linear.rs                   # Logistic regression, Ridge
│   │   │   │   └── ensemble.rs                 # Ensemble methods
│   │   │   │
│   │   │   ├── training/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── trainer.rs                  # Training loop, validation
│   │   │   │   ├── cv.rs                       # Cross-validation logic
│   │   │   │   └── metrics.rs                  # Accuracy, F1, ROC-AUC
│   │   │   │
│   │   │   ├── preprocessing/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── scaler.rs                   # StandardScaler, MinMaxScaler
│   │   │   │   ├── encoder.rs                  # Label encoding
│   │   │   │   └── imputer.rs                  # Handle missing values
│   │   │   │
│   │   │   ├── inference/
│   │   │   │   ├── mod.rs
│   │   │   │   └── predictor.rs                # Inference engine
│   │   │   │
│   │   │   └── serialization/
│   │   │       ├── mod.rs
│   │   │       └── serde_model.rs              # Serialize/deserialize models
│   │   │
│   │   └── tests/
│   │       ├── model_tests.rs
│   │       └── training_tests.rs
│   │
│   ├── signal-generator/                       # ML inference em Rust nativo
│   │   ├── Cargo.toml                          # Dependencies: ml crate, features crate
│   │   ├── src/
│   │   │   ├── main.rs                         # Load model, subscribe data, run inference
│   │   │   ├── lib.rs
│   │   │   │
│   │   │   ├── inference/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── engine.rs                   # Inference engine usando ml crate
│   │   │   │   ├── ensemble.rs                 # Combine multiple models
│   │   │   │   └── preprocessor.rs             # Feature preprocessing
│   │   │   │
│   │   │   ├── signal.rs                       # Signal generation logic
│   │   │   └── models/                         # Serialized model files
│   │   │
│   │   └── tests/
│   │       └── inference_tests.rs
│   │
│   ├── backtesting/                            # Event-driven backtester em Rust
│   │   ├── Cargo.toml
│   │   ├── src/
│   │   │   ├── lib.rs
│   │   │   │
│   │   │   ├── engine/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── event_loop.rs               # Main event processing loop
│   │   │   │   ├── data_handler.rs             # Feed historical data como events
│   │   │   │   └── clock.rs                    # Simulation clock
│   │   │   │
│   │   │   ├── portfolio/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── portfolio.rs                # Portfolio state management
│   │   │   │   ├── position.rs                 # Position tracking
│   │   │   │   └── performance.rs              # Performance tracking
│   │   │   │
│   │   │   ├── broker/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── simulator.rs                # Simula fills, slippage
│   │   │   │   ├── slippage_model.rs           # Models de slippage
│   │   │   │   └── commission.rs               # Commission calculation
│   │   │   │
│   │   │   ├── strategy/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── base.rs                     # Strategy trait
│   │   │   │   └── ml_strategy.rs              # ML-based strategy implementation
│   │   │   │
│   │   │   └── metrics/
│   │   │       ├── mod.rs
│   │   │       ├── returns.rs                  # Return calculations
│   │   │       ├── risk.rs                     # Sharpe, Sortino, max drawdown
│   │   │       └── trades.rs                   # Trade statistics
│   │   │
│   │   ├── tests/
│   │   │   └── backtest_tests.rs
│   │   │
│   │   └── examples/
│   │       └── run_backtest.rs                 # Example backtest run
│   │
│   ├── risk-manager/                           # Identical à branch híbrida
│   │   ├── Cargo.toml
│   │   ├── src/
│   │   │   ├── main.rs
│   │   │   ├── lib.rs
│   │   │   ├── limits/
│   │   │   ├── pnl/
│   │   │   ├── stops/
│   │   │   ├── circuit_breaker.rs
│   │   │   ├── state.rs
│   │   │   └── persistence.rs
│   │   └── tests/
│   │
│   ├── execution-engine/                       # Identical à branch híbrida
│   │   ├── Cargo.toml
│   │   ├── src/
│   │   │   ├── main.rs
│   │   │   ├── lib.rs
│   │   │   ├── router/
│   │   │   ├── orders/
│   │   │   ├── sor/
│   │   │   ├── slippage/
│   │   │   ├── fills.rs
│   │   │   └── reconciliation.rs
│   │   └── tests/
│   │
│   ├── data-tools/                             # Data download e management em Rust
│   │   ├── Cargo.toml                          # Dependencies: reqwest, parquet, arrow
│   │   ├── src/
│   │   │   ├── lib.rs
│   │   │   │
│   │   │   ├── loaders/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── alpaca.rs                   # Alpaca REST API data download
│   │   │   │   ├── polygon.rs                  # Polygon REST API
│   │   │   │   └── parquet.rs                  # Read/write Parquet
│   │   │   │
│   │   │   ├── storage/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── data_lake.rs                # Organize Parquet files
│   │   │   │   └── catalog.rs                  # Metadata catalog de datasets
│   │   │   │
│   │   │   └── preprocessing/
│   │   │       ├── mod.rs
│   │   │       ├── cleaning.rs                 # Data cleaning
│   │   │       └── alignment.rs                # Temporal alignment
│   │   │
│   │   ├── examples/
│   │   │   ├── download_data.rs                # CLI para download data
│   │   │   └── convert_to_parquet.rs           # Convert CSV to Parquet
│   │   │
│   │   └── tests/
│   │       └── loader_tests.rs
│   │
│   ├── analysis/                               # Analysis e reporting tools em Rust
│   │   ├── Cargo.toml                          # Dependencies: plotters para charting
│   │   ├── src/
│   │   │   ├── lib.rs
│   │   │   │
│   │   │   ├── visualization/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── equity_curve.rs             # Plot equity curves usando plotters
│   │   │   │   ├── drawdown.rs                 # Drawdown plots
│   │   │   │   └── distributions.rs            # Return distributions
│   │   │   │
│   │   │   ├── reports/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── backtest_report.rs          # Generate backtest reports
│   │   │   │   └── html_generator.rs           # Generate HTML reports
│   │   │   │
│   │   │   └── statistics/
│   │   │       ├── mod.rs
│   │   │       └── descriptive.rs              # Descriptive statistics
│   │   │
│   │   ├── examples/
│   │   │   └── generate_report.rs
│   │   │
│   │   └── tests/
│   │       └── report_tests.rs
│   │
│   ├── cli/                                    # CLI tools unificado
│   │   ├── Cargo.toml                          # Dependencies: clap para CLI parsing
│   │   ├── src/
│   │   │   ├── main.rs                         # Main CLI entry, subcommands
│   │   │   │
│   │   │   ├── commands/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── data.rs                     # Data download commands
│   │   │   │   ├── train.rs                    # Model training commands
│   │   │   │   ├── backtest.rs                 # Backtest commands
│   │   │   │   ├── live.rs                     # Live trading commands
│   │   │   │   └── report.rs                   # Report generation commands
│   │   │   │
│   │   │   └── utils.rs                        # CLI utilities
│   │   │
│   │   └── tests/
│   │       └── cli_tests.rs
│   │
│   ├── common/                                 # Shared library (similar à híbrida)
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── types/
│   │       ├── messaging/
│   │       ├── config/
│   │       ├── telemetry/
│   │       └── time.rs
│   │
│   └── integration-tests/
│       ├── Cargo.toml
│       ├── tests/
│       │   ├── end_to_end.rs
│       │   ├── latency_test.rs
│       │   ├── ml_pipeline_test.rs             # Test complete ML pipeline
│       │   └── backtest_integration.rs
│       └── fixtures/
│
├── config/                                     # Similar à híbrida mas sem Python configs
│   ├── dev/
│   ├── prod/
│   └── backtest/
│
├── data/                                       # Similar à híbrida
│   ├── raw/
│   ├── processed/
│   ├── models/                                 # Serialized Rust models (não ONNX)
│   └── results/
│
├── docker/                                     # Dockerfiles para cada componente
│   ├── Dockerfile.market-data
│   ├── Dockerfile.signal-generator
│   ├── Dockerfile.risk-manager
│   ├── Dockerfile.execution-engine
│   ├── Dockerfile.cli-tools                    # CLI tools container
│   └── Dockerfile.monitoring
│
├── deploy/
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   ├── docker-compose.prod.yml
│   └── scripts/
│
├── monitoring/                                 # Identical à híbrida
│   ├── prometheus/
│   ├── grafana/
│   └── loki/
│
├── docs/
│   ├── architecture/
│   │   ├── overview.md
│   │   ├── rust-pure-design.md                 # Why all-Rust approach
│   │   ├── performance.md                      # Performance benchmarks
│   │   └── diagrams/
│   │
│   ├── api/
│   ├── development/
│   │   ├── setup.md
│   │   ├── building-rust.md                    # Rust-specific build instructions
│   │   ├── ml-in-rust.md                       # Guide to ML in Rust
│   │   └── testing.md
│   │
│   ├── operations/
│   └── research/
│       └── ml-algorithms.md                    # ML algorithms implemented
│
├── scripts/
│   ├── setup-dev-env.sh                        # Only Rust toolchain
│   ├── run-tests.sh
│   ├── build-all.sh
│   ├── lint-all.sh
│   └── benchmark-all.sh                        # Run all benchmarks
│
├── benchmarks/                                 # Dedicated benchmarks directory
│   ├── results/                                # Store benchmark results over time
│   └── compare.sh                              # Compare with hybrid branch
│
└── results/
    ├── backtests/
    └── live-runs/
Explicação dos Componentes Únicos - Branch Rust Pura
Features Crate: Este é replacement completo do PyO3 bridge. Todas as features são implementadas nativamente em Rust usando ndarray para operações vectoriais. O technical/momentum.rs implementa RSI usando algoritmo eficiente com rolling windows - mantém deques de gains e losses, atualiza incrementalmente sem recalcular toda janela. SIMD em vectorized/simd_ops.rs usa std::simd para processar múltiplos valores simultaneamente - por exemplo, calcular returns de 8 preços em paralelo com uma instrução. Microstructure features em microstructure/imbalance.rs calculam ratios de volume bid/ask nos top N levels do order book, métricas que indicam pressure direcional. Todos os cálculos retornam ndarray::Array1<f64> que são zero-copy compatíveis com outros crates.

ML Crate: Implementa algoritmos de ML nativamente ou usa linfa/smartcore. O models/random_forest.rs pode usar linfa-trees que fornece implementação DecisionTree e RandomForest. Para treino, você carrega dados como ndarray::Array2, split em train/test, e chama fit(). O model treinado é serializado usando serde e bincode para formato binário compacto. Durante inference, você desserializa o model uma vez no startup e chama predict() com features novas. O preprocessing/scaler.rs implementa StandardScaler - calcula mean e std durante fit, aplica transformação (x - mean) / std durante transform. A vantagem é que tudo roda no mesmo address space sem FFI overhead, e você tem controle total de memory layout.

Backtesting Crate: Este é event-driven backtester completo em Rust. O engine/event_loop.rs processa events em ordem temporal - data events (novos bars), signal events (strategy gerou signal), order events (order submetida), e fill events (order executada). O data_handler.rs lê Parquet files usando arrow e converte rows em data events. O portfolio/portfolio.rs mantém state de posições, cash, e calcula equity. O broker/simulator.rs simula fills - para market orders, fill imediatamente no mid price mais slippage; para limit orders, check se price foi hit durante bar. Slippage model em slippage_model.rs pode ser constante (X bps) ou adaptativo baseado em volatility e volume. No final, metrics/ calcula comprehensive statistics - Sharpe, Sortino, Calmar, maximum drawdown com duration, win rate, profit factor, average trade duration. Results são salvos em Parquet e CSV. O analysis/visualization/ usa plotters para gerar PNG plots de equity curve, drawdown, e return distributions.

Data Tools Crate: Fornece CLI e library functions para data management. O loaders/alpaca.rs usa reqwest para fazer GET requests ao Alpaca REST API, parseia JSON responses, e salva em Parquet. O storage/data_lake.rs organiza Parquet files em structure hierárquica: data/processed/bars/SPY/2024/01/SPY_2024-01-15.parquet. O catalog.rs mantém metadata de todos datasets - symbols disponíveis, date ranges, schema. Isso permite queries rápidas sem scan filesystem. O CLI em examples/download_data.rs acepta arguments como --symbols SPY,QQQ --start 2024-01-01 --end 2024-12-31 e baixa data em batch com progress bar.

Analysis Crate: Focado em reporting e visualization pós-backtest. O visualization/equity_curve.rs usa plotters para criar plot com equity curve, drawdowns shaded, e markers em trades. plotters é pure Rust charting library que renderiza para PNG, SVG, ou HTML canvas. O reports/html_generator.rs cria HTML report com embedded plots, tables de metrics, e interactive elements usando templates. O HTML é self-contained (CSS inline, images base64 encoded) para fácil sharing.

CLI Crate: Unifica todos os comandos do sistema em um binary. O main.rs usa clap para definir subcommands: hft-cli data download, hft-cli train --config configs/train.toml, hft-cli backtest --strategy ml --start 2024-01-01, hft-cli live --mode paper, hft-cli report --backtest-id 123. Cada subcommand em commands/ invoca as libraries apropriadas. Isso fornece interface consistente e facilita scripting - você pode chain commands em bash scripts.

Workflow Entre Branches
Branch Híbrida (main) é onde você desenvolve e experimenta rapidamente. Python permite iteração rápida em feature engineering, model selection, e backtesting analysis. Notebooks facilitam exploração interativa. O bridge PyO3 demonstra polyglot systems engineering. Você usa esta branch para:

Research de novas features e models
Rapid prototyping de strategies
Análise exploratória de dados
Desenvolvimento de dashboards e reports
Branch Rust Pura (rust-pure) é onde você porta componentes otimizados para máxima performance. Você migra após validar no híbrido. Use esta branch para:

Demonstrar performance optimization
Benchmark contra versão híbrida
Mostrar compreensão de low-level optimization
Produzir binários standalone para deployment
Workflow Típico:

Desenvolve nova feature em Python na branch main
Valida que feature melhora model performance via backtest
Implementa mesma feature nativamente em Rust na branch rust-pure
Benchmarka ambas versões, documenta speedup
Mergeia documentação de volta ao main
Mantém ambas branches sincronizadas para configs e docs
Commits e Mensagens: Use commits que referenciem cross-branch - "Implement RSI in native Rust (equivalent to main branch PyO3 version)" ou "Backtest results confirm 15% better Sharpe vs main branch baseline". Isso demonstra que você pensa em trade-offs conscientemente.

Esta estrutura dual-branch permite você demonstrar tanto breadth (polyglot, ML engineering, data science) quanto depth (low-latency Rust, performance optimization, systems programming). O README de cada branch claramente indica propósito e trade-offs, e ambos apontam um para o outro para comparação.






