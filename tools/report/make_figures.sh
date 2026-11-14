#!/bin/bash
# レポートの図 1（Gazebo の画面）を動画撮影の録画（record_demo.sh の出力）から切り出し、
# 図 3（検出結果）を save_detections.py で保存した画像から複製する。コンテナ内で実行する。
#
#   bash /ws/tools/report/make_figures.sh <録画の出力先> <図 1 の時刻 [s]> <図 3 の画像> <出力先>
#
# レポート（docs/report/261031_final_report.md）の図は、次の指定で作成した。
# 図 1 の時刻は、最初の指示で赤い直方体を持ち上げた直後である。
#
#   bash /ws/tools/report/make_figures.sh /ws/tmp/video/take6 29.5 \
#       /ws/tmp/video/take6_detections/1793177663.6.png /ws/docs/report/images
#
# 出力:
#   gazebo_carrying.png   図 1。録画の指定時刻の画面から、Gazebo の 3D 表示部分を切り出したもの
#   owlv2_detections.png  図 3。指定した検出結果画像の複製

set -eu

if [ $# -ne 4 ]; then
    sed -n '2,6p' "$0" >&2
    exit 2
fi
take_dir=$1
time_seconds=$2
detection_image=$3
out_dir=$4

# 録画（1920 × 1080）のうち、Gazebo の 3D 表示部分（幅 1280、高さ 740、左端 0、上端 215）。
# record_demo.sh の窓の配置と Gazebo の視点に対応する
gazebo_crop=1280:740:0:215

mkdir -p "$out_dir"
ffmpeg -hide_banner -loglevel error -y -ss "$time_seconds" -i "$take_dir/screen.mkv" \
    -frames:v 1 -vf "crop=$gazebo_crop" "$out_dir/gazebo_carrying.png"
cp "$detection_image" "$out_dir/owlv2_detections.png"
echo "$out_dir に図 1 と図 3 を作成しました"
