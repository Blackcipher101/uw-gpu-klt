#!/bin/bash
# usage: bench/run_bench.sh [extra bench_frontend flags]   (bash; sources ROS 2 Jazzy)
# Env: BUILD (default ./build), GTSAM_PREFIX (default ../deps/gtsam-4.2.0),
#      NTNU (default ~/svin_data/ntnu: needs traj_06/traj_06_ros2 and calibration/).
source /opt/ros/jazzy/setup.bash
HERE=$(cd "$(dirname "$0")/.." && pwd)
BUILD=${BUILD:-$HERE/build}
GTSAM_PREFIX=${GTSAM_PREFIX:-$HERE/../deps/gtsam-4.2.0}
NTNU=${NTNU:-$HOME/svin_data/ntnu}
export LD_LIBRARY_PATH=$GTSAM_PREFIX/lib:${LD_LIBRARY_PATH:-}
C=$NTNU/calibration
exec "$BUILD/bench_frontend" --bag "$NTNU/traj_06/traj_06_ros2" \
  --intrinsics "$C/stereo_intrinsics_under_water/camchain-ariel_stereo_underwater.yaml" \
  --imucam "$C/stereo_extrinsics_above_water/camchain-imucam-ariel_stereo_extrinsics_above_water.yaml" \
  --left cam1 --right cam0 --left-topic /alphasense_driver_ros/cam1 --right-topic /alphasense_driver_ros/cam0 \
  --lcn 2 --lcn-stereo 0 "$@"
