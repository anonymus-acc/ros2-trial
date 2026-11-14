#!/bin/bash
# 円柱を配置した環境を乱数の種ごとに起動し、カメラ画像を 1 枚ずつ保存する。
# compare_cylinder_prompts.py の入力に使用する。コンテナ内で実行する。
# 検出用語句の選定（AI 版の説明の 10.3）には、次の指定で保存した 5 枚を使用した
# （種 3 は Gazebo の起動に失敗し、画像を保存できなかった）。
#
#   bash /ws/experiments/cylinder_distractors/capture_images.sh /ws/tmp/cylinder_images 24 3 7 11 15 19
#
# 出力: <出力先>/seed_<種>.png、.json（tools/detector_comparison/capture_dataset.py の出力）と、
#       種ごとの起動ログ sim_<種>.log

set -u
# sim.launch.py を SIGINT で停止できるよう、ジョブ制御を有効にする
set -m

here=$(cd "$(dirname "$0")" && pwd)
repo_root=$(cd "$here/../.." && pwd)
out_dir=$1
shift
mkdir -p "$out_dir"
export DISPLAY=:1

for seed in "$@"; do
    setsid ros2 launch crane_sorter sim.launch.py \
        layout:=/ws/src/crane_sorter/config/layout_shapes.yaml seed:="$seed" \
        > "$out_dir/sim_$seed.log" 2>&1 < /dev/null &
    for _ in $(seq 120); do
        grep -aq 'Configured and activated crane_plus_arm_controller' "$out_dir/sim_$seed.log" && break
        sleep 1
    done
    sleep 8
    python3 "$repo_root/tools/detector_comparison/capture_dataset.py" \
        "$out_dir" "seed_$(printf %03d "$seed")"
    bash "$here/stop_stack.sh" > /dev/null
done
