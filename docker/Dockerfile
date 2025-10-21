# Multi-stage Dockerfile for Rust Trading System
# Stage 1: Build environment
FROM rust:1.75-slim-bookworm as builder

# Install dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    libzmq3-dev \
    cmake \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy manifests
COPY Cargo.toml Cargo.lock ./
COPY src ./src

# Build dependencies (cached layer)
RUN mkdir -p src/bin && \
    echo "fn main() {}" > src/bin/dummy.rs && \
    cargo build --release --bin dummy && \
    rm -rf src/bin/dummy.rs

# Build the actual application with optimizations
ENV RUSTFLAGS="-C link-arg=-s -C lto=fat -C embed-bitcode=yes"
RUN cargo build --release --workspace

# Strip binaries to reduce size
RUN strip /app/target/release/market_data_service || true && \
    strip /app/target/release/order_execution_service || true && \
    strip /app/target/release/risk_management_service || true && \
    strip /app/target/release/strategy_engine || true && \
    strip /app/target/release/api_gateway || true

# Stage 2: Runtime environment for market_data_service
FROM debian:bookworm-slim as market_data_service

RUN apt-get update && apt-get install -y \
    libssl3 \
    libzmq5 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/target/release/market_data_service ./
COPY .env.example .env

EXPOSE 5555
CMD ["./market_data_service"]

# Stage 3: Runtime environment for order_execution_service
FROM debian:bookworm-slim as order_execution_service

RUN apt-get update && apt-get install -y \
    libssl3 \
    libzmq5 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/target/release/order_execution_service ./
COPY .env.example .env

EXPOSE 5556
CMD ["./order_execution_service"]

# Stage 4: Runtime environment for risk_management_service
FROM debian:bookworm-slim as risk_management_service

RUN apt-get update && apt-get install -y \
    libssl3 \
    libzmq5 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/target/release/risk_management_service ./
COPY .env.example .env

EXPOSE 5557
CMD ["./risk_management_service"]

# Stage 5: Runtime environment for strategy_engine
FROM debian:bookworm-slim as strategy_engine

RUN apt-get update && apt-get install -y \
    libssl3 \
    libzmq5 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/target/release/strategy_engine ./
COPY .env.example .env

EXPOSE 5558
CMD ["./strategy_engine"]

# Stage 6: Runtime environment for api_gateway
FROM debian:bookworm-slim as api_gateway

RUN apt-get update && apt-get install -y \
    libssl3 \
    libzmq5 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/target/release/api_gateway ./
COPY .env.example .env

EXPOSE 8080
CMD ["./api_gateway"]
