"""
Load Testing Suite for HealthFlow AI Prescription Validation System.
Uses Locust for distributed load testing.

Target: 5,000 concurrent users with P95 latency < 300ms
"""

from locust import HttpUser, task, between, events
import random
import json
import time
from datetime import datetime

# Test data
SAMPLE_PRESCRIPTIONS = [
    {
        "patient_id": f"patient_{i}",
        "medication": random.choice(["Metformin", "Lisinopril", "Atorvastatin", "Amlodipine"]),
        "dosage": random.choice(["10mg", "20mg", "40mg", "80mg"]),
        "frequency": random.choice(["once daily", "twice daily", "three times daily"])
    }
    for i in range(100)
]

SAMPLE_USERS = [
    {
        "email": f"doctor{i}@healthflow.com",
        "password": "TestPassword123!",
        "role": "doctor"
    }
    for i in range(50)
]


class PrescriptionValidationUser(HttpUser):
    """
    Simulates a user interacting with the prescription validation system.
    
    User behavior:
    - Login
    - Submit prescriptions for validation
    - Check validation results
    - Logout
    """
    
    # Wait time between tasks (1-3 seconds)
    wait_time = between(1, 3)
    
    # Authentication token
    access_token = None
    refresh_token = None
    
    def on_start(self):
        """Called when a user starts. Performs login."""
        self.login()
    
    def on_stop(self):
        """Called when a user stops. Performs logout."""
        if self.access_token:
            self.logout()
    
    def login(self):
        """Authenticate user and get JWT tokens."""
        user = random.choice(SAMPLE_USERS)
        
        with self.client.post(
            "/api/auth/login",
            json={
                "email": user["email"],
                "password": user["password"]
            },
            catch_response=True,
            name="Login"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                response.success()
            else:
                response.failure(f"Login failed: {response.status_code}")
    
    def logout(self):
        """Logout and revoke tokens."""
        if not self.access_token:
            return
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        with self.client.post(
            "/api/auth/logout",
            json={"refresh_token": self.refresh_token},
            headers=headers,
            catch_response=True,
            name="Logout"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Logout failed: {response.status_code}")
    
    @task(10)
    def submit_prescription(self):
        """Submit a prescription for validation (most common task)."""
        if not self.access_token:
            self.login()
            return
        
        prescription = random.choice(SAMPLE_PRESCRIPTIONS)
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        with self.client.post(
            "/api/prescriptions",
            json=prescription,
            headers=headers,
            catch_response=True,
            name="Submit Prescription"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 401:
                # Token expired, refresh and retry
                self.refresh_access_token()
                response.failure("Token expired, refreshing")
            else:
                response.failure(f"Submit failed: {response.status_code}")
    
    @task(5)
    def get_prescriptions(self):
        """Get list of prescriptions."""
        if not self.access_token:
            self.login()
            return
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        with self.client.get(
            "/api/prescriptions",
            headers=headers,
            catch_response=True,
            name="Get Prescriptions"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                self.refresh_access_token()
                response.failure("Token expired, refreshing")
            else:
                response.failure(f"Get failed: {response.status_code}")
    
    @task(3)
    def validate_prescription(self):
        """Validate a specific prescription."""
        if not self.access_token:
            self.login()
            return
        
        # Simulate validation of a random prescription ID
        prescription_id = random.randint(1, 1000)
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        with self.client.post(
            f"/api/prescriptions/{prescription_id}/validate",
            headers=headers,
            catch_response=True,
            name="Validate Prescription"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 401:
                self.refresh_access_token()
                response.failure("Token expired, refreshing")
            elif response.status_code == 404:
                response.success()  # Expected for non-existent IDs
            else:
                response.failure(f"Validate failed: {response.status_code}")
    
    @task(2)
    def get_user_profile(self):
        """Get current user profile."""
        if not self.access_token:
            self.login()
            return
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        with self.client.get(
            "/api/auth/me",
            headers=headers,
            catch_response=True,
            name="Get User Profile"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                self.refresh_access_token()
                response.failure("Token expired, refreshing")
            else:
                response.failure(f"Profile failed: {response.status_code}")
    
    @task(1)
    def refresh_access_token(self):
        """Refresh access token using refresh token."""
        if not self.refresh_token:
            self.login()
            return
        
        with self.client.post(
            "/api/auth/refresh",
            json={"refresh_token": self.refresh_token},
            catch_response=True,
            name="Refresh Token"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                response.success()
            else:
                # Refresh failed, re-login
                self.login()
                response.failure(f"Refresh failed: {response.status_code}")


class AdminUser(HttpUser):
    """
    Simulates an admin user performing administrative tasks.
    Lower frequency but more complex operations.
    """
    
    wait_time = between(5, 10)
    access_token = None
    
    def on_start(self):
        """Login as admin."""
        with self.client.post(
            "/api/auth/login",
            json={
                "email": "admin@healthflow.com",
                "password": "AdminPassword123!"
            },
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
    
    @task(5)
    def view_metrics(self):
        """View system metrics."""
        if not self.access_token:
            return
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        with self.client.get(
            "/api/admin/metrics",
            headers=headers,
            catch_response=True,
            name="Admin: View Metrics"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Metrics failed: {response.status_code}")
    
    @task(3)
    def view_audit_logs(self):
        """View audit logs."""
        if not self.access_token:
            return
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        with self.client.get(
            "/api/admin/audit-logs",
            headers=headers,
            catch_response=True,
            name="Admin: View Audit Logs"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Audit logs failed: {response.status_code}")
    
    @task(2)
    def get_retention_summary(self):
        """Get data retention summary."""
        if not self.access_token:
            return
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        with self.client.get(
            "/api/retention/summary",
            headers=headers,
            catch_response=True,
            name="Admin: Retention Summary"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Retention summary failed: {response.status_code}")


# Event listeners for custom metrics
@events.init_command_line_parser.add_listener
def _(parser):
    """Add custom command-line arguments."""
    parser.add_argument("--target-users", type=int, default=5000,
                       help="Target number of concurrent users")
    parser.add_argument("--target-p95", type=int, default=300,
                       help="Target P95 latency in milliseconds")


@events.test_start.add_listener
def _(environment, **kwargs):
    """Called when test starts."""
    print(f"\n{'='*60}")
    print(f"Load Test Started: {datetime.now().isoformat()}")
    print(f"Target: {environment.parsed_options.target_users} concurrent users")
    print(f"Target P95 Latency: {environment.parsed_options.target_p95}ms")
    print(f"{'='*60}\n")


@events.test_stop.add_listener
def _(environment, **kwargs):
    """Called when test stops. Check if targets were met."""
    print(f"\n{'='*60}")
    print(f"Load Test Completed: {datetime.now().isoformat()}")
    
    # Get statistics
    stats = environment.stats
    
    # Check P95 latency
    total_stats = stats.total
    p95_latency = total_stats.get_response_time_percentile(0.95)
    target_p95 = environment.parsed_options.target_p95
    
    print(f"\nResults:")
    print(f"  Total Requests: {total_stats.num_requests}")
    print(f"  Failed Requests: {total_stats.num_failures}")
    print(f"  Failure Rate: {total_stats.fail_ratio * 100:.2f}%")
    print(f"  Average Response Time: {total_stats.avg_response_time:.2f}ms")
    print(f"  P95 Response Time: {p95_latency:.2f}ms")
    print(f"  Target P95: {target_p95}ms")
    
    # Determine pass/fail
    if p95_latency <= target_p95:
        print(f"\n✅ PASS: P95 latency ({p95_latency:.2f}ms) is under target ({target_p95}ms)")
    else:
        print(f"\n❌ FAIL: P95 latency ({p95_latency:.2f}ms) exceeds target ({target_p95}ms)")
    
    print(f"{'='*60}\n")


# Test scenarios
"""
Run different test scenarios:

1. Baseline Test (100 users):
   locust -f locustfile.py --users 100 --spawn-rate 10 --run-time 5m --host https://api.healthflow.com

2. Target Load Test (5000 users):
   locust -f locustfile.py --users 5000 --spawn-rate 100 --run-time 30m --host https://api.healthflow.com

3. Stress Test (10000 users):
   locust -f locustfile.py --users 10000 --spawn-rate 200 --run-time 15m --host https://api.healthflow.com

4. Spike Test (rapid ramp-up):
   locust -f locustfile.py --users 5000 --spawn-rate 500 --run-time 10m --host https://api.healthflow.com

5. Endurance Test (sustained load):
   locust -f locustfile.py --users 5000 --spawn-rate 50 --run-time 2h --host https://api.healthflow.com
"""

