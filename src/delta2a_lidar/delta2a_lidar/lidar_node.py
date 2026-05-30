"""
3iRobotics Delta-2A LiDAR ROS2 driver — protocol reverse-engineered from hex dump.

Packet format (168 bytes fixed):
  Byte  0-1 : AA 00            — sync header
  Byte  2   : A6               — CT (scan packet)
  Byte  3   : 01               — unknown, ignored
  Bytes 4-10: constant 7 bytes — device info, ignored
  Bytes 11-12: FSA big-endian  — first sample angle, degrees = val / 100.0
  Bytes 13-165: 51 × 3 bytes  — [dist_L dist_H qual], dist in mm (no shift)
  Bytes 166-167: checksum     — ignored for now

Baud rate: 230400
"""

import math
import subprocess
import serial
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan

HEADER_1    = 0xAA
HEADER_2    = 0x00
CT_SCAN     = 0xA6
PACKET_SIZE = 168
HEADER_SIZE = 13
NUM_SAMPLES = 51

BAUD_RATE   = 230400
SERIAL_PORT = '/dev/ttyUSB0'

RANGE_MIN   = 0.05   # metres
RANGE_MAX   = 8.0    # metres


def fsa_to_degrees(fsa_h: int, fsa_l: int) -> float:
    """Big-endian uint16 → degrees."""
    return ((fsa_h << 8) | fsa_l) / 100.0


class Delta2ANode(Node):

    def __init__(self):
        super().__init__('delta2a_lidar')

        self.declare_parameter('port',     SERIAL_PORT)
        self.declare_parameter('baud',     BAUD_RATE)
        self.declare_parameter('frame_id', 'laser')
        self.declare_parameter('topic',    'scan')

        port     = self.get_parameter('port').value
        baud     = self.get_parameter('baud').value
        self._frame_id = self.get_parameter('frame_id').value
        topic    = self.get_parameter('topic').value

        self._pub = self.create_publisher(LaserScan, topic, 10)

        # Accumulated full-revolution scan: angle_deg → dist_m
        self._scan: dict[float, float] = {}
        self._prev_fsa: float = -1.0

        # Configure port with stty first (same as what fixed the raw bytes issue)
        try:
            subprocess.run(
                ['stty', '-F', port, str(baud), 'raw', 'cs8', '-cstopb', '-parenb'],
                check=True
            )
            self.get_logger().info(f'stty configured {port}')
        except Exception as e:
            self.get_logger().warn(f'stty failed (may be ok): {e}')

        try:
            self._ser = serial.Serial(
                port=port,
                baudrate=baud,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1.0,
            )
            self.get_logger().info(f'Opened {port} @ {baud} baud')
        except serial.SerialException as e:
            self.get_logger().fatal(f'Cannot open port: {e}')
            raise SystemExit(1)

        self._buf = bytearray()
        self.create_timer(0.001, self._read_loop)

    # ------------------------------------------------------------------
    def _read_loop(self):
        try:
            waiting = self._ser.in_waiting
            if waiting:
                self._buf.extend(self._ser.read(waiting))
        except serial.SerialException as e:
            self.get_logger().error(f'Serial read error: {e}')
            return
        self._parse_buffer()

    # ------------------------------------------------------------------
    def _parse_buffer(self):
        buf = self._buf

        while True:
            # Find AA 00 header
            idx = -1
            for i in range(len(buf) - 1):
                if buf[i] == HEADER_1 and buf[i + 1] == HEADER_2:
                    idx = i
                    break

            if idx == -1:
                self._buf = bytearray(buf[-1:]) if buf else bytearray()
                return

            if idx > 0:
                buf = buf[idx:]

            # Need full packet
            if len(buf) < PACKET_SIZE:
                break

            ct = buf[2]

            if ct == CT_SCAN:
                self._process_packet(buf[:PACKET_SIZE])
                buf = buf[PACKET_SIZE:]
            else:
                # Unknown CT — log and skip this header
                self.get_logger().warn(
                    f'Unknown CT=0x{ct:02X} at buf[2], skipping header',
                    throttle_duration_sec=2.0
                )
                buf = buf[1:]  # skip one byte and re-search

        self._buf = bytearray(buf)

    # ------------------------------------------------------------------
    def _process_packet(self, pkt: bytearray):
        # FSA: big-endian uint16 at bytes 11-12
        fsa_deg = fsa_to_degrees(pkt[11], pkt[12])

        # Detect full revolution (angle wrapped back past 0°)
        if self._prev_fsa >= 0.0 and fsa_deg < self._prev_fsa - 10.0:
            self._publish_scan()
            self._scan.clear()

        self._prev_fsa = fsa_deg

        # Angle step per sample (~0.44° based on 22.5° span / 51 samples)
        angle_step = 22.5 / NUM_SAMPLES

        # Parse 51 samples: [dist_L dist_H qual] from byte 13
        for i in range(NUM_SAMPLES):
            base = HEADER_SIZE + i * 3
            dist_l = pkt[base]
            dist_h = pkt[base + 1]
            qual   = pkt[base + 2]

            if qual == 0:
                continue  # no return

            dist_mm = (dist_h << 8) | dist_l
            dist_m  = dist_mm / 1000.0

            if RANGE_MIN <= dist_m <= RANGE_MAX:
                angle_deg = fsa_deg + i * angle_step
                self._scan[angle_deg % 360.0] = dist_m

    # ------------------------------------------------------------------
    def _publish_scan(self):
        if len(self._scan) < 10:
            return

        angles_deg = sorted(self._scan.keys())
        n = len(angles_deg)

        angle_min_rad = math.radians(angles_deg[0])
        angle_max_rad = math.radians(angles_deg[-1])
        angle_inc     = (angle_max_rad - angle_min_rad) / max(n - 1, 1)

        ranges = [float(self._scan[a]) for a in angles_deg]

        msg = LaserScan()
        msg.header.stamp    = self.get_clock().now().to_msg()
        msg.header.frame_id = self._frame_id
        msg.angle_min       = angle_min_rad
        msg.angle_max       = angle_max_rad
        msg.angle_increment = angle_inc
        msg.time_increment  = 0.0
        msg.scan_time       = 1.0 / 6.5
        msg.range_min       = RANGE_MIN
        msg.range_max       = RANGE_MAX
        msg.ranges          = ranges

        self._pub.publish(msg)
        self.get_logger().info(
            f'Scan published: {n} points, FSA={self._prev_fsa:.1f}°',
            throttle_duration_sec=1.0
        )

    # ------------------------------------------------------------------
    def destroy_node(self):
        if hasattr(self, '_ser') and self._ser.is_open:
            self._ser.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = Delta2ANode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
