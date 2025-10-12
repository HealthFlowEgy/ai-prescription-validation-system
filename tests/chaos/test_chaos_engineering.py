"""
Chaos engineering tests to validate system resilience.
Tests system behavior under failure conditions.
"""

import pytest
import requests
import time
from kubernetes import client, config
import random


class ChaosTestBase:
    """Base class for chaos tests."""

    @staticmethod
    def setup_kubernetes():
        """Setup Kubernetes client."""
        config.load_kube_config()
        return client.CoreV1Api(), client.AppsV1Api()

    @staticmethod
    def wait_for_recovery(url: str, timeout: int = 60) -> bool:
        """Wait for service to recover."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{url}/health", timeout=5)
                if response.status_code == 200:
                    return True
            except requests.RequestException:
                pass
            time.sleep(2)
        return False


class TestPodFailureChaos(ChaosTestBase):
    """Test system resilience to pod failures."""

    def test_api_pod_termination(self):
        """
        Test system behavior when API pod is randomly terminated.

        Expected behavior:
        - Request should be routed to healthy pods
        - No data loss
        - Recovery within 30 seconds
        """
        v1, apps_v1 = self.setup_kubernetes()

        # Get API pods
        pods = v1.list_namespaced_pod(
            namespace="healthflow", label_selector="app=healthflow-api"
        )

        if len(pods.items) < 2:
            pytest.skip("Need at least 2 API pods for this test")

        # Select random pod to kill
        pod_to_kill = random.choice(pods.items)
        pod_name = pod_to_kill.metadata.name

        print(f"Killing pod: {pod_name}")

        # Start continuous requests
        api_url = "http://healthflow-api.healthflow.svc.cluster.local"
        errors_during_chaos = []

        def make_requests():
            for _ in range(30):  # 30 seconds of requests
                try:
                    response = requests.get(f"{api_url}/health", timeout=5)
                    if response.status_code != 200:
                        errors_during_chaos.append(response.status_code)
                except requests.RequestException as e:
                    errors_during_chaos.append(str(e))
                time.sleep(1)

        # Kill pod
        v1.delete_namespaced_pod(name=pod_name, namespace="healthflow")

        # Make requests during chaos
        make_requests()

        # Assertions
        assert len(errors_during_chaos) <= 2, "Too many errors during pod failure"
        assert self.wait_for_recovery(api_url, timeout=30), "Service did not recover"

    def test_database_pod_failure(self):
        """
        Test database failover when primary pod fails.

        Expected behavior:
        - Patroni promotes replica to primary
        - Failover completes in <30 seconds
        - No data loss
        - Application reconnects automatically
        """
        v1, apps_v1 = self.setup_kubernetes()

        # Get PostgreSQL pods
        pods = v1.list_namespaced_pod(
            namespace="healthflow", label_selector="app=postgresql"
        )

        # Find primary pod
        primary_pod = None
        for pod in pods.items:
            # Check if pod is primary
            exec_command = [
                "psql",
                "-U",
                "postgres",
                "-c",
                "SELECT pg_is_in_recovery();",
            ]
            try:
                response = client.stream(
                    v1.connect_get_namespaced_pod_exec,
                    pod.metadata.name,
                    "healthflow",
                    command=exec_command,
                    stderr=True,
                    stdin=False,
                    stdout=True,
                    tty=False,
                )
                if "f" in response:  # f = not in recovery = primary
                    primary_pod = pod
                    break
            except Exception:
                continue

        if not primary_pod:
            pytest.skip("Could not identify primary database pod")

        print(f"Killing primary database pod: {primary_pod.metadata.name}")

        # Record start time
        start_time = time.time()

        # Kill primary pod
        v1.delete_namespaced_pod(name=primary_pod.metadata.name, namespace="healthflow")

        # Wait for failover
        time.sleep(5)

        # Verify new primary is elected
        new_primary_found = False
        for _ in range(10):  # Check for 30 seconds
            pods = v1.list_namespaced_pod(
                namespace="healthflow", label_selector="app=postgresql"
            )

            for pod in pods.items:
                if pod.metadata.name == primary_pod.metadata.name:
                    continue

                try:
                    exec_command = [
                        "psql",
                        "-U",
                        "postgres",
                        "-c",
                        "SELECT pg_is_in_recovery();",
                    ]
                    response = client.stream(
                        v1.connect_get_namespaced_pod_exec,
                        pod.metadata.name,
                        "healthflow",
                        command=exec_command,
                        stderr=True,
                        stdin=False,
                        stdout=True,
                        tty=False,
                    )
                    if "f" in response:
                        new_primary_found = True
                        failover_time = time.time() - start_time
                        print(f"New primary found: {pod.metadata.name}")
                        print(f"Failover time: {failover_time:.2f} seconds")
                        break
                except Exception:
                    continue

            if new_primary_found:
                break

            time.sleep(3)

        # Assertions
        assert new_primary_found, "No new primary elected after failover"
        assert failover_time < 30, f"Failover took too long: {failover_time:.2f}s"


class TestResourceExhaustionChaos(ChaosTestBase):
    """Test system under resource constraints."""

    def test_memory_pressure(self):
        """
        Test system behavior under memory pressure.

        Expected behavior:
        - OOM killer terminates pod
        - Kubernetes restarts pod
        - Load balancer routes traffic to healthy pods
        - No user-visible errors
        """
        v1, apps_v1 = self.setup_kubernetes()

        pods = v1.list_namespaced_pod(
            namespace="healthflow", label_selector="app=healthflow-api"
        )

        if len(pods.items) < 2:
            pytest.skip("Need at least 2 pods for this test")

        target_pod = pods.items[0]

        # Execute stress test in pod
        exec_command = [
            "stress-ng",
            "--vm",
            "1",
            "--vm-bytes",
            "90%",
            "--timeout",
            "60s",
        ]

        # This will likely cause OOM kill
        try:
            client.stream(
                v1.connect_get_namespaced_pod_exec,
                target_pod.metadata.name,
                "healthflow",
                command=exec_command,
                stderr=True,
                stdin=False,
                stdout=True,
                tty=False,
            )
        except Exception:
            pass  # Expected to fail

        # Wait for pod restart
        time.sleep(10)

        # Verify pod was restarted
        pod = v1.read_namespaced_pod(
            name=target_pod.metadata.name, namespace="healthflow"
        )

        assert pod.status.restart_count > 0, "Pod was not restarted"
