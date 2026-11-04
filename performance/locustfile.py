from locust import HttpUser, task, between


class AnomalyUser(HttpUser):
    wait_time = between(1, 3)
    token = None

    def on_start(self):
        # Register and login
        self.client.post(
            "/api/auth/register",
            json={
                "email": f"user{self.user_id}@example.com",
                "name": f"User{self.user_id}",
                "password": "password123",
            },
        )
        resp = self.client.post(
            "/api/auth/login",
            json={"email": f"user{self.user_id}@example.com", "password": "password123"},
        )
        if resp.status_code == 200:
            self.token = resp.json().get("access_token")

    @task(3)
    def list_engagements(self):
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        self.client.get("/api/engagements", headers=headers)

    @task(2)
    def dashboard(self):
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        self.client.get("/api/dashboard", headers=headers)

    @task(1)
    def health(self):
        self.client.get("/api/health")

    @task(1)
    def metrics(self):
        self.client.get("/api/metrics")
