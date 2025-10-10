# tushare-agent-deepseek-gradio

An intelligent stock data analysis agent based on **Tushare** and **DeepSeek**, with an interactive interface built using **Gradio**. Supports natural language queries and strategy-based stock analysis.

---

## 📌 Project Overview

This project provides a smart stock data analysis agent, allowing users to query stock data, trends, and strategy-based analysis using natural language.

---

## ⚙️ Features

- **Natural Language Query Parsing**: Uses DeepSeek to interpret user input and determine which Tushare function to call with what parameters.
- **Stock Data Retrieval**: Fetch historical stock data including moving averages and other technical indicators via Tushare API.
- **Strategy Matching Analysis**: Analyze stock trends and volume based on predefined strategies.
- **Interactive Interface**: Built with Gradio for a user-friendly interface to submit queries and view results in real-time.

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/siyu618/tushare-agent-deepseek-gradio.git
cd tushare-agent-deepseek-gradio
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Tushare/DeepSeek Token
```bash
DEEPSEEK_API_KEY=sk-xxxx
DEEPSEEK_API_URL="https://api.deepseek.com/v1/chat/completions"
TUSHARE_TOKEN=xxxxxx
```

### 4. Run the Application
```bash
python app.py
```

Visit [http://localhost:7860](http://localhost:7860) to interact with the agent via the Gradio interface.

## Project Structure
```graphql
tushare-agent-deepseek-gradio/
├── app.py              # Gradio app entry point
├── agent.py            # Natural language query parsing and decision logic
├── deepseek_client.py  # DeepSeek API client wrapper
├── tushare_tools.py    # Tushare data retrieval and processing
├── utils.py            # Utility functions
├── requirements.txt    # Project dependencies
└── README.md           # Project documentation
```

## 🧪 Usage Examples
* **List all live stocks:**
```bash
get_all_live_stocks()
```

* **Retrieve historical data for a specific stock:**
```bash
get_stock_data(ts_code='600519.SH', start_date='20230101', end_date='20230930')
```

* **Get stock match days based on strategy:**
```bash
get_stock_match_days(ts_code='600519.SH', start_date='20230101', end_date='20230930')
```

## 🤖 Example Queries
```
User: List all listed stocks

System: Calls get_all_live_stocks() and returns a list of all listed stocks.
```
```
User: Get historical data for 600519.SH from Jan 2023 to Sep 2023

System: Calls get_stock_data() and returns the requested stock data.
```

## 🛠 Developer Guide
1. Environment

  Python version: 3.8 or above
  
  Dependencies: Install via pip. Required packages include tushare, gradio, requests, etc.

2. Extending the Agent

  Add new functions: Extend agent.py with new natural language parsing rules, and implement corresponding functionality in tushare_tools.py.
  
  Improve interface: Modify app.py to adjust the Gradio interface layout and interactions.
