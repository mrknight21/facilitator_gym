
.PHONY: dev install seed clean

install:
	pip install -r requirements.txt
	cd frontend && npm install

seed:
	python scripts/seed_db.py

dev:
	@echo "Starting Facilitator Gym Dev Environment..."
	@echo "NOTE: This requires 'honcho' or 'foreman' typically, but we will use a Python script manager or separate tabs."
	@echo "Run these in separate terminals:"
	@echo "  1. LiveKit: lk server --dev"
	@echo "  2. Backend: uvicorn app.main:app --reload"
	@echo "  3. Frontend: cd frontend && npm run dev"

# Optional: if they want a single command, we can try to use a Procfile-like approach if we add a dev script.
# For now, let's keep it simple or use a python script to run all?
# Let's actually make 'make dev' try to run things if possible, but standard 'make' is synchronous.
# A common pattern is to use a Procfile and 'honcho start'.

setup:
	pip install honcho
	echo "web: cd frontend && npm run dev" > Procfile
	echo "api: uvicorn app.main:app --reload" >> Procfile
	# LiveKit usually needs its own setup or binary. assuming 'lk' is in path.
	echo "lk: lk server --dev" >> Procfile

run:
	honcho start
