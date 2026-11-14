"""物体検出ノードの検出結果画像（/object_detector/detections）を、一定間隔で PNG 形式で保存する。

レポートの図 3 は、動画撮影（tools/video/record_demo.sh）と並行して本スクリプトで保存した
画像から選定した。sorter.launch.py（detector:=ai）の起動後に、コンテナ内のシステムの
Python で実行する。Ctrl+C で終了する。

    python3 tools/report/save_detections.py /ws/tmp/video/take6_detections --period 1.5

Writes:
  - <出力先>/<受信時の UNIX 時刻>.png: 検出枠とラベルを描画したカメラ画像
"""

import argparse
from pathlib import Path
import time

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from sensor_msgs.msg import Image

_TOPIC = '/object_detector/detections'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('output_dir', type=Path)
    parser.add_argument('--period', type=float, default=1.5, help='保存間隔 [s]')
    parser.add_argument('--count', type=int, default=0, help='保存枚数の上限。0 は上限なし')
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Ctrl+C を KeyboardInterrupt として受け、保存枚数を表示してから終了するため、
    # rclpy のシグナル処理は使用しない
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = _DetectionSaver(args.output_dir, args.period, args.count)
    try:
        while not node.finished:
            rclpy.spin_once(node, timeout_sec=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        print(f'{node.saved} 枚を {args.output_dir} に保存しました')
        node.destroy_node()
        rclpy.try_shutdown()


class _DetectionSaver(Node):
    """検出結果画像を受信し、前回の保存から period 秒以上経過していれば保存する。"""

    def __init__(self, output_dir: Path, period: float, count: int) -> None:
        super().__init__('save_detections')
        self._output_dir = output_dir
        self._period = period
        self._count = count
        self._last_saved_at = -float('inf')
        self.saved = 0
        self.create_subscription(Image, _TOPIC, self._on_image, 10)

    @property
    def finished(self) -> bool:
        """保存枚数が上限に達していれば True を返す。"""
        return self._count > 0 and self.saved >= self._count

    def _on_image(self, message: Image) -> None:
        now = time.time()
        if self.finished or now - self._last_saved_at < self._period:
            return
        self._last_saved_at = now
        cv2.imwrite(str(self._output_dir / f'{now:.1f}.png'), _to_bgr_array(message))
        self.saved += 1


def _to_bgr_array(message: Image) -> np.ndarray:
    """sensor_msgs/Image（rgb8 または bgr8）を、OpenCV で保存できる BGR の配列に変換する。"""
    rows = np.frombuffer(message.data, dtype=np.uint8).reshape(message.height, message.step)
    # 行末に詰め物がある場合に備え、画像幅の分のみ使用する
    channels = rows[:, :message.width * 3].reshape(message.height, message.width, 3)
    if message.encoding == 'rgb8':
        channels = channels[:, :, ::-1]
    return np.ascontiguousarray(channels)


if __name__ == '__main__':
    main()
