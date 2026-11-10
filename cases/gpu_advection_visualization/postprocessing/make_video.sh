#!/bin/bash
# Render the time steps with advect_scene.py in parallel and encode the video.
#
# Usage: make_video.sh <data_dir> <out_dir> [num_workers] [steps_per_second] [stride]
# The video has 24 fps. With steps_per_second < 24 each rendered step is shown for several frames.
# stride > 1 renders only every stride-th time step (e.g. for a quick test).
# Writes <out_dir>/frames/frame_NNN.png, <out_dir>/advect_hybrid_cube.mp4 and
# <out_dir>/advect_hybrid_cube_still.png (middle rendered step).
set -e

data_dir=$1
out_dir=$2
workers=${3:-28}
steps_per_second=${4:-24}
stride=${5:-1}
script_dir=$(cd "$(dirname "$0")" && pwd)
pvpython="env -u LD_LIBRARY_PATH -u PYTHONPATH LP_NUM_THREADS=4 /usr/bin/pvpython --force-offscreen-rendering"

num_steps=$(ls "$data_dir" | grep -c -E '^advection_[0-9]+\.pvtu$')
steps=( $(seq 0 $stride $(( num_steps - 1 ))) )
mkdir -p "$out_dir/frames" "$out_dir/logs"
rm -f "$out_dir"/frames/frame_*.png

# Contiguous ranges of the selected steps, one per worker.
chunk=$(( (${#steps[@]} + workers - 1) / workers ))
for (( i = 0; i < ${#steps[@]}; i += chunk )); do
  j=$(( i + chunk - 1 < ${#steps[@]} - 1 ? i + chunk - 1 : ${#steps[@]} - 1 ))
  $pvpython "$script_dir/advect_scene.py" render "$data_dir" "$out_dir/frames" ${steps[$i]} ${steps[$j]} $stride \
    > "$out_dir/logs/render_${steps[$i]}.log" 2>&1 &
done
wait

missing=0
for step in "${steps[@]}"; do
  [ -f "$out_dir/frames/$(printf frame_%03d.png $step)" ] || { echo "missing frame $step"; missing=1; }
done
[ $missing = 0 ] || exit 1

ffmpeg -y -loglevel error -framerate $steps_per_second -pattern_type glob -i "$out_dir/frames/frame_*.png" \
  -r 24 -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -movflags +faststart \
  "$out_dir/advect_hybrid_cube.mp4"
cp "$out_dir/frames/$(printf frame_%03d.png ${steps[$(( ${#steps[@]} / 2 ))]})" "$out_dir/advect_hybrid_cube_still.png"
echo "done: ${#steps[@]} frames"
