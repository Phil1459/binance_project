# Binance Project

Realtime crypto trading research framework using Binance WebSocket streams.

The goal is to understand market structure based on raw trade data, derive useful signals, and test my own trading ideas for strategies.

There are some executed Jupyter-Notebooks that provide insights.

This project is experimental and under active development.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a local `.env` file before running the project:

```bash
cp .env.example .env
```

Then fill in the required values, especially:

```env
BINANCE_API_KEY=
BINANCE_API_SECRET=
SYMBOLS=
```
