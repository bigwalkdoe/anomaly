from locust import HttpUser, between, task


class AnomalyUser(HttpUser):
    wait_time = between(1, 3)
    token = None

    def on_start(self):
        """Authenticate user at the start of each test."""
        email = f"user{self.user_id}@example.com"
        password = "password123"
        
        # Try to register (may fail if user exists)
        self.client.post(
            "/api/auth/register",
            json={
                "email": email,
                "name": f"User{self.user_id}",
                "password": password,
            },
        )
        
        # Login
        resp = self.client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("mfa_required"):
                # MFA enabled - skip for load testing
                self.token = None
            else:
                self.token = data.get("access_token")

    def _get_headers(self):
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    @task(3)
    def list_engagements(self):
        self.client.get("/api/engagements", headers=self._get_headers())

    @task(3)
    def list_findings(self):
        self.client.get("/api/search?q=", headers=self._get_headers())

    @task(2)
    def list_runs(self):
        self.client.get("/api/runs?limit=100", headers=self._get_headers())

    @task(2)
    def dashboard(self):
        self.client.get("/api/dashboard", headers=self._get_headers())

    @task(1)
    def health(self):
        self.client.get("/api/health")

    @task(1)
    def metrics(self):
        self.client.get("/api/metrics")

    @task(1)
    def list_notifications(self):
        self.client.get("/api/notifications", headers=self._get_headers())
