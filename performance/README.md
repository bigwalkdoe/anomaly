# Anomaly Performance Testing

This directory contains load and performance tests for the Anomaly platform.

## Tools Used

- [locust](https://locust.io/) - Distributed load testing
- [pytest-benchmark](https://pytest-benchmark.readthedocs.io/) - Micro-benchmarks

## Running Load Tests

```bash
# Install locust
pip install locust

# Run load test against local API
locust -f locustfile.py --host http://localhost:8000

# Run headless
locust -f locustfile.py --host http://localhost:8000 --headless -u 10 -r 2 -t 60s
```

## Locustfile

Create `locustfile.py`:

```python
from locust import HttpUser, task, between


class AnomalyUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # Login
        self.client.post(
            "/api/auth/login", json={"email": "test@example.com", "password": "password"}
        )

    @task
    def list_engagements(self):
        self.client.get("/api/engagements")

    @task
    def list_findings(self):
        self.client.get("/api/engagements/1/findings")

    @task
    def dashboard(self):
        self.client.get("/api/dashboard")
```

## Benchmark Tests

Run pytest-benchmark for micro-benchmarks:

```bash
pip install pytest-benchmark
pytest --benchmark-only tests/core/
```
