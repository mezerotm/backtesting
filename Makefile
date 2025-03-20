# Python virtual environment paths
VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip

# Setup virtual environment
setup:
	python -m venv $(VENV)
	$(PIP) install -r requirements.txt

# Freeze current dependencies to requirements.txt
freeze:
	$(PIP) freeze > requirements.txt

# Basic run with AAPL (default settings)
backtest-aapl:
	$(PYTHON) backtest_strategy.py --ticker AAPL

# Test run with NVDA and custom parameters
backtest-nvda:
	$(PYTHON) backtest_strategy.py --ticker NVDA

test-backtest: backtest-aapl backtest-nvda

# Strategy Comparison Commands
# ----------------------------

# Compare strategies on AAPL
compare-aapl:
	$(PYTHON) run_comparisons.py --symbol AAPL

# Compare strategies on NVDA
compare-nvda:
	$(PYTHON) run_comparisons.py --symbol NVDA

# Run a comprehensive test across multiple symbols
test-comparison: results-dir compare-nvda compare-aapl

# Report Generation
# ----------------

# Generate HTML report from results
generate-report: 
	$(PYTHON) utils/strategy_comparison_report.py --dir results

# Complete testing and reporting workflow
test-and-report: test-comparison generate-report
	@echo "Testing and reporting complete."

# Clean up results
clean:
	rm -rf results/*

# Create results directory if it doesn't exist
results-dir:
	mkdir -p results

.PHONY: setup freeze test-backtest \
	compare-aapl compare-nvda test-comparison \
	results-dir generate-report test-and-report clean
