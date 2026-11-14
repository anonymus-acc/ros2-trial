"""Gazebo 上の物体の位置から、各物体が指示どおりの箱に投入されたかと、円柱が移動していないかを判定する。

箱の位置と内寸は配置の設定ファイル（layout_shapes.yaml）から求め、物体の中心が箱の内側
（中心から内寸の半分以内）にあれば投入成功とする。円柱の初期位置は sim.launch.py のログから
読み取る。evaluate_sorting.sh から、仕分けの完了後に呼び出す。

    python3 judge_positions.py /ws/tmp/eval/seed_21/sim.log \\
        red_cuboid=left,red_cube=right,blue_cube=left,green_cuboid=right

Reads:
  - <sim.log>: 円柱の初期位置（「distractor_<名前>: x=... y=...」の行）
  - 配置の設定ファイル（--layout）
出力（標準出力）:
  - 物体ごとの判定（OK / NG）と箱の中心からのずれ、円柱ごとの移動距離、最終行に「RESULT 成功数/物体数」
"""

import argparse
from pathlib import Path
import re
import subprocess

from crane_sorter.layout import box_placements, load_layout

_DEFAULT_LAYOUT = Path('/ws/src/crane_sorter/config/layout_shapes.yaml')
_DISTRACTOR_LINE = re.compile(r'(distractor_\w+): x=([-0-9.]+) y=([-0-9.]+)')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('sim_log', type=Path)
    parser.add_argument('expected', help='物体名=箱名 をカンマ区切りで並べたもの')
    parser.add_argument('--layout', type=Path, default=_DEFAULT_LAYOUT)
    args = parser.parse_args()

    layout = load_layout(args.layout)
    boxes = {box.name: (box.x, box.y) for box in box_placements(layout)}
    shape = layout['box_shape']
    inner_half = (shape['outer_size'] - 2 * shape['wall_thickness']) / 2
    expected = dict(item.split('=') for item in args.expected.split(','))
    initial = _read_distractor_positions(args.sim_log)
    positions = _read_model_positions()

    succeeded = 0
    for label, box_name in expected.items():
        x, y = positions[f'object_{label}']
        box_x, box_y = boxes[box_name]
        inside = abs(x - box_x) <= inner_half and abs(y - box_y) <= inner_half
        succeeded += inside
        print(f'{label}: {"OK" if inside else "NG"} ({x:.3f}, {y:.3f}) '
              f'dx={x - box_x:+.3f} dy={y - box_y:+.3f}')
    for name, (x0, y0) in initial.items():
        x, y = positions[name]
        print(f'{name}: moved {((x - x0) ** 2 + (y - y0) ** 2) ** 0.5 * 100:.1f} cm')
    print(f'RESULT {succeeded}/{len(expected)}')


def _read_distractor_positions(sim_log: Path) -> dict[str, tuple[float, float]]:
    """sim.launch.py のログから、円柱のモデル名と初期位置 [m] を読み取る。"""
    positions = {}
    for line in sim_log.read_text(errors='replace').splitlines():
        match = _DISTRACTOR_LINE.search(line)
        if match:
            positions[match.group(1)] = (float(match.group(2)), float(match.group(3)))
    return positions


def _read_model_positions() -> dict[str, tuple[float, float]]:
    """Gazebo から、モデル名ごとの現在の水平位置 [m] を読み取る。

    腕は Gazebo の世界座標の原点の真上に置かれるため、水平位置は crane_plus_base から見た値と一致する。
    """
    output = subprocess.run(
        ['gz', 'topic', '-e', '-n', '1', '-t', '/world/default/pose/info'],
        capture_output=True, text=True, check=True, timeout=30,
    ).stdout
    positions: dict[str, tuple[float, float]] = {}
    name: str | None = None
    position: dict[str, float] = {}
    in_position = False
    for line in output.splitlines():
        text = line.strip()
        if text.startswith('name: "'):
            name, position = text.split('"')[1], {}
        elif text.startswith('position {'):
            in_position = True
        elif in_position and text == '}':
            in_position = False
            # モデルの中のリンクも同じ名前で続けて出ることがあるため、最初の 1 つのみ使用する
            if name and name not in positions:
                positions[name] = (position.get('x', 0.0), position.get('y', 0.0))
            name = None
        elif in_position and ':' in text:
            key, value = text.split(':', 1)
            position[key.strip()] = float(value)
    return positions


if __name__ == '__main__':
    main()
