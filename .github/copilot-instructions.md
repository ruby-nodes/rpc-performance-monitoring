# Ethereum Node Monitor - Copilot Instructions

This project monitors Ethereum-based blockchain fullnodes (geth and reth) to detect and analyze desync issues.

## Project Context
- **Purpose**: Monitor BSC (geth) and Base (reth) nodes for synchronization issues
- **Networks**: BSC mainnet and Base mainnet
- **Key Features**: IPC communication, Prometheus metrics collection, correlation analysis, AI-ready logging

## Technical Stack
- **Language**: Python 3.8+
- **Key Libraries**: asyncio, prometheus_client, web3, sqlite3, json
- **Monitoring**: Prometheus metrics scraping from port 9090
- **Communication**: IPC sockets for node communication
- **Analysis**: Statistical correlation and anomaly detection

## Network-Specific Configuration
- **BSC (geth)**: IPC at `/var/lib/bsc/geth.ipc`, RPC at `https://bsc-dataseed.bnbchain.org/`
- **Base (reth)**: IPC at `/tmp/reth.ipc`, RPC at `https://mainnet.base.org`

## Code Style Guidelines
- Use type hints for all function parameters and return values
- Follow async/await patterns for I/O operations
- Implement comprehensive error handling with specific exceptions
- Use structured logging with JSON format for desync events
- Include docstrings with examples for complex functions

## Key Implementation Notes
- Auto-detect node type (geth vs reth) from IPC responses
- Collect Prometheus metrics every 5 seconds during normal operation
- Create detailed desync logs with 10-minute context windows
- Implement correlation analysis between metrics and desync events
- Generate AI-ready analysis prompts for each desync event