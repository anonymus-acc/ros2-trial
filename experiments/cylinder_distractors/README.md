# 円柱を配置した試験

把持対象外の円柱（赤・青）を机上に配置した環境で実施した、2 つの試験の処理です（issue #17、#28）。
結果と考察は、[AI 版の説明](../../docs/design/261027_ai_detector.md)の 10 章と、[レポート](../../docs/report/261031_final_report.md)の 4.3・5.2 に記載しています。

すべてコンテナの中で実行します。
GPU を使用するため、コンテナは `compose.gpu.yaml` を指定して起動します（README の 1 章）。

## 1. 円柱の検出用語句の比較

円柱に付けるラベルの検出用語句（例: `red cylinder`、`red round block`）の候補ごとに、OWLv2 が円柱に付ける得点と、ラベルの割り当て結果を比較します。
AI 版の説明 10.3 の表は、この結果に基づきます。

```bash
# 乱数の種ごとに Gazebo を起動し、カメラ画像を保存する
bash /ws/experiments/cylinder_distractors/capture_images.sh /ws/tmp/cylinder_images 24 3 7 11 15 19
# 語句の候補ごとに比較する
$AI_VENV/bin/python /ws/experiments/cylinder_distractors/compare_cylinder_prompts.py /ws/tmp/cylinder_images
```

| ファイル | 内容 |
|---|---|
| `capture_images.sh` | 種ごとに Gazebo を起動し、カメラ画像を 1 枚保存する |
| `compare_cylinder_prompts.py` | 語句の候補ごとに、円柱の得点、4 物体のラベルを奪う強さ、割り当ての誤りを出力する |

## 2. 仕分け試験

乱数の種ごとに、4 物体の仕分けと、実行できない 2 つの指示（机上にない物体、未登録の語）を順に送信し、結果を判定します。
レポート 5.2 と AI 版の説明 10.4 の結果は、次の指定で取得しました（1 種あたり約 4 分）。

```bash
bash /ws/experiments/cylinder_distractors/evaluate_sorting.sh /ws/tmp/eval 21 22 23 25 26
```

| ファイル | 内容 |
|---|---|
| `evaluate_sorting.sh` | 種ごとに環境を起動し、指示を送信して判定する。種ごとに 1 行の要約を出力する |
| `start_stack.sh`、`stop_stack.sh` | 仕分け環境（Gazebo と AI 版のノード）の起動と停止 |
| `watch_object_frames.py` | 物体の座標系（tf）を監視し、掴む物体のラベルが円柱付近に配信された回数を数える |
| `judge_positions.py` | Gazebo 上の位置から、箱への投入の成否と円柱の移動距離を判定する |

判定の基準は次のとおりです。

- 箱への投入: 物体の中心が、箱の内側（箱の中心から縦横 6 cm 以内）にあること
- ラベルの誤付与: 掴む物体のラベルの座標系が、円柱の中心から 4 cm 以内に配信されないこと

## 3. 注意事項

- 処理は、2026-10-28 の試験で使用した作業用のスクリプトを整理したものです。2026-11-14 に、整理後の版で仕分け試験（種 21、22）と語句の比較（種 24）を再実行し、記載の結果と一致することを確認しました
- ホストの GPU ドライバを入れ直した直後は、検出モデルの初回の読み込みと推論が非常に遅く（推論 1 回あたり約 2 秒）、仕分けが失敗しました。2 回目以降は通常の速度（約 55 ms）に戻ったため、ドライバの更新後は一度検出モデルを動作させてから試験します
- 起動した処理は、必ず `stop_stack.sh` で停止します。停止が不完全な状態で次の環境を起動すると、残った `robot_state_publisher` などの影響で、MoveIt が動作の実行を拒否し続けます
