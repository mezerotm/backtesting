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
	

# Database management
db-start:
	@echo "Starting PocketBase database server..."
	@if [ ! -f "libs/pocketbase" ]; then \
		echo "Error: PocketBase binary not found at libs/pocketbase"; \
		echo "Please ensure the PocketBase binary is in the libs directory"; \
		exit 1; \
	fi
	@mkdir -p pb_data
	@echo "PocketBase server starting on http://127.0.0.1:8090"
	@echo "Admin UI available at http://127.0.0.1:8090/_/"
	@echo "Press Ctrl+C to stop the server"
	@libs/pocketbase serve --http=127.0.0.1:8090 --dir=pb_data

db-reset:
	@echo "⚠️  WARNING: This will delete all PocketBase data!"
	@read -p "Are you sure? Type 'yes' to continue: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		echo "Removing PocketBase data directory..."; \
		rm -rf pb_data; \
		echo "✅ PocketBase data reset complete"; \
	else \
		echo "Reset cancelled"; \
	fi

db-backup:
	@echo "Creating PocketBase data backup..."
	@if [ -d "pb_data" ]; then \
		backup_name="pb_backup_$$(date +%Y%m%d_%H%M%S)"; \
		cp -r pb_data "$$backup_name"; \
		echo "✅ Backup created: $$backup_name"; \
	else \
		echo "❌ No PocketBase data directory found"; \
	fi

db-restore:
	@echo "Available backups:"
	@ls -d pb_backup_* 2>/dev/null || echo "No backups found"
	@if [ -d "pb_data" ]; then \
		echo "⚠️  Current data will be overwritten!"; \
		read -p "Enter backup directory name: " backup_dir; \
		if [ -d "$$backup_dir" ]; then \
			rm -rf pb_data; \
			cp -r "$$backup_dir" pb_data; \
			echo "✅ Data restored from $$backup_dir"; \
		else \
			echo "❌ Backup directory not found: $$backup_dir"; \
		fi; \
	else \
		echo "❌ No current PocketBase data directory found"; \
	fi

db-init:
	@echo "Initializing PocketBase database..."
	@echo "Note: This must be run from the project root directory"
	@echo "Current directory: $(PWD)"
	@$(PYTHON) utils/db_init.py

# Syntax checking and auto-fixing with flake8 and autopep8
syntax-check:
	@echo "🔧 Auto-fixing formatting issues with autopep8..."
	@$(PYTHON) -m autopep8 --in-place --recursive --aggressive --aggressive server/ utils/ workflows/ strategies/

# Frontend development server
dev-frontend:
	@echo "Starting Vite development server..."
	@echo "Frontend will be available at http://localhost:3001"
	@echo "API proxy configured to http://localhost:8000"
	@echo "Press Ctrl+C to stop the server"
	npm run dev

# Build frontend for production
build-frontend:
	@echo "Building frontend for production..."
	npm run build
	@echo "Frontend built successfully!"

# Start FastAPI server (serves static and API)
server: results-dir syntax-check build-frontend
	@echo "Starting production server..."
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:8000"
	@echo "PocketBase: http://127.0.0.1:8090/_/ (run 'make db-start' in another terminal)"
	@echo "Opening API page in browser..."
	@sleep 2 && xdg-open http://localhost:8000 || open http://localhost:8000 || start http://localhost:8000 || echo "Please manually open: http://localhost:8000"
	$(PYTHON) -m server.main

# Development server with hot reload
dev-server: results-dir syntax-check
	@echo "Starting development server with hot reload..."
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:3001 (run 'make dev-frontend' in another terminal)"
	@echo "PocketBase: http://127.0.0.1:8090/_/ (run 'make db-start' in another terminal)"
	@echo "Hot reload enabled - watching server/ and utils/ directories"
	@echo "Server will restart when Python files in these directories change"
	@echo "Opening API page in browser..."
	@sleep 2 && xdg-open http://localhost:8000 || open http://localhost:8000 || start http://localhost:8000 || echo "Please manually open: http://localhost:8000"
	$(PYTHON) -m uvicorn server.api.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir server --reload-dir utils --log-level info





.PHONY: setup backtest-nvda backtest-smci \
	compare-active clean results-dir server ensure-venv activate-venv backtest-active \
	backtest-experimental compare-experimental dev debug-buy-hold market-check morning-check full-market-check debug-market-check install deps \
	db-start db-reset db-backup db-restore db-init dev-frontend build-frontend dev-server