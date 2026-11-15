# Python service

Install with `pip install -r requirements.txt`; run from this directory with:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

The current decision endpoint always returns WAIT and execution_allowed=false. It is an API contract stub, not a trading signal engine.
