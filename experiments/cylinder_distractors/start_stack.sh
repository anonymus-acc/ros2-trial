#!/bin/bash
# 円柱を配置した仕分け環境（Gazebo）と AI 版のノードを起動し、指示を受け付けられる状態まで待機する。
# evaluate_sorting.sh から呼び出す。コンテナ内で実行し、停止には stop_stack.sh を使用する。
#
#   bash start_stack.sh <ログの出力先> <乱数の種>
#
# 出力:
#   sim.log     sim.launch.py のログ（物体と円柱の配置位置を含む）
#   sorter.log  sorter.launch.py のログ
#
# 起動に失敗した場合は、終了コード 1 で終了する。起動途中の処理は残るため、stop_stack.sh で停止する。

set -eu
# 非対話の bash では、バックグラウンドの処理が SIGINT を無視する設定で起動される。
# stop_stack.sh の SIGINT で停止できるよう、ジョブ制御を有効にする
set -m

out_dir=$1
seed=$2
mkdir -p "$out_dir"
export DISPLAY=:1

wait_for_log() {
    local file=$1 pattern=$2 timeout=$3
    for _ in $(seq "$timeout"); do
        grep -aq "$pattern" "$file" 2> /dev/null && return 0
        sleep 1
    done
    echo "起動待ちが時間切れになりました: $file に「$pattern」が出力されません" >&2
    return 1
}

# 画面の保護が有効になると Gazebo の画面が描画されないため、停止する
pkill -f '[m]ate-screensaver' || true

setsid ros2 launch crane_sorter sim.launch.py \
    layout:=/ws/src/crane_sorter/config/layout_shapes.yaml seed:="$seed" \
    > "$out_dir/sim.log" 2>&1 < /dev/null &
wait_for_log "$out_dir/sim.log" 'Configured and activated crane_plus_arm_controller' 120
sleep 5
setsid ros2 launch crane_sorter sorter.launch.py detector:=ai \
    > "$out_dir/sorter.log" 2>&1 < /dev/null &
wait_for_log "$out_dir/sorter.log" '用意しました' 180
wait_for_log "$out_dir/sorter.log" '依頼を待っています' 180

# RViz は crane_plus の launch が必ず起動するが、試験には不要なため終了する
pkill -f 'lib/rviz2/[r]viz2' || true
echo ready
