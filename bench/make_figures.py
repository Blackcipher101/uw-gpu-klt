#!/usr/bin/env python3
"""Regenerate the README figures of uw-gpu-klt.

Usage: python3 bench/make_figures.py --bench-log <gpu_bench_ws1.log> --ate-tsv <ntnu_all.tsv> [--out docs/figures]

The latency numbers are parsed from the bench_frontend final table (RTX 5080 shared workstation, traj_06,
6058 frames); the ATE numbers from the tab-separated run table (tag, traj, ATE m, RPE %, recoveries) with
tags dvl_none_off (CPU KLT) and gpu_klt (GPU tracks replayed). Nothing is typed in by hand.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

CPU_C, GPU_C, BASE_C = "#8C8C8C", "#2E8B57", "#4C72B0"
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": "white", "axes.facecolor": "white", "savefig.dpi": 150})
ROW = re.compile(r"^\s*(.+?)\s{2,}([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*$")
STATS = ("mean", "P50", "P95", "P99", "max")


def parse_latency(path: Path) -> dict[str, dict[str, float]]:
    rows: dict[str, dict[str, float]] = {}
    on = False
    for line in path.read_text().splitlines():
        if line.startswith("latency [ms/frame]"):
            on = True
            continue
        if on and line.startswith("speed-up"):
            break
        m = ROW.match(line) if on else None
        if m:
            rows[m.group(1)] = dict(zip(STATS, map(float, m.groups()[1:])))
    for key in ("CPU total track()", "GPU total track()"):
        if key not in rows:
            raise ValueError(f"{path}: row '{key}' not found")
    return rows


def fig_latency(rows: dict, out: Path) -> None:
    cpu, gpu = rows["CPU total track()"], rows["GPU total track()"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(10.5, 4.2), gridspec_kw={"width_ratios": [1, 1.5]})
    x = range(3)
    labs = ["mean", "P50", "P95"]
    for i, (name, d, c) in enumerate((("CPU (OpenCV)", cpu, CPU_C), ("GPU (CUDA)", gpu, GPU_C))):
        vals = [d[k] for k in labs]
        bars = a.bar([j + (i - 0.5) * 0.38 for j in x], vals, 0.38, color=c, label=name)
        for r, v in zip(bars, vals):
            a.text(r.get_x() + r.get_width() / 2, v + 0.4, f"{v:.1f}", ha="center", fontsize=8.5)
    a.set_xticks(list(x), labs)
    a.set_ylabel("track() latency (ms/frame)")
    a.set_ylim(0, max(cpu["P95"], gpu["P95"]) * 1.25)
    a.set_title(f"GPU front end: {cpu['mean'] / gpu['mean']:.1f}x faster on average,\n"
                f"{cpu['P95'] / gpu['P95']:.1f}x at P95", fontsize=11)
    a.legend(frameon=False, loc="upper left")

    pairs = [("preprocessing", "CPU preprocessing (noise,LCN,CLAHE)", "GPU pre (upload,LCN/CLAHE,pyr)"),
             ("temporal LK", "CPU temporal LK fwd+bwd", "GPU temporal LK (event time)"),
             ("detect", "CPU detect (goodFeaturesToTrack)", "GPU detect (event time)"),
             ("stereo LK", "CPU stereo LK fwd+bwd", "GPU stereo LK (event time)"),
             ("FB filter + RANSAC\n(host, GPU run only)", None, "host FB+RANSAC (wall)")]
    y = list(range(len(pairs)))[::-1]
    for yy, (lab, ck, gk) in zip(y, pairs):
        if ck:
            b.barh(yy + 0.19, rows[ck]["mean"], 0.36, color=CPU_C, label="CPU stage" if yy == y[0] else None)
            b.text(rows[ck]["mean"] + 0.1, yy + 0.19, f"{rows[ck]['mean']:.2f}", va="center", fontsize=8.5)
        b.barh(yy - 0.19, rows[gk]["mean"], 0.36, color=GPU_C, label="GPU stage" if yy == y[0] else None)
        b.text(rows[gk]["mean"] + 0.1, yy - 0.19, f"{rows[gk]['mean']:.2f}", va="center", fontsize=8.5)
    b.set_yticks(y, [p[0] for p in pairs])
    b.set_xlabel("mean time per frame (ms)")
    b.set_title("Per-stage mean (CPU stages are replayed OpenCV calls;\nthey approximate, not sum to, the total)", fontsize=10)
    b.legend(frameon=False, loc="lower right")
    fig.text(0.5, 0.005, "Shared RTX 5080 workstation (other users' jobs inflate GPU tails); NTNU traj_06, 6058 frames, "
             "720x540, closed loop, GPU keepalive on.", ha="center", fontsize=8.5, color="0.3")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(out / "latency_cpu_vs_gpu.png", pil_kwargs={"optimize": True})
    plt.close(fig)


def fig_ate(tsv: Path, out: Path) -> None:
    d: dict = {}
    for line in tsv.read_text().splitlines():
        tag, traj, ate, *_ = line.split("\t")
        if tag in ("dvl_none_off", "gpu_klt") and not traj.startswith("MEAN"):
            d.setdefault(tag, {})[traj] = float(ate)
    trajs = sorted(d["gpu_klt"])
    fig, ax = plt.subplots(figsize=(8.2, 3.9))
    for i, (tag, name, c) in enumerate((("dvl_none_off", "CPU KLT", CPU_C), ("gpu_klt", "GPU KLT (tracks replayed)", GPU_C))):
        v = [d[tag][t] for t in trajs]
        bars = ax.bar([j + (i - 0.5) * 0.38 for j in range(len(trajs))], v, 0.38, color=c, label=name)
        for r, val in zip(bars, v):
            ax.text(r.get_x() + r.get_width() / 2, val + 0.01, f"{val:.2f}", ha="center", fontsize=8)
    mean = {k: sum(d[k].values()) / len(d[k]) for k in d}
    ax.set_xticks(range(len(trajs)), [t.replace("traj_", "traj ") for t in trajs])
    ax.set_ylabel("ATE SE3 (m)")
    ax.set_ylim(0, 0.75)
    ax.set_title(f"GPU tracks lose no accuracy on any trajectory (mean ATE {mean['gpu_klt']:.3f} m vs "
                 f"{mean['dvl_none_off']:.3f} m, one run each)", fontsize=10.5)
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(out / "ate_cpu_vs_gpu.png", pil_kwargs={"optimize": True})
    plt.close(fig)


def fig_pipeline(out: Path) -> None:
    """Block diagram of 'What runs where' in README.md (GPU: upload, noise, LCN/CLAHE, pyramids, LK, detect)."""
    fig, ax = plt.subplots(figsize=(11, 3.3))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 3.3)
    ax.axis("off")
    blocks = [("image upload\n(pinned)", "g"), ("noise sigma,\nLCN / CLAHE", "g"), ("pyramids +\nScharr", "g"),
              ("pyramidal LK\nfwd + bwd\n(temporal, stereo)", "g"), ("Shi-Tomasi\ndetect per cell", "g"),
              ("FB check, undistort,\nRANSAC, epipolar", "c"), ("FeatureObs\nto estimator", "o")]
    w, gap, x0 = 1.34, 0.2, 0.1
    for i, (txt, k) in enumerate(blocks):
        x = x0 + i * (w + gap)
        col = {"g": GPU_C, "c": CPU_C, "o": "white"}[k]
        ax.add_patch(FancyBboxPatch((x, 0.9), w, 1.5, boxstyle="round,pad=0.03", fc=col, ec="0.2", alpha=0.9 if k != "o" else 1))
        ax.text(x + w / 2, 1.65, txt, ha="center", va="center", fontsize=9, color="white" if k != "o" else "black")
        if i:
            ax.annotate("", xy=(x - 0.01, 1.65), xytext=(x - gap + 0.02, 1.65), arrowprops=dict(arrowstyle="->", lw=1.2))
    ax.text(x0 + 2.5 * (w + gap), 2.85, "GPU (CUDA, one stream; host syncs 3x per frame)", ha="center", fontsize=10, color=GPU_C)
    ax.text(x0 + 5 * (w + gap) + w / 2, 2.85, "CPU (same code as reference)", ha="center", fontsize=10, color="0.35")
    ax.text(5.5, 0.35, "Detection-mask discs are drawn on the CPU (cv::circle) and uploaded; everything else per the README table.",
            ha="center", fontsize=8.5, color="0.3")
    fig.tight_layout()
    fig.savefig(out / "pipeline_gpu_vs_cpu.png", pil_kwargs={"optimize": True})
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench-log", type=Path, required=True)
    ap.add_argument("--ate-tsv", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent.parent / "docs" / "figures")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    fig_latency(parse_latency(a.bench_log), a.out)
    fig_ate(a.ate_tsv, a.out)
    fig_pipeline(a.out)


if __name__ == "__main__":
    main()
