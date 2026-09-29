"""
Unit tests for NVIDIA Hardware Acceleration Benchmark endpoint.
Part of NVIDIA BioNeMo Agentic Scientist Suite.
Copyright (C) 2026 Jorwalzzz.
"""

import pytest
import serve_cockpit

def test_hardware_speedup_benchmark_endpoint():
    res = serve_cockpit.get_hardware_speedup_benchmark()
    
    assert res["status"] == "success"
    assert "cpu_hardware" in res
    assert "NVIDIA H100" in res["gpu_hardware"]
    assert res["overall_speedup_multiplier"] > 10.0
    assert res["total_cpu_latency_sec"] > res["total_h100_latency_sec"]
    assert len(res["tasks"]) == 3
    
    for task in res["tasks"]:
        assert task["speedup"] > 1.0
        assert task["cpu_latency_ms"] > task["h100_latency_ms"]
