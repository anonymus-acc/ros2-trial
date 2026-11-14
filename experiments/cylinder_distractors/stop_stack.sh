#!/bin/bash
# start_stack.sh で起動した処理を停止する。まず SIGINT で停止し、残った処理は SIGTERM、SIGKILL の順に
# 停止する。SIGKILL を使用した場合は、以降のノード間通信の不具合を防ぐため共有メモリを清掃する。
#
#   bash stop_stack.sh

pkill -INT -f '[r]os2 launch crane_sorter sorter' || true
pkill -INT -f '[r]os2 launch crane_sorter sim' || true
sleep 10

# launch の子プロセスを含め、試験で起動しうる処理の一覧
patterns=(
    '[r]os2 launch crane_sorter' '[o]bject_detector' '[p]ick_and_place_server'
    '[r]obot_state_publisher' '[p]arameter_bridge' '[s]tatic_transform_publisher'
    '[c]ontroller_manager/spawner' '[m]ove_group' '[g]z sim' '[r]viz2'
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
pgrep -af '[g]z sim|[m]ove_group|[r]obot_state_publisher|[r]os2 launch' || echo stopped
