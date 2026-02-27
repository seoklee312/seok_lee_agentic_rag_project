"""Time-series metrics tracking service."""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict, deque
import threading
import time


class MetricsService:
    """Thread-safe time-series metrics collector with caching."""
    
    def __init__(self, max_history: int = 1000, cache_ttl_seconds: int = 10):
        self.max_history = max_history
        self.cache_ttl_seconds = cache_ttl_seconds
        self._lock = threading.Lock()
        
        # Cache for aggregated metrics
        self._metrics_cache: Dict[int, Dict] = {}  # {hours: {data, timestamp}}
        
        # Time-series data
        self._queries = deque(maxlen=max_history)
        self._response_times = deque(maxlen=max_history)
        self._web_searches = deque(maxlen=max_history)
        self._errors = deque(maxlen=max_history)
        self._feedback_positive = deque(maxlen=max_history)
        self._feedback_negative = deque(maxlen=max_history)
        
        # Step-by-step latency tracking
        self._step_latencies = defaultdict(lambda: deque(maxlen=max_history))
        
        # Counters
        self._total_queries = 0
        self._total_web_searches = 0
        self._total_errors = 0
        self._total_feedback_positive = 0
        self._total_feedback_negative = 0
    
    def record_query(self, response_time_ms: float, web_search_used: bool, error: bool = False, 
                     step_timings: Dict[str, float] = None):
        """Record a query execution with step timings."""
        if response_time_ms < 0:
            import logging
            logging.warning(f"Invalid response time: {response_time_ms}ms, skipping record")
            return
        
        try:
            with self._lock:
                timestamp = datetime.utcnow().isoformat()
                
                self._queries.append((timestamp, 1))
                self._response_times.append((timestamp, response_time_ms))
                self._total_queries += 1
                
                if web_search_used:
                    self._web_searches.append((timestamp, 1))
                    self._total_web_searches += 1
                
                if error:
                    self._errors.append((timestamp, 1))
                    self._total_errors += 1
                
                # Record step timings
                if step_timings:
                    for step, latency in step_timings.items():
                        if latency >= 0:  # Validate latency
                            self._step_latencies[step].append((timestamp, latency))
        except Exception as e:
            import logging
            logging.error(f"[MetricsService] Failed to record query: {e}", exc_info=True)
    
    def record_feedback(self, is_positive: bool):
        """Record user feedback."""
        try:
            with self._lock:
                timestamp = datetime.utcnow().isoformat()
                
                if is_positive:
                    self._feedback_positive.append((timestamp, 1))
                    self._total_feedback_positive += 1
                else:
                    self._feedback_negative.append((timestamp, 1))
                    self._total_feedback_negative += 1
        except Exception as e:
            import logging
            logging.error(f"[MetricsService] Failed to record feedback: {e}", exc_info=True)
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile from list of values."""
        if not values:
            return 0
        sorted_vals = sorted(values)
        idx = int(len(sorted_vals) * percentile / 100)
        return sorted_vals[min(idx, len(sorted_vals) - 1)]
    
    def _filter_by_time_window(self, data: deque, hours: int = 1) -> List:
        """Filter data to last N hours with early exit optimization."""
        if not data:
            return []
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        result = []
        
        # Iterate from newest (right) to oldest (left) for early exit
        for timestamp, value in reversed(data):
            try:
                dt = datetime.fromisoformat(timestamp)
                if dt < cutoff:
                    break  # Early exit - no need to check older entries
                result.append((timestamp, value))
            except (ValueError, TypeError):
                continue  # Skip invalid timestamps
        
        return list(reversed(result))
    
    def _get_cached_metrics(self, time_window_hours: int) -> Optional[Dict]:
        """Get cached metrics if still valid."""
        if time_window_hours in self._metrics_cache:
            cached = self._metrics_cache[time_window_hours]
            age = time.time() - cached['timestamp']
            if age < self.cache_ttl_seconds:
                return cached['data']
        return None
    
    def _set_cached_metrics(self, time_window_hours: int, data: Dict):
        """Cache metrics with timestamp."""
        self._metrics_cache[time_window_hours] = {
            'data': data,
            'timestamp': time.time()
        }
    
    def get_metrics(self, time_window_hours: int = 1) -> Dict:
        """Get all metrics with time-series data filtered by time window (cached)."""
        # Check cache first
        cached = self._get_cached_metrics(time_window_hours)
        if cached:
            return cached
        
        with self._lock:
            # Filter data by time window
            filtered_queries = self._filter_by_time_window(self._queries, time_window_hours)
            filtered_response_times = self._filter_by_time_window(self._response_times, time_window_hours)
            filtered_web_searches = self._filter_by_time_window(self._web_searches, time_window_hours)
            filtered_errors = self._filter_by_time_window(self._errors, time_window_hours)
            
            # Calculate TPS (queries per second in the window)
            window_total = len(filtered_queries)
            window_seconds = time_window_hours * 3600
            tps = window_total / window_seconds if window_seconds > 0 else 0
            
            # Calculate response time stats
            response_times = [rt for _, rt in filtered_response_times]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            p50_response_time = self._calculate_percentile(response_times, 50)
            p99_response_time = self._calculate_percentile(response_times, 99)
            
            # Calculate availability
            window_errors = len(filtered_errors)
            availability = ((window_total - window_errors) / window_total * 100) if window_total > 0 else 100
            
            # Calculate rates
            web_search_rate = (len(filtered_web_searches) / window_total * 100) if window_total > 0 else 0
            error_rate = (window_errors / window_total * 100) if window_total > 0 else 0
            
            satisfaction_rate = (
                (self._total_feedback_positive / 
                 (self._total_feedback_positive + self._total_feedback_negative) * 100)
                if (self._total_feedback_positive + self._total_feedback_negative) > 0 else 0
            )
            
            # Calculate step-by-step metrics with time series
            step_metrics = {}
            for step, timings in self._step_latencies.items():
                filtered_timings = self._filter_by_time_window(timings, time_window_hours)
                values = [val for _, val in filtered_timings]
                if values:
                    step_metrics[step] = {
                        "avg_ms": round(sum(values) / len(values), 2),
                        "p50_ms": round(self._calculate_percentile(values, 50), 2),
                        "p99_ms": round(self._calculate_percentile(values, 99), 2),
                        "count": len(values),
                        "time_series": filtered_timings
                    }
            
            result = {
                "totals": {
                    "total_queries": self._total_queries,
                    "total_web_searches": self._total_web_searches,
                    "total_errors": self._total_errors,
                    "total_feedback_positive": self._total_feedback_positive,
                    "total_feedback_negative": self._total_feedback_negative,
                },
                "window": {
                    "hours": time_window_hours,
                    "queries": window_total,
                    "errors": window_errors,
                    "web_searches": len(filtered_web_searches),
                    "tps": round(tps, 3)
                },
                "rates": {
                    "availability_percent": round(availability, 2),
                    "avg_response_time_ms": round(avg_response_time, 2),
                    "p50_response_time_ms": round(p50_response_time, 2),
                    "p99_response_time_ms": round(p99_response_time, 2),
                    "web_search_rate_percent": round(web_search_rate, 2),
                    "error_rate_percent": round(error_rate, 2),
                    "satisfaction_rate_percent": round(satisfaction_rate, 2),
                },
                "step_metrics": step_metrics,
                "time_series": {
                    "queries": filtered_queries,
                    "response_times": filtered_response_times,
                    "web_searches": filtered_web_searches,
                    "errors": filtered_errors,
                    "feedback_positive": list(self._feedback_positive),
                    "feedback_negative": list(self._feedback_negative),
                }
            }
            
            # Cache the result
            self._set_cached_metrics(time_window_hours, result)
            
            return result


# Global instance
metrics_service = MetricsService()
