# delta2a_lidar — ROS2 Driver for 3iRobotics Delta-2A LiDAR

A ROS2 (Jazzy Jalisco) driver for the **3iRobotics Delta-2A** triangulation LiDAR.  
Publishes standard `sensor_msgs/LaserScan` messages compatible with Nav2, slam_toolbox, and RViz2.

> **Why this exists:** No official ROS2 driver exists for the Delta-2A. This driver was written from scratch by reverse-engineering the raw serial protocol from hex dumps of the device's actual output.

---

## Hardware

| Property | Value |
|---|---|
| Model | 3iRobotics Delta-2A |
| Type | Rotating triangulation LiDAR |
| Range | 0.05 m – 8.0 m |
| Scan rate | ~6–7 Hz |
| Points per scan | ~630 |
| Interface | USB-Serial (230400 baud, 8N1) |
| Scan angle | 360° |

---

## Requirements

- ROS2 **Jazzy Jalisco** (tested); should work on Humble/Iron with minor changes
- Python 3.10+
- `pyserial` Python package
- Docker (optional but recommended — full setup included)

---

## Repository Structure

```
delta2a_lidar/          ← ROS2 Python package
├── delta2a_lidar/
│   ├── __init__.py
│   └── lidar_node.py   ← main driver node
├── launch/
│   └── lidar.launch.py
├── resource/
│   └── delta2a_lidar
├── package.xml
├── setup.py
└── setup.cfg

docker/                 ← Docker setup (optional)
├── Dockerfile
├── docker-compose.yml
└── entrypoint.sh
```

---

## Quick Start (Docker — recommended)

This is the easiest path. Everything is pre-configured.

### 1. Clone the repo

```bash
git clone https://github.com/krranky/delta2a_lidar_ros2.git
cd delta2a_lidar_ros2
```

### 2. Connect the LiDAR and find the port

```bash
ls /dev/ttyUSB*
# Usually /dev/ttyUSB0
```

### 3. Allow X11 forwarding (for RViz2)

```bash
xhost +local:docker
```

### 4. Build and start the container

```bash
cd docker
docker compose build
docker compose up -d
```

### 5. Run the LiDAR node

```bash
docker compose exec ros2_jazzy bash
ros2 launch delta2a_lidar lidar.launch.py
```

### 6. Open RViz2 (second terminal)

```bash
docker compose exec ros2_jazzy bash
rviz2
```

In RViz2:
- Set **Fixed Frame** → `laser`
- Click **Add** → **By topic** → `/scan` → **LaserScan**
- Set **Color Transformer** → `FlatColor`, color white

---

## Quick Start (Native ROS2, no Docker)

### 1. Install dependencies

```bash
sudo apt install ros-jazzy-rviz2
pip3 install pyserial
```

### 2. Clone into your workspace

```bash
cd ~/your_ros2_ws/src
git clone https://github.com/krranky/delta2a_lidar_ros2.git
cd ..
colcon build --packages-select delta2a_lidar
source install/setup.bash
```

### 3. Give yourself serial port access

```bash
sudo usermod -aG dialout $USER
# Log out and back in, then:
sudo stty -F /dev/ttyUSB0 230400 raw cs8 -cstopb -parenb
```

### 4. Launch

```bash
ros2 launch delta2a_lidar lidar.launch.py
```

---

## Parameters

All parameters can be set in the launch file or via `--ros-args`:

| Parameter | Default | Description |
|---|---|---|
| `port` | `/dev/ttyUSB0` | Serial port of the LiDAR |
| `baud` | `230400` | Baud rate |
| `frame_id` | `laser` | TF frame name in LaserScan header |
| `topic` | `scan` | Published topic name |

Example with custom port:

```bash
ros2 run delta2a_lidar lidar_node \
    --ros-args -p port:=/dev/ttyUSB1 -p frame_id:=base_scan
```

---

## Published Topics

| Topic | Type | Description |
|---|---|---|
| `/scan` | `sensor_msgs/msg/LaserScan` | 360° laser scan, ~6–7 Hz |

---

## Protocol Notes

The Delta-2A uses a **proprietary binary serial protocol** — not the standard RPLIDAR protocol.

```
Packet structure (168 bytes fixed):

  Byte 00-01 : AA 00          — sync header
  Byte 02    : A6             — content type (scan packet)
  Byte 03-10 : device info    — ignored
  Byte 11-12 : FSA (uint16 BE)— first sample angle = value / 100.0 degrees
  Byte 13-165: 51 × 3 bytes  — [dist_L, dist_H, quality]
                                dist_mm = (dist_H << 8) | dist_L
                                quality = 0 means no return (discard)
  Byte 166-167: checksum     — currently not validated

Baud rate : 230400
Packets/revolution : 16
Angular span/packet: 22.5°
Samples/packet     : 51
```

A secondary packet type `CT=0xA3` (speed/status) is also emitted by the hardware and silently ignored by this driver.

---

## Integration with Other Packages

Once the node is running and `/scan` is publishing, plug it into any standard ROS2 stack:

### SLAM (mapping)

```bash
sudo apt install ros-jazzy-slam-toolbox
ros2 launch slam_toolbox online_async_launch.py
```

### Navigation (Nav2)

```bash
sudo apt install ros-jazzy-nav2-bringup
```
Point your Nav2 costmap config at `topic: /scan` and `frame: laser`.

### Verify data

```bash
ros2 topic hz /scan          # should show ~6–7 Hz
ros2 topic echo /scan --no-arr   # shows message headers
```

---

## Troubleshooting

**No data / node starts but nothing publishes**

The port must be configured before opening:
```bash
sudo stty -F /dev/ttyUSB0 230400 raw cs8 -cstopb -parenb
```
This is done automatically by the node, but if your system resets port settings, run it manually first.

**Permission denied on /dev/ttyUSB0**
```bash
sudo chmod 666 /dev/ttyUSB0
# Or permanently:
sudo usermod -aG dialout $USER
```

**RViz shows no points but Status is OK**

Set **Color Transformer** to `FlatColor` — without it, points are black on black and invisible.

**Wrong port**
```bash
dmesg | grep tty   # find which port the LiDAR was assigned
```

**RViz won't open (display error)**
```bash
xhost +local:docker   # run on HOST before starting container
```

---

## Tested On

| OS | ROS2 | Status |
|---|---|---|
| Ubuntu 24.04 (Docker) | Jazzy Jalisco | ✅ Working |

---

## Related Resources

- [3iRobotics Delta-2B SDK (official, ROS1)](https://github.com/CWRU-AutonomousVehiclesLab/Delta-2B-Lidar-SDK) — contains the original Delta-2A C SDK and protocol reference
- [jeroenvervaeke/delta_2a_lidar](https://github.com/jeroenvervaeke/delta_2a_lidar) — Rust implementation, useful for protocol cross-reference
- [kaiaai/awesome-2d-lidars](https://github.com/kaiaai/awesome-2d-lidars) — good overview of 2D LiDAR options

---

## License

MIT License — free to use, modify, and distribute.

---

## Author

**Azimbek Mustafokulov** — [@krranky](https://github.com/krranky)  
Mechanical engineering student, Tashkent  
Building robots in free time 🤖
