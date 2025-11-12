# Ethereum Node Monitor

A comprehensive monitoring system for Ethereum-based blockchain fullnodes (geth and reth) designed to detect and analyze synchronization issues with AI-ready logging and correlation analysis.

## 🎯 Purpose

This system monitors BSC (geth) and Base (reth) nodes to detect desynchronization events, analyze their causes, and provide detailed insights for improving node reliability. It features real-time metrics collection, anomaly detection, and AI-optimized logging for advanced analysis.

## ✨ Key Features

- **Universal Node Support**: Auto-detects and monitors both geth and reth nodes
- **Real-time Desync Detection**: Monitors sync status with configurable thresholds
- **Prometheus Integration**: Collects and analyzes comprehensive metrics
- **Anomaly Detection**: Statistical analysis of metrics patterns
- **AI-Ready Logging**: Structured JSON logs optimized for AI analysis
- **Correlation Analysis**: Links metrics patterns with desync events
- **Multi-Network Support**: BSC mainnet and Base mainnet ready
- **Comprehensive Storage**: SQLite database for historical analysis

## 🏗️ Architecture

```
src/
├── core/           # Core communication modules
├── monitoring/     # Sync and metrics monitoring
├── logging/        # AI-optimized desync logging
├── storage/        # Database and data models
├── analysis/       # Correlation and pattern analysis
└── utils/          # Configuration and utilities

config/             # YAML configuration files
logs/              # Structured output logs
├── desyncs/       # Detailed desync event logs
├── analysis/      # AI analysis prompts and data
├── metrics/       # Metrics collection logs
└── system/        # System operation logs
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Running geth or reth node with IPC enabled
- Prometheus metrics endpoint (optional but recommended)

### Installation

1. **Clone and Setup**:
   ```bash
   git clone <repository-url>
   cd rpc-performance-checker
   pip install -r requirements.txt
   ```

2. **Configure IPC Path**:
   Edit `config/config.yaml` and set the correct IPC socket path:
   ```yaml
   ipc:
     socket_path: "/var/lib/bsc/geth.ipc"  # For BSC geth
     # OR
     socket_path: "/tmp/reth.ipc"          # For Base reth
   ```

3. **Start Monitoring**:
   ```bash
   python main.py
   ```

## ⚙️ Configuration

### Main Configuration (`config/config.yaml`)

```yaml
# Node and network settings
ipc:
  socket_path: "/var/lib/bsc/geth.ipc"
  connection_timeout_seconds: 10

networks:
  bsc:
    chain_id: 56
    consensus_rpc_url: "https://bsc-dataseed.bnbchain.org/"
  base:
    chain_id: 8453
    consensus_rpc_url: "https://mainnet.base.org"

# Monitoring thresholds
monitoring:
  sync_check_interval_seconds: 30
  desync_threshold_blocks: 5
  metrics_collection_interval_seconds: 5
```

### Prometheus Metrics (`config/prometheus_metrics.yaml`)

Defines which metrics to collect and monitor for anomalies.

### Logging Configuration (`config/logging.yaml`)

Controls log levels, formats, and AI optimization settings.

## 🔍 Monitoring Capabilities

### Desync Detection

- **Real-time Monitoring**: Compares local node height with network consensus
- **Configurable Thresholds**: Set custom block lag thresholds
- **Recovery Tracking**: Monitors desync resolution and timing
- **Severity Classification**: Automatic severity assessment (low/medium/high/critical)

### Metrics Collection

- **Prometheus Integration**: Collects node performance metrics
- **Anomaly Detection**: Statistical analysis of metric patterns
- **Historical Storage**: SQLite database for trend analysis
- **Correlation Analysis**: Links metrics with desync events

### AI-Ready Logging

Each desync event generates:

- **Comprehensive Context**: 10-minute metric windows around events
- **Structured Data**: JSON format optimized for AI analysis
- **Analysis Prompts**: Pre-generated prompts for AI investigation
- **Environmental Factors**: System state and network conditions
- **Investigation Hints**: Suggested analysis paths and checkpoints

## 📊 Data Models

### Desync Event Structure

```json
{
  "event_metadata": {
    "event_id": "desync_1703123456",
    "timestamp": 1703123456.789,
    "detection_source": "sync_monitor"
  },
  "desync_details": {
    "local_block_height": 123450,
    "consensus_block_height": 123465,
    "blocks_behind": 15,
    "severity": "medium"
  },
  "metrics_context": {
    "pre_event_metrics": [...],
    "during_event_metrics": [...],
    "post_event_metrics": [...]
  }
}
```

## 🤖 AI Integration

### Analysis Prompt Generation

For each desync event, the system generates comprehensive analysis prompts:

```
BLOCKCHAIN NODE DESYNC ANALYSIS REQUEST

This is a medium desync event requiring thorough analysis. 
The node fell 15 blocks behind the network. Focus your 
analysis on identifying the root cause and prevention strategies.

KEY QUESTIONS TO ADDRESS:
- What was the primary cause of this desynchronization event?
- Were there any warning signs in the metrics before the desync occurred?
- How do the peer connection patterns correlate with the desync timing?

SUGGESTED INVESTIGATION PATHS:
- Analyze historical desync patterns for trends
- Compare with other nodes on the same network
- Review infrastructure monitoring for correlations
```

## 📈 Metrics and Analysis

### Collected Metrics

- **Sync Status**: Block height, sync state, peer count
- **Performance**: CPU, memory, disk I/O patterns  
- **Network**: Peer connectivity, latency patterns
- **Blockchain**: Block processing times, transaction throughput

### Analysis Features

- **Trend Analysis**: Historical pattern identification
- **Correlation Detection**: Metrics-to-events correlation
- **Anomaly Scoring**: Statistical deviation analysis
- **Predictive Hints**: Early warning indicators

## 🔧 Usage Examples

### Basic Monitoring

```bash
# Start with default configuration
python main.py
```

### Custom Configuration

```bash
# Use custom config file
CONFIG_FILE=/path/to/custom/config.yaml python main.py
```

### Development Mode

```bash
# Run with debug logging
LOG_LEVEL=DEBUG python main.py
```

## 📝 Log Files

### Directory Structure

```
logs/
├── desyncs/           # Detailed desync events
│   └── desync_events.jsonl
├── analysis/          # AI analysis data
│   ├── ai_analysis.jsonl
│   └── anomalies.jsonl
├── metrics/           # Metrics collection logs
│   └── collection.log
└── system/            # System operation logs
    └── monitor.log
```

## 🚨 Troubleshooting

### Common Issues

1. **IPC Connection Failed**:
   - Verify IPC socket path in configuration
   - Check node is running and IPC is enabled
   - Verify permissions on socket file

2. **Prometheus Metrics Unavailable**:
   - Confirm metrics endpoint is accessible
   - Check network connectivity
   - Verify Prometheus configuration

3. **Database Errors**:
   - Check disk space availability
   - Verify write permissions in logs directory
   - Review SQLite error messages in logs

### Debug Mode

```bash
LOG_LEVEL=DEBUG python main.py
```

## 📋 System Requirements

- **CPU**: 1+ core (monitoring is lightweight)
- **Memory**: 512MB+ available RAM
- **Storage**: 1GB+ for logs and database
- **Network**: Access to consensus RPC endpoints

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch
3. **Implement** changes with tests
4. **Submit** a pull request

### Code Style

- **Type hints**: Required for all functions
- **Async patterns**: Use async/await consistently
- **Error handling**: Comprehensive exception management
- **Documentation**: Docstrings with examples

## 📄 License

This project is licensed under the MIT License.

---

**Note**: This monitoring system is designed for production use but should be tested thoroughly in your specific environment before deployment.
