# FixOps

FixOps is an experimental incident-detection and automated response toolkit.
It provides detector components, action workers, and optional AI-driven analysis
to help detect issues and run remediation workflows.

Quickstart
---------

Prerequisites
- Python virtual environment (recommended)
- Redis (used by RQ for background workers)
- Project dependencies in `requirement.txt`

Local setup
1. Create and activate a virtual environment:

	 On Windows (PowerShell):

	 ```powershell
	 python -m venv .venv
	 .\.venv\Scripts\Activate.ps1
	 ```

2. Install dependencies:

	 ```bash
	 pip install -r requirement.txt
	 ```

3. Start Redis (example with Docker):

	 ```bash
	 docker run -p 6379:6379 redis
	 ```

Running the app and workers
- Run the API (development):

	```bash
	python -m uvicorn main:app --reload
	```

- Start RQ workers (examples):

	```bash
	rq worker logs --worker-class rq.worker.SimpleWorker
	rq worker analysis --worker-class rq.worker.SimpleWorker
	rq worker logs analysis actions --worker-class rq.worker.SimpleWorker
	```

Project layout (important files)
- `main.py` — application entry / API
- `worker_tasks.py` — task definitions enqueued to workers
- `queue_config.py` — queue names and RQ configuration
- `services/` — service modules (actions, ai, detectors, etc.)
- `state/` — lightweight runtime state

Notes
- This README intentionally avoids changing code. Follow the existing
	module interfaces when extending functionality.
- If you need a developer workflow (tests, linters, CI), tell me and I can
	add concise instructions.

Contributing
- Open an issue for design discussions before large changes.
- Keep changes isolated and add tests where appropriate.

License
- (Add license information here)
