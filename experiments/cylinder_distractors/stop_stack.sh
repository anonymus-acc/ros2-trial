#!/bin/bash
# start_stack.sh で起動した処理を停止する。まず SIGINT で停止し、残った処理は SIGTERM、SIGKILL の順に
# 停止する。SIGKILL を使用した場合は、以降のノード間通信の不具合を防ぐため共有メモリを清掃する。
#
#   bash stop_stack.sh

# 実行ファイルのパスを含む形で指定し、名前に触れるだけの無関係の処理（シェルなど）を停止しないようにする
pkill -INT -f 'bin/[r]os2 launch crane_sorter sorter' || true
pkill -INT -f 'bin/[r]os2 launch crane_sorter sim' || true
sleep 10

# launch の子プロセスを含め、試験で起動しうる処理の一覧
patterns=(
    'bin/[r]os2 launch crane_sorter' 'lib/crane_sorter/[o]bject_detector'
    'lib/crane_sorter/[p]ick_and_place_server' 'lib/robot_state_publisher/[r]obot_state_publisher'
    'lib/ros_gz_bridge/[p]arameter_bridge' 'lib/tf2_ros/[s]tatic_transform_publisher'
    'lib/controller_manager/[s]pawner' 'lib/moveit_ros_move_group/[m]ove_group' '^gz sim'
    'lib/rviz2/[r]viz2'
)
for pattern in "${patterns[@]}"; do pkill -TERM -f "$pattern"; done
sleep 4
killed=0
for pattern in "${patterns[@]}"; do pkill -KILL -f "$pattern" && killed=1; done
if [ "$killed" = 1 ]; then
    sleep 1
    fastdds shm clean > /dev/null
    echo 'SIGKILL で停止した処理があったため、共有メモリを清掃しました'
fi
pgrep -af '^gz sim|lib/moveit_ros_move_group/[m]ove_group|lib/robot_state_publisher/[r]obot|bin/[r]os2 launch' \
    || echo stopped
