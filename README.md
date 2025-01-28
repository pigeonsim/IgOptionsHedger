# IG Trading Options Analytics Platform

A Streamlit application designed to interface with the IG Trading API for options hedging purposes.

## Features

- Real-time options data streaming
- Advanced options analytics including:
  - Implied volatility computations
  - Time decay calculation
  - Delta calculations

## Prerequisites to run locally

- Python 3.11 or higher
- IG Trading API credentials
  - API Key
  - Username
  - Password

## Installation

1. Clone this repository
2. Install dependencies:
```bash
pip install -r uv.lock
```

## Configuration

1. Create a `.streamlit/config.toml` file with the following content:
```toml
[server]
headless = true
address = "0.0.0.0"
port = 5000

[theme]
primaryColor = "#FF4B4B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"
```

## Usage

1. Start the application:
```bash
streamlit run main.py
```

2. Access the web interface at `http://localhost:5000`

3. Log in using your IG Trading credentials

4. Features available after login:
   - View current positions
   - Monitor real-time options analytics
   - Stream options data updates
   - Calculate IV and delta

## Error Handling
All errors are logged to both console and `app.log` file.

## Project Structure

- `main.py`: Main application entry point and Streamlit interface
- `ig_api.py`: IG Trading API client implementation
- `option_calculations.py`: Options mathematics and analytics
- `options_processor.py`: Options data processing and calculations
- `utils.py`: Utility functions
- `epic_mapping.py`: Market instrument mappings

## Disclaimer

This script should be used with caution when handling sensitive information or financial data;
