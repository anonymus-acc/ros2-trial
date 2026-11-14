"""物体検出ノードが配信する物体の座標系（tf の object_<物体名>）を監視し、円柱付近での配信回数を数える。

掴む物体の名前が、把持対象外の円柱に誤って付与されていないかを確認するために使用する。
物体名ごとに、配信回数と、配信位置が円柱の中心から radius 以内であった回数を記録する。
evaluate_sorting.sh から起動し、SIGINT（Ctrl+C）で停止した時点で結果を書き出す。

    python3 watch_object_frames.py /ws/tmp/eval/seed_21/tf.json \\
        --cylinder 0.233,0.255 --cylinder 0.227,0.327

Writes:
  - <出力先>: {"counts": {物体名: 配信回数}, "near_cylinder": {物体名: 円柱付近での配信回数}}
"""

import argparse
import json
import math
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from rclpy.time import Time
from tf2_msgs.msg import TFMessage
from tf2_ros import Buffer, TransformException, TransformListener

_REFERENCE_FRAME = 'crane_plus_base'
_FRAME_PREFIX = 'object_'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('output', type=Path, help='結果の JSON の出力先')
    parser.add_argument(
        '--cylinder', action='append', default=[], type=_parse_position,
        help='円柱の中心位置 x,y [m]（crane_plus_base から見た値）。円柱の数だけ指定する',
    )
    parser.add_argument('--radius', type=float, default=0.04, help='円柱付近とみなす距離 [m]')
    args = parser.parse_args()

    # SIGINT を KeyboardInterrupt として受け、結果を書き出してから終了するため、
    # rclpy のシグナル処理は使用しない
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = _ObjectFrameWatcher(args.cylinder, args.radius)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        args.output.write_text(json.dumps(
            {'counts': node.counts, 'near_cylinder': node.near_cylinder}, ensure_ascii=False
        ))
        node.destroy_node()
        rclpy.try_shutdown()


class _ObjectFrameWatcher(Node):
    """/tf を購読し、物体の座標系が配信されるたびに位置を求めて集計する。"""

    def __init__(self, cylinders: list[tuple[float, float]], radius: float) -> None:
        super().__init__('watch_object_frames')
        self._cylinders = cylinders
        self._radius = radius
        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)
        # 同じ配信を重複して数えないよう、座標系名と時刻の組を記録する
        self._seen: set[tuple[str, int, int]] = set()
        self.counts: dict[str, int] = {}
        self.near_cylinder: dict[str, int] = {}
        self.create_subscription(TFMessage, '/tf', self._on_tf, 100)

    def _on_tf(self, message: TFMessage) -> None:
        for transform in message.transforms:
            frame = transform.child_frame_id
            if not frame.startswith(_FRAME_PREFIX):
                continue
            key = (frame, transform.header.stamp.sec, transform.header.stamp.nanosec)
            if key in self._seen:
                continue
            self._seen.add(key)
            try:
                pose = self._tf_buffer.lookup_transform(_REFERENCE_FRAME, frame, Time())
            except TransformException:
                continue
            x, y = pose.transform.translation.x, pose.transform.translation.y
            label = frame[len(_FRAME_PREFIX):]
            self.counts[label] = self.counts.get(label, 0) + 1
            if any(math.hypot(x - cx, y - cy) < self._radius for cx, cy in self._cylinders):
                self.near_cylinder[label] = self.near_cylinder.get(label, 0) + 1


def _parse_position(text: str) -> tuple[float, float]:
    """「x,y」形式の文字列を、位置 (x, y) に変換する。"""
    x, y = text.split(',')
    return float(x), float(y)


if __name__ == '__main__':
    main()
