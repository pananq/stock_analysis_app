# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**股海罗盘** - A Chinese A-share stock data analysis and strategy execution system. Built with Python/Flask, it provides a REST API backend and a web frontend for managing stock data, technical indicators, and automated trading strategies.

## Commands

### Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml  # then edit with DB credentials and API tokens
```

### Running the App
```bash
# Start all services in background (API on :5000, Web on :8000)
python main.py start

# Start in foreground (for development/debugging)
python main.py start --foreground

# Service management
python main.py stop
python main.py status
python main.py restart

# Start individual services
python main.py start --api-only    # API + scheduler only
python main.py start --web-only    # Web frontend only

# Initialize/verify database
python main.py --init-db
```

### Testing
```bash
# Run all tests
python -m tests.run_tests

# Run quick tests (no network calls)
python -m tests.run_tests --quick

# Run a specific module
python -m tests.run_tests --module integration
python -m tests.run_tests --module rate_limiter
python -m tests.run_tests --module datasource
python -m tests.run_tests --module performance
```

### Production (Gunicorn)
```bash
python run_gunicorn.py
# or
gunicorn -c gunicorn_config.py
```

## Architecture

The app consists of two Flask processes (API and Web) launched via `multiprocessing`, plus an APScheduler instance in the API process.

### Dual-Process Design
- **API server** (`app/api/`, port 5000): REST endpoints + APScheduler for automated daily jobs
- **Web server** (`app/web/`, port 8000): Jinja2 web frontend that proxies calls to the API
- `main.py` manages both processes as a daemon with PID file tracking

### Data Layer
The system uses **MySQL** as the primary database (configurable to SQLite). All ORM models are in `app/models/orm_models.py` using SQLAlchemy 2.x. Key tables:
- `stocks` - stock metadata (code, name, industry, market_type)
- `daily_market` - OHLCV daily price data (composite primary key: code + trade_date)
- `strategies` / `strategy_results` - strategy config and execution results
- `job_logs` / `task_execution_details` - scheduled task history

`app/models/database_factory.py` provides the singleton `ORMDatabase` instance. `app/models/orm_db.py` is a compatibility shim for existing code.

### Data Sources
`app/services/datasource.py` defines the `DataSource` ABC with methods:
- `get_stock_list()` → DataFrame
- `get_stock_daily(code, start_date, end_date)` → DataFrame
- `get_trading_dates()` / `is_trading_day()`

Two implementations: `AkshareDataSource` and `TushareDataSource`. Selected via `datasource.type` in `config.yaml`. The factory is in `app/services/datasource_factory.py`.

### Service Layer
- `app/services/stock_service.py` - CRUD for stock metadata
- `app/services/market_data_service.py` - bulk import/update of OHLCV data, wraps data source + DB
- `app/services/strategy_service.py` - strategy CRUD
- `app/services/strategy_executor.py` - runs strategies against historical data using `app/indicators/technical_indicators.py`
- `app/services/auth_service.py` - JWT-based auth (bcrypt passwords)

### Scheduler
`app/scheduler/task_scheduler.py` uses APScheduler with four daily jobs (configured in `config.yaml` under `scheduler.jobs`):
- 18:00 - stock list update
- 18:30 - market data update
- 19:00 - strategy execution
- every 30 min - health check

### Configuration
`config.yaml` (gitignored) is the runtime config. `config.example.yaml` is the template. Loaded via `app/utils/config.py` as a singleton, accessed everywhere with `get_config()`.

Key config sections: `api`, `web`, `database` (mysql/sqlite), `datasource` (tushare token or akshare), `logging`, `scheduler`, `auth`.

### Background Tasks
Long-running operations (full data import) are tracked as background tasks via `app/task_manager.py` with UUID task IDs. Progress can be polled via `GET /api/data/tasks/{task_id}`.

## Extending the System

**New data source**: Subclass `DataSource` in `app/services/datasource.py`, implement the 4 abstract methods, then register in `DataSourceFactory`.

**New technical indicator**: Add method to `app/indicators/technical_indicators.py`.

**New API endpoint**: Add route file under `app/api/routes/`, register in `app/api/app.py`.
