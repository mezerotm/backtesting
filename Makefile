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

# Basic run with AAPL (default settings)
backtest-aapl: results-dir
	$(PYTHON) backtest_strategy.py --ticker AAPL

# Test run with NVDA and custom parameters
backtest-nvda: results-dir
	$(PYTHON) backtest_strategy.py --ticker NVDA

test-backtest: results-dir backtest-aapl backtest-nvda dashboard

# Strategy Comparison Commands
# ----------------------------

# Compare strategies on AAPL
compare-aapl: results-dir
	$(PYTHON) run_comparisons.py --symbol AAPL

# Compare strategies on NVDA
compare-nvda: results-dir
	$(PYTHON) run_comparisons.py --symbol NVDA

# Run a comprehensive test across multiple symbols
test-comparisons: results-dir compare-nvda compare-aapl dashboard

# Clean up results
clean:
	rm -rf results/*

# Create results directory if it doesn't exist
results-dir:
	mkdir -p results

# Start dashboard server
server:
	$(PYTHON) -m utils.dashboard_generator

.PHONY: setup freeze test-backtest \
	compare-aapl compare-nvda test-comparison \
	results-dir generate-report test-and-report clean ensure-venv activate-venv
