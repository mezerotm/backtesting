# Python virtual environment paths
VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip

# Ensure virtual environment exists
ensure-venv:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv $(VENV); \
	else \
		echo "Virtual environment already exists."; \
	fi

# Show command to activate the virtual environment
activate-venv: ensure-venv
	@echo "To activate the virtual environment, run this command in your terminal:"
	@echo "source $(VENV)/bin/activate"

# Setup virtual environment
setup: activate-venv
	$(PIP) install -r requirements.txt

# Freeze current dependencies to requirements.txt
freeze:
	$(PIP) freeze > requirements.txt

# Test run with NVDA and custom parameters
backtest-nvda: results-dir
	$(PYTHON) backtest_workflow_cli.py --symbol NVDA --strategies sma --force-refresh || \
	(echo "Retrying in 60 seconds..." && sleep 60 && \
	$(PYTHON) backtest_workflow_cli.py --symbol NVDA --strategies sma --force-refresh)

backtest-smci: results-dir
	$(PYTHON) backtest_workflow_cli.py --symbol SMCI --strategies sma

# High-frequency trading with short moving averages (generates many trades)
backtest-active: results-dir
	$(PYTHON) backtest_workflow_cli.py --symbol SMCI --strategies ema --fast-ma 5 --slow-ma 20

# Compare strategies on NVDA
compare-active: results-dir
	$(PYTHON) comparison_workflow_cli.py --symbol SMCI

# Run experimental combined strategy
backtest-experimental: results-dir
	$(PYTHON) backtest_workflow_cli.py --symbol SMCI --strategies buy_hold experimental sma ema

# Compare only buy and hold with experimental
compare-experimental: results-dir
	$(PYTHON) comparison_workflow_cli.py --symbol SMCI --strategies buy_hold experimental

# Development target with error handling
dev: results-dir
	$(PYTHON) backtest_workflow_cli.py --symbol SMCI --strategies sma

financial-analysis: results-dir
	$(PYTHON) financial_workflow_cli.py --symbols COST

# market check with all indicators
market-check: results-dir
	$(PYTHON) market_workflow_cli.py --force-refresh

# Clean up results
clean:
	rm -rf public/results/*

# Create results directory if it doesn't exist
results-dir:
	mkdir -p public/results

test:
	make market-check
	make financial-analysis
	make backtest-nvda
	

# Start report server
server:
	$(PYTHON) server/report_server.py

.PHONY: setup freeze backtest-nvda backtest-smci \
	compare-active clean results-dir server ensure-venv activate-venv backtest-active \
	backtest-experimental compare-experimental dev debug-buy-hold market-check morning-check full-market-check debug-market-check