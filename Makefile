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
	$(PYTHON) backtest_strategy.py --symbol NVDA

# Compare strategies on NVDA
compare-nvda: results-dir
	$(PYTHON) run_comparisons.py --symbol NVDA

# Clean up results
clean:
	rm -rf public/results/*

# Create results directory if it doesn't exist
results-dir:
	mkdir -p public/results

# Start dashboard server
server:
	$(PYTHON) -m utils.dashboard_generator

.PHONY: setup freeze backtest-nvda \
	compare-nvda clean results-dir server ensure-venv activate-venv
