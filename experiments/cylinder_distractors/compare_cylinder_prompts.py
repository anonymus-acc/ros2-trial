"""円柱の検出用語句の候補ごとに、OWLv2 が円柱に付ける得点と、ラベルの割り当て結果を比較する。

AI 版の説明（docs/design/261027_ai_detector.md）の 10.3 の表と、レポートの 4.3 の語句選定
（round block を採用）は、本スクリプトの出力に基づく。入力は capture_images.sh で保存した画像。
コンテナ内で、仮想環境の Python で実行する（GPU を使用する）。

    $AI_VENV/bin/python experiments/cylinder_distractors/compare_cylinder_prompts.py \\
        /ws/tmp/cylinder_images

円柱か否かは、画像中の位置で判定する。layout_shapes.yaml の distractor_area は腕の左奥にあり、
円柱は画像の左端付近（枠の中心の横方向の画素位置が 200 未満）に、4 物体はそれより右に写る。
配置の範囲を変更した場合は、--cylinder-max-u を見直す必要がある。

Reads:
  - <画像の場所>/seed_*.png
出力（標準出力）: 語句ごと・画像ごとに 1 行
  - cylinder: 円柱に付いたラベルの得点（赤 / 青。付かなかった場合は -）
  - steal: 円柱の枠における、4 物体のラベルの得点の最大値（円柱が 4 物体のラベルを奪う強さ）
  - wrong: 位置の判定と合わないラベル（円柱のラベルが右側に、4 物体のラベルが左側に付いたもの）
  - missing: どの枠にも付かなかったラベル
"""

import argparse
from pathlib import Path

from crane_sorter.detectors import assign_labels, Candidate, Owlv2Detector
import cv2
import numpy as np

# 4 物体の検出用語句。object_detector.yaml と同じもの
_OBJECT_PROMPTS = {
    'red_cube': 'red square block',
    'red_cuboid': 'red long block',
    'blue_cube': 'blue square block',
    'green_cuboid': 'green long block',
}
_CYLINDER_COLORS = ('red', 'blue')
# 円柱の語句の候補。{} に色の英単語が入る
_DEFAULT_VARIANTS = (
    '{} cylinder', '{} round block', '{} circle', '{} can', '{} round object', '{} disc',
    '{} cylinder block',
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('image_dir', type=Path)
    parser.add_argument('--variants', nargs='+', default=list(_DEFAULT_VARIANTS),
                        help='円柱の語句の候補。{} に色の英単語が入る')
    parser.add_argument('--score-threshold', type=float, default=0.1,
                        help='ラベルの割り当てに使用する得点の下限（object_detector.yaml と同じ値）')
    parser.add_argument('--cylinder-max-u', type=float, default=200.0,
                        help='円柱とみなす、枠の中心の横方向の画素位置の上限')
    args = parser.parse_args()

    images = [
        (path.stem, cv2.cvtColor(cv2.imread(str(path)), cv2.COLOR_BGR2RGB))
        for path in sorted(args.image_dir.glob('seed_*.png'))
    ]
    for variant in args.variants:
        prompts = dict(_OBJECT_PROMPTS)
        prompts.update({f'{color}_cylinder': variant.format(color) for color in _CYLINDER_COLORS})
        detector = Owlv2Detector(prompts, args.score_threshold, 'cuda', True)
        print(f'== {variant}')
        for name, rgb_image in images:
            print(f'{name}: {_summarize(detector, rgb_image, args)}')
        del detector


def _summarize(detector: Owlv2Detector, rgb_image: np.ndarray, args: argparse.Namespace) -> str:
    """画像 1 枚について、円柱の得点、ラベルを奪う強さ、割り当ての誤りと欠落を 1 行にまとめる。"""
    labels = detector.labels
    candidates = detector.candidates(rgb_image)
    assignment = assign_labels(candidates, labels, args.score_threshold)
    on_left = [_center_u(candidate) < args.cylinder_max_u for candidate in candidates]

    wrong = [
        label for label, index in assignment.items()
        if label.endswith('_cylinder') != on_left[index]
    ]
    missing = [label for label in labels if label not in assignment]
    cylinder_scores = [
        f'{candidates[assignment[label]].scores[labels.index(label)]:.2f}'
        if label in assignment else '-'
        for label in labels if label.endswith('_cylinder')
    ]
    object_indices = [
        index for index, label in enumerate(labels) if not label.endswith('_cylinder')
    ]
    steal = max(
        (
            candidate.scores[index]
            for candidate, left in zip(candidates, on_left) if left
            for index in object_indices
        ),
        default=0.0,
    )
    return (f'cylinder={"/".join(cylinder_scores)} steal={steal:.2f} '
            f'wrong={wrong} missing={missing}')


def _center_u(candidate: Candidate) -> float:
    """枠の中心の横方向の画素位置を返す。"""
    left, _, right, _ = candidate.box
    return (left + right) / 2


if __name__ == '__main__':
    main()
