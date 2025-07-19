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

# Modern dependency management: single command for deps
install: ensure-venv
	@echo "[INFO] To add or upgrade packages, edit requirements.in then run: make deps"
	@if ! $(VENV)/bin/pip show pip-tools > /dev/null 2>&1; then \
		echo "Installing pip-tools in the virtual environment..."; \
		$(PIP) install pip-tools; \
	fi
	$(VENV)/bin/pip-compile requirements.in --output-file requirements.txt
	$(PIP) install -r requirements.txt
	@echo "[SUCCESS] All dependencies installed! (requirements.txt is up to date)"

# Quick dependency update (alias for install)
deps: install

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

# NVDA CRWD COIN MSTR NAKA CRWV NBIS
financial-analysis: results-dir
	$(PYTHON) financial_workflow_cli.py --symbols UNH --force-refresh

# market check with all indicators
market-check: results-dir
	$(PYTHON) market_workflow_cli.py --force-refresh

# Clean up results
clean:
	rm -rf public/results/*

# Create results directory if it doesn't exist
results-dir:
	mkdir -p public/results
	

# Start FastAPI server (serves static and API)
server: results-dir
	$(PYTHON) -m server.main

.PHONY: setup backtest-nvda backtest-smci \
	compare-active clean results-dir server ensure-venv activate-venv backtest-active \
	backtest-experimental compare-experimental dev debug-buy-hold market-check morning-check full-market-check debug-market-check install deps