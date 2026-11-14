#!/bin/bash
# 円柱を配置した環境で、乱数の種ごとに 6 つの指示を順に送信し、仕分けの結果を判定する。
# レポート（docs/report/261031_final_report.md）の 5.2 と、AI 版の説明
# （docs/design/261027_ai_detector.md）の 10.4 の結果は、次の指定で取得した。
#
#   bash /ws/experiments/cylinder_distractors/evaluate_sorting.sh /ws/tmp/eval 21 22 23 25 26
#
# 種ごとに 1 行の要約を標準出力に出す。詳細は <出力先>/seed_<種>/ に出力する（既存の内容は上書き）。
#   run.log    指示送信コマンドの出力と所要時間 [s]
#   judge.txt  箱への投入の判定と円柱の移動距離（judge_positions.py）
#   tf.json    物体名ごとの tf 配信回数と、円柱から 4 cm 以内での配信回数（watch_object_frames.py）
#   sim.log、sorter.log、watch.log  各処理のログ

set -u
# watch_object_frames.py を SIGINT で停止できるよう、ジョブ制御を有効にする
set -m

here=$(cd "$(dirname "$0")" && pwd)
root=$1
shift

# 4 つは机上の物体の仕分け、残りの 2 つは机上にない物体と、未登録の語を含む指示
instructions=(
    '赤い直方体を左の箱へ' '赤い立方体を右の箱へ' '青い立方体を左の箱へ' '緑の直方体を右の箱へ'
    '黄色い立方体を左の箱へ' '赤いボールを右の箱へ'
)
# 仕分け後の正しい箱（物体名=箱名）
expected=red_cuboid=left,red_cube=right,blue_cube=left,green_cuboid=right

for seed in "$@"; do
    out_dir=$root/seed_$seed
    rm -rf "$out_dir"
    mkdir -p "$out_dir"
    fastdds shm clean > /dev/null 2>&1
    if ! bash "$here/start_stack.sh" "$out_dir" "$seed" > /dev/null; then
        echo "seed $seed: 起動に失敗しました"
        bash "$here/stop_stack.sh" > /dev/null
        continue
    fi

    # 円柱の配置位置を sim.log から読み取り、tf の監視を開始する
    cylinder_args=()
    while read -r position; do
        cylinder_args+=(--cylinder "$position")
    done < <(grep -a 'distractor_' "$out_dir/sim.log" | sed -E 's/.*x=([-0-9.]+) y=([-0-9.]+).*/\1,\2/')
    setsid python3 "$here/watch_object_frames.py" "$out_dir/tf.json" "${cylinder_args[@]}" \
        > "$out_dir/watch.log" 2>&1 < /dev/null &
    sleep 5

    start=$(date +%s)
    timeout 600 ros2 run crane_sorter send_instruction "${instructions[@]}" > "$out_dir/run.log" 2>&1
    echo "elapsed $(( $(date +%s) - start ))" >> "$out_dir/run.log"
    sleep 4
    pkill -INT -f '[w]atch_object_frames.py'
    sleep 2

    python3 "$here/judge_positions.py" "$out_dir/sim.log" "$expected" > "$out_dir/judge.txt" 2>&1
    bash "$here/stop_stack.sh" > /dev/null
    echo "seed $seed: $(grep RESULT "$out_dir/judge.txt")" \
        "/ 成功 $(grep -a -c '成功' "$out_dir/run.log") 件" \
        "/ $(grep -a 'elapsed' "$out_dir/run.log") s" \
        "/ tf $(cat "$out_dir/tf.json" 2> /dev/null)"
done
