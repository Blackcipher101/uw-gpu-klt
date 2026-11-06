# uw-gpu-klt

CUDA port of the `uw_ct_vio` KLT stereo front end: a drop-in `GpuKltStereoTracker` that reproduces the algorithm
and OpenCV's numerics on the GPU.

| `track()` latency per frame, CPU vs GPU | End-to-end ATE with CPU vs GPU tracks |
|---|---|
| [![Latency CPU vs GPU](docs/figures/latency_cpu_vs_gpu.png)](docs/figures/latency_cpu_vs_gpu.png) | [![ATE CPU vs GPU](docs/figures/ate_cpu_vs_gpu.png)](docs/figures/ate_cpu_vs_gpu.png) |
| NTNU traj_06, 6058 frames, shared RTX 5080 (other users' jobs inflate GPU tails) | all 6 NTNU 2023 trajectories, one run each |

[![What runs on GPU vs CPU](docs/figures/pipeline_gpu_vs_cpu.png)](docs/DESIGN.md)

## Results

Front end, NTNU traj_06, 6058 frames, closed loop, workstation RTX 5080 (shared machine, 2026-11-04):

| ms/frame | mean | P50 | P95 | P99 | max |
|---|---|---|---|---|---|
| CPU `track()` | 19.28 | 19.01 | 26.31 | 31.58 | 49.97 |
| GPU `track()` | 9.53 | 7.91 | 20.69 | 24.24 | 37.57 |

Speed-up 2.0x mean, 2.4x P50 (laptop, quiet period: 4.9x mean). Not measured on Jetson Orin (sm_87 compiled,
never run).

End to end, uw_ct_vio best config (h05) on all 6 NTNU 2023 trajectories, same binary and flags:

| tracks | mean ATE (m) | mean RPE (%) |
|---|---|---|
| CPU KLT (h05) | 0.401 | 6.75 |
| GPU KLT | 0.341 | 6.71 |

No accuracy loss on any trajectory. One run per trajectory, no variance estimate: the lower GPU mean is NOT
claimed as an improvement.

## Quick start

```bash
git clone https://github.com/Blackcipher101/uw-vio-dvl ../uw-vio-dvl   # CPU reference tracker and types
bash -lc 'source /opt/ros/jazzy/setup.bash && \
  cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DGTSAM_PREFIX=$HOME/deps/gtsam-4.2.0 \
        -DCMAKE_CUDA_COMPILER=/usr/local/cuda-12.8/bin/nvcc && cmake --build build -j2'
LD_LIBRARY_PATH=$HOME/deps/gtsam-4.2.0/lib ctest --test-dir build --output-on-failure
bench/run_bench.sh --gpu-keepalive    # NTNU root from $NTNU
```

## More

- [docs/DESIGN.md](docs/DESIGN.md): which stages run on the GPU and their measured fidelity to the CPU tracker,
  unsupported options, synchronisation and allocation behaviour, CUDA architectures.
- [docs/BENCHMARK.md](docs/BENCHMARK.md): build and test, benchmark options, the `UWTRK1` track replay, the full
  per-trajectory ATE table and figure regeneration.

Known limits: `map_predict`, `reacquire`, `snr_sigma`, `ncc_noise_aware` not implemented (constructor throws);
max 2048 features; single-threaded use; only sm_120 has been run.
