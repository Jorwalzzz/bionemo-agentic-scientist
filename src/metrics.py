"""
Benchmark Metrics Profiling, Statistical Aggregation, and Visualization Engine.

Generates publication-quality comparative plots (Seaborn/Matplotlib) and exports
CSV performance summary tables evaluating NVIDIA NIM acceleration vs. local CPU baselines.
"""

from __future__ import annotations

import os
import logging
from typing import List, Dict, Any, Tuple
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from src.pipeline import ComplexBenchmarkRecord

logger = logging.getLogger(__name__)

# Design Palette: NVIDIA Developer Green & Sleek Dark Contrast
NVIDIA_GREEN = "#76B900"
DARK_TEAL = "#0B3C49"
CPU_BLUE = "#3A86FF"
CORAL_ACCENT = "#FF5964"
CHARCOAL = "#212529"
BG_LIGHT = "#F8F9FA"


def compute_summary_statistics(values: List[float]) -> Dict[str, float]:
    """Computes mean, median, standard deviation, min, max, and 95th percentile."""
    if not values:
        return {"mean": 0.0, "median": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "p95": 0.0}
    arr = np.array(values, dtype=float)
    return {
        "mean": round(float(np.mean(arr)), 2),
        "median": round(float(np.median(arr)), 2),
        "std": round(float(np.std(arr)), 2),
        "min": round(float(np.min(arr)), 2),
        "max": round(float(np.max(arr)), 2),
        "p95": round(float(np.percentile(arr, 95)), 2),
    }


class BenchmarkReporter:
    """
    Manages benchmark data aggregation, tabular CSV reporting, and graphical charting.
    """

    def __init__(self, records: List[ComplexBenchmarkRecord], output_dir: str = "results"):
        self.records = records
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.df = pd.DataFrame([r.to_dict() for r in records])

    def export_csv(self, filename: str = "benchmark_summary.csv") -> str:
        """Exports full benchmark metrics to CSV."""
        filepath = os.path.join(self.output_dir, filename)
        self.df.to_csv(filepath, index=False)
        logger.info("Saved benchmark CSV to %s", filepath)
        return filepath

    def get_aggregate_stats(self) -> Dict[str, Any]:
        """Calculates aggregate latency and throughput statistics."""
        return {
            "nim_latency_stats": compute_summary_statistics(self.df["nim_total_latency_ms"].tolist()),
            "cpu_latency_stats": compute_summary_statistics(self.df["cpu_total_latency_ms"].tolist()),
            "nim_throughput_stats": compute_summary_statistics(self.df["nim_tokens_per_sec"].tolist()),
            "cpu_throughput_stats": compute_summary_statistics(self.df["cpu_tokens_per_sec"].tolist()),
            "speedup_stats": compute_summary_statistics(self.df["speedup_factor"].tolist()),
            "diffdock_latency_stats": compute_summary_statistics(self.df["diffdock_latency_ms"].tolist()),
        }

    def plot_throughput_comparison(self, filename: str = "throughput_comparison.png") -> str:
        """
        Generates publication-grade comparative bar plot comparing
        NVIDIA NIM GPU throughput against Local CPU Baseline (Tokens / Sec).
        """
        filepath = os.path.join(self.output_dir, filename)

        # Configure style
        sns.set_theme(style="whitegrid", font="sans-serif")
        plt.rcParams["font.family"] = "sans-serif"

        fig, ax = plt.subplots(figsize=(11, 6.5), dpi=300)

        # Prepare grouped bar data
        df_sorted = self.df.sort_values(by="residue_count").reset_index(drop=True)
        labels = [f"{row['target_name'][:18]}...\n({row['residue_count']} aa)" for _, row in df_sorted.iterrows()]

        x = np.arange(len(labels))
        width = 0.35

        rects1 = ax.bar(
            x - width / 2,
            df_sorted["cpu_tokens_per_sec"],
            width,
            label="Local CPU Baseline (ESM-2 8M)",
            color="#4A90E2",
            edgecolor="#2C5282",
            linewidth=1.2,
            alpha=0.9,
        )

        rects2 = ax.bar(
            x + width / 2,
            df_sorted["nim_tokens_per_sec"],
            width,
            label="NVIDIA BioNeMo NIM (ESM-2 650M GPU)",
            color=NVIDIA_GREEN,
            edgecolor="#4B7700",
            linewidth=1.2,
            alpha=0.95,
        )

        # Annotate Speedup multipliers above NIM bars
        for idx, row in df_sorted.iterrows():
            speedup = row["throughput_improvement_ratio"]
            y_val = row["nim_tokens_per_sec"]
            ax.annotate(
                f"{speedup:.1f}x\nSpeedup",
                xy=(x[idx] + width / 2, y_val),
                xytext=(0, 6),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=9.5,
                fontweight="bold",
                color="#2F4F4F",
            )

        # Labels & Aesthetics
        ax.set_ylabel("Residue Throughput (Tokens / Sec)", fontsize=12, fontweight="bold", labelpad=10)
        ax.set_title(
            "Residue Processing Throughput: NVIDIA BioNeMo NIM vs. Local CPU Baseline",
            fontsize=14,
            fontweight="bold",
            pad=15,
        )
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=10)
        ax.legend(frameon=True, facecolor="white", edgecolor="#CBD5E0", fontsize=10.5, loc="upper right")

        # Subtle upper bound padding for annotations
        max_val = df_sorted["nim_tokens_per_sec"].max()
        ax.set_ylim(0, max_val * 1.22)
        ax.grid(axis="y", linestyle="--", alpha=0.5)

        # Subtitle note
        plt.figtext(
            0.5,
            0.01,
            "NVIDIA NIM ESM-2 TensorRT GPU Microservice vs. Single-Socket Host CPU (Higher is Better)",
            ha="center",
            fontsize=9.5,
            color="#64748B",
            style="italic",
        )

        plt.tight_layout(rect=[0, 0.03, 1, 0.98])
        fig.savefig(filepath, dpi=300, bbox_inches="tight")
        plt.close(fig)
        logger.info("Saved throughput comparison plot to %s", filepath)
        return filepath

    def plot_latency_vs_length(self, filename: str = "latency_vs_length.png") -> str:
        """
        Generates publication-quality scaling curves showing total inference latency
        vs. protein sequence length in amino acid residues.
        """
        filepath = os.path.join(self.output_dir, filename)

        sns.set_theme(style="whitegrid", font="sans-serif")
        fig, ax = plt.subplots(figsize=(10.5, 6), dpi=300)

        df_sorted = self.df.sort_values(by="residue_count").reset_index(drop=True)
        res_counts = df_sorted["residue_count"].values

        # CPU Curve
        ax.plot(
            res_counts,
            df_sorted["cpu_total_latency_ms"],
            marker="o",
            markersize=8,
            linewidth=2.5,
            color="#E63946",
            label="Local CPU Baseline (Unaccelerated)",
        )

        # NIM GPU Curve
        ax.plot(
            res_counts,
            df_sorted["nim_total_latency_ms"],
            marker="s",
            markersize=8,
            linewidth=2.5,
            color=NVIDIA_GREEN,
            label="NVIDIA NIM ESM-2 (TensorRT GPU)",
        )

        # DiffDock Docking Latency
        ax.plot(
            res_counts,
            df_sorted["diffdock_latency_ms"],
            marker="^",
            markersize=8,
            linewidth=2.0,
            linestyle="--",
            color="#9B5DE5",
            label="NVIDIA NIM DiffDock (Molecular Docking)",
        )

        # Annotations for each data point
        for _, row in df_sorted.iterrows():
            ax.annotate(
                f"{row['nim_total_latency_ms']:.0f}ms",
                (row["residue_count"], row["nim_total_latency_ms"]),
                textcoords="offset points",
                xytext=(0, -15),
                ha="center",
                fontsize=8.5,
                color="#2E7D32",
                fontweight="bold",
            )
            ax.annotate(
                f"{row['cpu_total_latency_ms']:.0f}ms",
                (row["residue_count"], row["cpu_total_latency_ms"]),
                textcoords="offset points",
                xytext=(0, 10),
                ha="center",
                fontsize=8.5,
                color="#C62828",
                fontweight="bold",
            )

        ax.set_xlabel("Protein Sequence Length (Residues / Amino Acids)", fontsize=11, fontweight="bold", labelpad=8)
        ax.set_ylabel("Total Latency (Milliseconds)", fontsize=11, fontweight="bold", labelpad=8)
        ax.set_title(
            "Inference Latency Scaling vs. Protein Sequence Length",
            fontsize=13.5,
            fontweight="bold",
            pad=14,
        )
        ax.legend(frameon=True, facecolor="white", edgecolor="#CBD5E0", fontsize=10, loc="upper left")
        ax.grid(True, linestyle="--", alpha=0.5)

        plt.figtext(
            0.5,
            0.01,
            "Evaluated across Human Ubiquitin (76aa), DHFR (150aa), ABL1 (279aa), EGFR (504aa), and SARS-CoV-2 RdRp (850aa)",
            ha="center",
            fontsize=9.0,
            color="#64748B",
            style="italic",
        )

        plt.tight_layout(rect=[0, 0.03, 1, 0.98])
        fig.savefig(filepath, dpi=300, bbox_inches="tight")
        plt.close(fig)
        logger.info("Saved latency vs. length plot to %s", filepath)
        return filepath
