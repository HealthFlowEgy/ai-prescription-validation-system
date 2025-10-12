"""
Performance Optimization and Load Testing System
Monitors performance, identifies bottlenecks, and conducts load testing
"""

import time
import asyncio
import aiohttp
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import statistics
import logging
import psutil
import concurrent.futures

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance measurement results"""

    operation: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    success: bool
    error: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class LoadTestResults:
    """Load test results"""

    test_name: str
    duration_seconds: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    requests_per_second: float
    avg_response_time_ms: float
    median_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    error_rate: float
    errors: Dict[str, int] = field(default_factory=dict)


class PerformanceMonitor:
    """
    Monitors application performance in real-time
    """

    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.metric_buffer_size = 10000

    def measure(self, operation: str):
        """
        Decorator to measure function performance

        Args:
            operation: Operation name
        """

        def decorator(func: Callable):
            def wrapper(*args, **kwargs):
                start_time = datetime.utcnow()
                start_ms = time.time() * 1000
                error = None
                success = True

                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    error = str(e)
                    raise
                finally:
                    end_time = datetime.utcnow()
                    end_ms = time.time() * 1000
                    duration_ms = end_ms - start_ms

                    metric = PerformanceMetrics(
                        operation=operation,
                        start_time=start_time,
                        end_time=end_time,
                        duration_ms=duration_ms,
                        success=success,
                        error=error,
                    )

                    self.record_metric(metric)

            return wrapper

        return decorator

    def record_metric(self, metric: PerformanceMetrics):
        """Record performance metric"""
        self.metrics.append(metric)

        # Trim buffer if too large
        if len(self.metrics) > self.metric_buffer_size:
            self.metrics = self.metrics[-self.metric_buffer_size :]

    def get_operation_stats(
        self, operation: str, time_window_minutes: int = 60
    ) -> Dict:
        """
        Get statistics for an operation

        Args:
            operation: Operation name
            time_window_minutes: Time window for stats

        Returns:
            Statistics dictionary
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)

        relevant_metrics = [
            m
            for m in self.metrics
            if m.operation == operation and m.start_time >= cutoff_time
        ]

        if not relevant_metrics:
            return {"error": "No data available"}

        durations = [m.duration_ms for m in relevant_metrics]
        successful = [m for m in relevant_metrics if m.success]
        failed = [m for m in relevant_metrics if not m.success]

        sorted_durations = sorted(durations)
        n = len(sorted_durations)

        return {
            "operation": operation,
            "time_window_minutes": time_window_minutes,
            "total_calls": len(relevant_metrics),
            "successful_calls": len(successful),
            "failed_calls": len(failed),
            "success_rate": len(successful) / len(relevant_metrics),
            "response_time_ms": {
                "mean": statistics.mean(durations),
                "median": sorted_durations[n // 2],
                "p95": sorted_durations[int(n * 0.95)] if n > 0 else 0,
                "p99": sorted_durations[int(n * 0.99)] if n > 0 else 0,
                "min": min(durations),
                "max": max(durations),
                "std_dev": statistics.stdev(durations) if len(durations) > 1 else 0,
            },
        }

    def identify_bottlenecks(self, threshold_ms: float = 1000) -> List[Dict]:
        """
        Identify performance bottlenecks

        Args:
            threshold_ms: Threshold for slow operations

        Returns:
            List of bottlenecks
        """
        # Group by operation
        by_operation = defaultdict(list)
        for metric in self.metrics:
            by_operation[metric.operation].append(metric.duration_ms)

        bottlenecks = []

        for operation, durations in by_operation.items():
            if not durations:
                continue

            p95 = sorted(durations)[int(len(durations) * 0.95)] if durations else 0

            if p95 > threshold_ms:
                bottlenecks.append(
                    {
                        "operation": operation,
                        "p95_ms": p95,
                        "mean_ms": statistics.mean(durations),
                        "max_ms": max(durations),
                        "sample_size": len(durations),
                        "severity": "high" if p95 > threshold_ms * 2 else "medium",
                    }
                )

        # Sort by severity
        bottlenecks.sort(key=lambda x: x["p95_ms"], reverse=True)

        return bottlenecks


class LoadTester:
    """
    Conducts load testing on API endpoints
    """

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.results: List[PerformanceMetrics] = []

    async def _make_request(
        self,
        session: aiohttp.ClientSession,
        method: str,
        endpoint: str,
        headers: Optional[Dict] = None,
        data: Optional[Dict] = None,
    ) -> PerformanceMetrics:
        """Make single HTTP request"""
        url = f"{self.base_url}{endpoint}"
        start_time = datetime.utcnow()
        start_ms = time.time() * 1000

        try:
            async with session.request(
                method,
                url,
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                await response.text()

                end_ms = time.time() * 1000
                duration_ms = end_ms - start_ms

                return PerformanceMetrics(
                    operation=f"{method} {endpoint}",
                    start_time=start_time,
                    end_time=datetime.utcnow(),
                    duration_ms=duration_ms,
                    success=response.status < 400,
                    error=None if response.status < 400 else f"HTTP {response.status}",
                )

        except Exception as e:
            end_ms = time.time() * 1000
            duration_ms = end_ms - start_ms

            return PerformanceMetrics(
                operation=f"{method} {endpoint}",
                start_time=start_time,
                end_time=datetime.utcnow(),
                duration_ms=duration_ms,
                success=False,
                error=str(e),
            )

    async def run_load_test(
        self,
        method: str,
        endpoint: str,
        concurrent_users: int,
        duration_seconds: int,
        headers: Optional[Dict] = None,
        data: Optional[Dict] = None,
    ) -> LoadTestResults:
        """
        Run load test

        Args:
            method: HTTP method
            endpoint: API endpoint
            concurrent_users: Number of concurrent users
            duration_seconds: Test duration
            headers: Request headers
            data: Request data

        Returns:
            Load test results
        """
        test_start = time.time()
        self.results = []

        async with aiohttp.ClientSession() as session:
            tasks = []

            while (time.time() - test_start) < duration_seconds:
                # Create batch of concurrent requests
                batch = [
                    self._make_request(session, method, endpoint, headers, data)
                    for _ in range(concurrent_users)
                ]

                # Execute batch
                batch_results = await asyncio.gather(*batch)
                self.results.extend(batch_results)

                # Small delay to avoid overwhelming
                await asyncio.sleep(0.1)

        return self._calculate_results(f"{method} {endpoint}", time.time() - test_start)

    def _calculate_results(
        self, test_name: str, duration_seconds: float
    ) -> LoadTestResults:
        """Calculate load test results"""
        total = len(self.results)
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]

        durations = [r.duration_ms for r in self.results]
        sorted_durations = sorted(durations)
        n = len(sorted_durations)

        # Count error types
        errors = defaultdict(int)
        for r in failed:
            errors[r.error or "unknown"] += 1

        return LoadTestResults(
            test_name=test_name,
            duration_seconds=duration_seconds,
            total_requests=total,
            successful_requests=len(successful),
            failed_requests=len(failed),
            requests_per_second=total / duration_seconds if duration_seconds > 0 else 0,
            avg_response_time_ms=statistics.mean(durations) if durations else 0,
            median_response_time_ms=sorted_durations[n // 2] if n > 0 else 0,
            p95_response_time_ms=sorted_durations[int(n * 0.95)] if n > 0 else 0,
            p99_response_time_ms=sorted_durations[int(n * 0.99)] if n > 0 else 0,
            min_response_time_ms=min(durations) if durations else 0,
            max_response_time_ms=max(durations) if durations else 0,
            error_rate=len(failed) / total if total > 0 else 0,
            errors=dict(errors),
        )

    def print_results(self, results: LoadTestResults):
        """Print load test results"""
        print(f"\n{'='*60}")
        print(f"Load Test Results: {results.test_name}")
        print(f"{'='*60}")
        print(f"Duration: {results.duration_seconds:.1f}s")
        print(f"Total Requests: {results.total_requests}")
        print(f"Successful: {results.successful_requests}")
        print(f"Failed: {results.failed_requests}")
        print(f"Requests/sec: {results.requests_per_second:.1f}")
        print(f"Error Rate: {results.error_rate:.1%}")
        print(f"\nResponse Times (ms):")
        print(f"  Average: {results.avg_response_time_ms:.1f}")
        print(f"  Median: {results.median_response_time_ms:.1f}")
        print(f"  P95: {results.p95_response_time_ms:.1f}")
        print(f"  P99: {results.p99_response_time_ms:.1f}")
        print(f"  Min: {results.min_response_time_ms:.1f}")
        print(f"  Max: {results.max_response_time_ms:.1f}")

        if results.errors:
            print(f"\nErrors:")
            for error, count in results.errors.items():
                print(f"  {error}: {count}")

        print(f"{'='*60}\n")


class ResourceMonitor:
    """
    Monitors system resource usage
    """

    def get_current_usage(self) -> Dict:
        """Get current resource usage"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "cpu": {"percent": cpu_percent, "count": psutil.cpu_count()},
            "memory": {
                "total_gb": memory.total / (1024**3),
                "used_gb": memory.used / (1024**3),
                "available_gb": memory.available / (1024**3),
                "percent": memory.percent,
            },
            "disk": {
                "total_gb": disk.total / (1024**3),
                "used_gb": disk.used / (1024**3),
                "free_gb": disk.free / (1024**3),
                "percent": disk.percent,
            },
        }

    def check_resource_limits(self) -> Dict:
        """Check if resources are approaching limits"""
        usage = self.get_current_usage()
        warnings = []

        # CPU check
        if usage["cpu"]["percent"] > 80:
            warnings.append(
                {
                    "resource": "CPU",
                    "current": usage["cpu"]["percent"],
                    "threshold": 80,
                    "severity": "high" if usage["cpu"]["percent"] > 90 else "medium",
                }
            )

        # Memory check
        if usage["memory"]["percent"] > 80:
            warnings.append(
                {
                    "resource": "Memory",
                    "current": usage["memory"]["percent"],
                    "threshold": 80,
                    "severity": "high" if usage["memory"]["percent"] > 90 else "medium",
                }
            )

        # Disk check
        if usage["disk"]["percent"] > 80:
            warnings.append(
                {
                    "resource": "Disk",
                    "current": usage["disk"]["percent"],
                    "threshold": 80,
                    "severity": "high" if usage["disk"]["percent"] > 90 else "medium",
                }
            )

        return {
            "status": "warning" if warnings else "ok",
            "usage": usage,
            "warnings": warnings,
        }


class CacheOptimizer:
    """
    Optimizes caching strategies
    """

    def __init__(self):
        self.cache_hits = defaultdict(int)
        self.cache_misses = defaultdict(int)

    def record_cache_access(self, key: str, hit: bool):
        """Record cache access"""
        if hit:
            self.cache_hits[key] += 1
        else:
            self.cache_misses[key] += 1

    def get_cache_statistics(self) -> Dict:
        """Get cache statistics"""
        all_keys = set(self.cache_hits.keys()) | set(self.cache_misses.keys())

        stats = []
        for key in all_keys:
            hits = self.cache_hits[key]
            misses = self.cache_misses[key]
            total = hits + misses

            stats.append(
                {
                    "key": key,
                    "hits": hits,
                    "misses": misses,
                    "total_accesses": total,
                    "hit_rate": hits / total if total > 0 else 0,
                }
            )

        # Sort by total accesses
        stats.sort(key=lambda x: x["total_accesses"], reverse=True)

        return {
            "total_keys": len(all_keys),
            "overall_hit_rate": (
                sum(self.cache_hits.values())
                / (sum(self.cache_hits.values()) + sum(self.cache_misses.values()))
                if (sum(self.cache_hits.values()) + sum(self.cache_misses.values())) > 0
                else 0
            ),
            "key_statistics": stats[:20],  # Top 20
        }

    def recommend_optimizations(self) -> List[Dict]:
        """Recommend cache optimizations"""
        stats = self.get_cache_statistics()
        recommendations = []

        for key_stat in stats["key_statistics"]:
            # Low hit rate - consider removing from cache
            if key_stat["hit_rate"] < 0.3 and key_stat["total_accesses"] > 100:
                recommendations.append(
                    {
                        "key": key_stat["key"],
                        "recommendation": "Remove from cache",
                        "reason": f"Low hit rate ({key_stat['hit_rate']:.1%})",
                        "priority": "medium",
                    }
                )

            # High access, high hit rate - increase TTL
            elif key_stat["hit_rate"] > 0.8 and key_stat["total_accesses"] > 1000:
                recommendations.append(
                    {
                        "key": key_stat["key"],
                        "recommendation": "Increase TTL",
                        "reason": f"High hit rate ({key_stat['hit_rate']:.1%}) and access frequency",
                        "priority": "high",
                    }
                )

        return recommendations


# Example usage
if __name__ == "__main__":
    # Performance monitoring
    monitor = PerformanceMonitor()

    @monitor.measure("prescription_processing")
    def process_prescription():
        time.sleep(0.1)  # Simulate work
        return "processed"

    # Simulate some operations
    for _ in range(100):
        process_prescription()

    # Get statistics
    stats = monitor.get_operation_stats("prescription_processing")
    print("Prescription Processing Stats:")
    print(f"  Total calls: {stats['total_calls']}")
    print(f"  Mean time: {stats['response_time_ms']['mean']:.1f}ms")
    print(f"  P95: {stats['response_time_ms']['p95']:.1f}ms")

    # Identify bottlenecks
    bottlenecks = monitor.identify_bottlenecks(threshold_ms=50)
    if bottlenecks:
        print("\nBottlenecks detected:")
        for b in bottlenecks:
            print(f"  {b['operation']}: P95={b['p95_ms']:.1f}ms ({b['severity']})")

    # Resource monitoring
    resource_monitor = ResourceMonitor()
    usage = resource_monitor.get_current_usage()
    print(f"\nCurrent Resource Usage:")
    print(f"  CPU: {usage['cpu']['percent']}%")
    print(f"  Memory: {usage['memory']['percent']}%")
    print(f"  Disk: {usage['disk']['percent']}%")

    # Check limits
    limit_check = resource_monitor.check_resource_limits()
    if limit_check["warnings"]:
        print("\nResource Warnings:")
        for warning in limit_check["warnings"]:
            print(
                f"  {warning['resource']}: {warning['current']}% ({warning['severity']})"
            )

    # Load testing
    async def run_load_test():
        tester = LoadTester("http://localhost:5000")

        results = await tester.run_load_test(
            method="GET", endpoint="/health", concurrent_users=10, duration_seconds=10
        )

        tester.print_results(results)

    # Run load test
    # asyncio.run(run_load_test())
