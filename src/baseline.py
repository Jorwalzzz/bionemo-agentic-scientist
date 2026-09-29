"""
Local CPU Baseline Benchmark Runner for Protein Embedding Generation.

Benchmarks Hugging Face's lightweight `facebook/esm2_t6_8M_UR50D` model on local CPU
without GPU acceleration to evaluate time-per-residue (ms/residue), token throughput
(tokens/sec), and memory footprint.
"""

from __future__ import annotations

import time
import logging
import tracemalloc
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

import torch

logger = logging.getLogger(__name__)

DEFAULT_BASELINE_MODEL = "facebook/esm2_t6_8M_UR50D"


@dataclass
class BaselineProfileResult:
    """Latency, throughput, and memory profiling metrics for CPU baseline inference."""
    sequence_length: int
    tokenization_ms: float
    forward_pass_ms: float
    total_cpu_latency_ms: float
    ms_per_residue: float
    tokens_per_sec: float
    peak_memory_mb: float
    tensor_bytes: int
    tensor_shape: Tuple[int, ...]
    model_name: str
    is_mock: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class LocalCPUBaseline:
    """
    Runner for local CPU ESM-2 inference benchmarking.
    Measures baseline unaccelerated compute performance across varying protein sequence lengths.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_BASELINE_MODEL,
        device: str = "cpu",
        lazy_load: bool = True,
        mock_fallback: bool = True,
    ):
        self.model_name = model_name
        self.device = torch.device(device)
        self.mock_fallback = mock_fallback
        self.tokenizer = None
        self.model = None
        self._is_loaded = False
        self._using_mock = False

        if not lazy_load:
            self.load_model()

    def load_model(self) -> None:
        """Loads tokenizer and model weights onto the target device (CPU)."""
        if self._is_loaded:
            return

        try:
            logger.info("Loading baseline ESM-2 model '%s' on %s...", self.model_name, self.device)
            from transformers import AutoTokenizer, AutoModel

            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModel.from_pretrained(self.model_name)
            self.model.to(self.device)
            self.model.eval()
            self._is_loaded = True
            self._using_mock = False
            logger.info("Baseline ESM-2 model successfully loaded.")
        except Exception as e:
            if self.mock_fallback:
                logger.warning(
                    "Unable to load '%s' from HuggingFace hub (%s). Falling back to CPU simulation mode.",
                    self.model_name,
                    str(e),
                )
                self._is_loaded = True
                self._using_mock = True
            else:
                raise RuntimeError(f"Failed to load baseline model {self.model_name}: {e}") from e

    def benchmark_sequence(
        self,
        sequence: str,
        warmup_runs: int = 1,
        benchmark_runs: int = 3,
    ) -> BaselineProfileResult:
        """
        Runs protein sequence embedding inference on local CPU and records execution metrics.

        Args:
            sequence: Validated amino acid sequence string.
            warmup_runs: Initial untimed runs to warm CPU caches and instruction paths.
            benchmark_runs: Timed repeated runs to average out timing jitter.

        Returns:
            BaselineProfileResult with detailed latency, throughput, and memory stats.
        """
        clean_seq = sequence.strip().upper()
        seq_len = len(clean_seq)

        if not self._is_loaded:
            self.load_model()

        if self._using_mock:
            return self._benchmark_mock(clean_seq, seq_len)

        # Warmup CPU caches
        inputs = self.tokenizer(clean_seq, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            for _ in range(warmup_runs):
                _ = self.model(**inputs)

        # Memory profiling with tracemalloc
        tracemalloc.start()
        start_mem_peak = tracemalloc.get_traced_memory()[1]

        # Tokenization timing
        t_tok_start = time.perf_counter()
        tokenized_inputs = self.tokenizer(clean_seq, return_tensors="pt")
        tokenized_inputs = {k: v.to(self.device) for k, v in tokenized_inputs.items()}
        t_tok_end = time.perf_counter()
        tokenization_ms = (t_tok_end - t_tok_start) * 1000.0

        # Timed forward passes
        forward_times = []
        last_hidden_state = None

        with torch.no_grad():
            for _ in range(max(1, benchmark_runs)):
                t_fwd_start = time.perf_counter()
                outputs = self.model(**tokenized_inputs)
                t_fwd_end = time.perf_counter()
                forward_times.append((t_fwd_end - t_fwd_start) * 1000.0)
                last_hidden_state = outputs.last_hidden_state

        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_memory_mb = max(0.01, (peak_mem - start_mem_peak) / (1024.0 * 1024.0))

        # Average forward pass duration
        avg_forward_ms = sum(forward_times) / len(forward_times)
        total_latency_ms = tokenization_ms + avg_forward_ms

        # Throughput calculations
        ms_per_residue = total_latency_ms / max(1, seq_len)
        tokens_per_sec = (seq_len / (total_latency_ms / 1000.0)) if total_latency_ms > 0 else 0.0

        # Tensor memory footprint
        tensor_bytes = 0
        tensor_shape = (1, seq_len, 320)
        if last_hidden_state is not None:
            tensor_bytes = last_hidden_state.element_size() * last_hidden_state.nelement()
            tensor_shape = tuple(last_hidden_state.shape)

        return BaselineProfileResult(
            sequence_length=seq_len,
            tokenization_ms=round(tokenization_ms, 3),
            forward_pass_ms=round(avg_forward_ms, 3),
            total_cpu_latency_ms=round(total_latency_ms, 3),
            ms_per_residue=round(ms_per_residue, 4),
            tokens_per_sec=round(tokens_per_sec, 2),
            peak_memory_mb=round(peak_memory_mb, 2),
            tensor_bytes=tensor_bytes,
            tensor_shape=tensor_shape,
            model_name=self.model_name,
            is_mock=False,
            metadata={"benchmark_runs": benchmark_runs, "device": str(self.device)},
        )

    def _benchmark_mock(self, clean_seq: str, seq_len: int) -> BaselineProfileResult:
        """
        Synthesizes realistic CPU unaccelerated baseline latency metrics.
        On an average modern x86 CPU, 8M ESM-2 runs at roughly 0.45 - 1.2 ms per residue
        with quadratic attention growth overhead at longer sequences.
        """
        # Baseline CPU performance characteristics
        tok_ms = 0.5 + (seq_len * 0.005)
        # O(N) feedforward + O(N^2) unaccelerated attention component
        fwd_ms = (seq_len * 0.55) + (0.0004 * (seq_len**2))
        total_ms = tok_ms + fwd_ms

        ms_per_res = total_ms / seq_len
        tokens_per_sec = seq_len / (total_ms / 1000.0)

        # Emulate CPU processing delay (proportional but bounded for quick benchmark execution)
        emulated_delay = min(0.08, total_ms / 2000.0)
        time.sleep(emulated_delay)

        hidden_dim = 320  # ESM2-t6-8M hidden dimension
        tensor_shape = (1, seq_len + 2, hidden_dim)  # includes CLS and EOS tokens
        tensor_bytes = (seq_len + 2) * hidden_dim * 4  # float32 = 4 bytes
        peak_mem_mb = 12.0 + (seq_len * 0.02)

        return BaselineProfileResult(
            sequence_length=seq_len,
            tokenization_ms=round(tok_ms, 3),
            forward_pass_ms=round(fwd_ms, 3),
            total_cpu_latency_ms=round(total_ms, 3),
            ms_per_residue=round(ms_per_res, 4),
            tokens_per_sec=round(tokens_per_sec, 2),
            peak_memory_mb=round(peak_mem_mb, 2),
            tensor_bytes=tensor_bytes,
            tensor_shape=tensor_shape,
            model_name=f"{self.model_name} (CPU Simulated)",
            is_mock=True,
            metadata={"device": "cpu-simulated"},
        )
