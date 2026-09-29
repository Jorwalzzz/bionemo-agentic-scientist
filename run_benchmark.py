#!/usr/bin/env python3
"""
NVIDIA BioNeMo & NIM Inference Benchmark CLI Runner.

Executes comparative benchmarks evaluating NVIDIA NIM endpoints (ESM-2, DiffDock)
against local unaccelerated CPU baselines across varying protein sequence lengths
and FDA-approved small-molecule complexes.
"""

from __future__ import annotations

import os
import sys
import json
import argparse
import logging
from typing import List, Dict, Any

from dotenv import load_dotenv
import pandas as pd

from src.client import NimBioClient
from src.baseline import LocalCPUBaseline
from src.pipeline import BenchmarkPipeline, ComplexBenchmarkRecord
from src.metrics import BenchmarkReporter

# Load environment variables from .env if present
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("BioNeMoBenchmark")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="NVIDIA BioNeMo & NIM Inference Benchmark Suite",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        default=False,
        help="Force mock simulation mode for NIM microservices (ideal for CI/CD or offline execution).",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="NVIDIA API key (overrides NVIDIA_API_KEY from environment or .env).",
    )
    parser.add_argument(
        "--samples",
        type=str,
        default="data/sample_complexes.json",
        help="Path to JSON file containing target complexes and SMILES ligands.",
    )
    parser.add_argument(
        "--save-plots",
        action="store_true",
        default=False,
        help="Generate and save publication-quality Seaborn/Matplotlib charts to output directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results",
        help="Directory to store benchmark CSV reports and generated charts.",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=2,
        help="Number of timed forward passes to average for CPU baseline timing.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Enable detailed DEBUG level logging.",
    )
    return parser.parse_args()


def load_sample_complexes(filepath: str) -> List[Dict[str, Any]]:
    """Loads sample complex dataset from JSON."""
    if not os.path.exists(filepath):
        logger.error("Sample complexes file not found: %s", filepath)
        sys.exit(1)
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected a list of complexes in {filepath}, got {type(data)}")
    return data


def print_ascii_header(mock_mode: bool) -> None:
    mode_str = "[ MOCK SIMULATION (CI/CD READY) ]" if mock_mode else "[ LIVE NVIDIA NIM CLOUD ENDPOINTS ]"
    print("\n" + "=" * 80)
    print("  NVIDIA BioNeMo & NIM Inference Benchmark Suite")
    print(f"  Mode: {mode_str}")
    print("  Evaluating GPU TensorRT Microservices vs. Local Unaccelerated CPU Baseline")
    print("=" * 80 + "\n")


def print_results_table(records: List[ComplexBenchmarkRecord]) -> None:
    """Formats and prints executive summary table."""
    summary_rows = []
    for r in records:
        summary_rows.append({
            "Complex ID": r.complex_id,
            "Target (Residues)": f"{r.target_name[:18]} ({r.residue_count}aa)",
            "Drug (MW)": f"{r.drug_name.split()[0]} ({r.ligand_validation.molecular_weight or 0:.0f}g/mol)",
            "NIM Latency": f"{r.nim_total_latency_ms:.1f} ms",
            "NIM Throughput": f"{r.nim_tokens_per_sec:.0f} tok/s",
            "CPU Latency": f"{r.cpu_total_latency_ms:.1f} ms",
            "CPU Throughput": f"{r.cpu_tokens_per_sec:.0f} tok/s",
            "Speedup": f"{r.speedup_factor:.1f}x",
            "DiffDock Affinity": f"{r.diffdock_top_affinity_kcal_mol:.1f} kcal/mol",
        })

    df = pd.DataFrame(summary_rows)
    print("\n" + "-" * 80)
    print("BENCHMARK EXECUTION SUMMARY TABLE")
    print("-" * 80)
    print(df.to_string(index=False))
    print("-" * 80 + "\n")


def main() -> None:
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    api_key = args.api_key or os.getenv("NVIDIA_API_KEY", "")
    is_mock = args.mock or not api_key or api_key.startswith("nvapi-your-key-here")

    print_ascii_header(mock_mode=is_mock)

    # Load complexes
    samples = load_sample_complexes(args.samples)
    logger.info("Loaded %d target complexes from %s", len(samples), args.samples)

    # Initialize client, baseline, and pipeline
    nim_client = NimBioClient(api_key=api_key, mock=is_mock)
    cpu_baseline = LocalCPUBaseline(mock_fallback=True)
    pipeline = BenchmarkPipeline(nim_client=nim_client, cpu_baseline=cpu_baseline)

    # Execute benchmark suite
    logger.info("Starting benchmark evaluation loop (%d iterations/sample)...", args.iterations)
    records = pipeline.run_suite(samples, benchmark_runs=args.iterations)

    # Generate Reporter & CSV
    reporter = BenchmarkReporter(records, output_dir=args.output_dir)
    csv_path = reporter.export_csv("benchmark_summary.csv")
    print(f" Saved structured metrics to: {csv_path}")

    # Display Table
    print_results_table(records)

    # Generate Plots if requested
    if args.save_plots:
        t_plot = reporter.plot_throughput_comparison("throughput_comparison.png")
        l_plot = reporter.plot_latency_vs_length("latency_vs_length.png")
        print(f" Generated throughput comparison chart: {t_plot}")
        print(f" Generated latency scaling chart:        {l_plot}")

    # Aggregate summary metrics
    stats = reporter.get_aggregate_stats()
    avg_speedup = stats["speedup_stats"]["mean"]
    max_speedup = stats["speedup_stats"]["max"]
    print(f" Benchmark Complete! Average Acceleration: {avg_speedup:.1f}x (Peak: {max_speedup:.1f}x)\n")


if __name__ == "__main__":
    main()
