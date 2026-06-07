# LiDAR-Raspberry-Pi-Distributed-System
How to check lidar working with Raspberry pi using your laptop on the same channel with RPI




This repository provides a step-by-step guide on how to build a fully distributed, autonomous ROS 2 robot using a **Raspberry Pi 4/5**, and a **Delta-2A LiDAR**.

---

## LiDAR + Raspberry Pi Distributed System
In this phase, we establish a **Distributed ROS 2 Architecture**. The heavy hardware reading is done on an edge device (Raspberry Pi), which wirelessly streams sensor data to a powerful base station (Ubuntu Laptop) for visualization.

### 🛠️ Hardware Architecture
To prevent motor "brownouts" and voltage drops from crashing the system, we separated the power sources:
* **The Brains (Raspberry Pi & LiDAR):** Powered by a standard 2-port USB Phone Power Bank (5V / 2.1A+).
  * *Port 1:* Powers the Raspberry Pi.
  * *Port 2:* Plugs into the LiDAR's secondary "Power-Only" USB cable (ensures the laser spins at maximum speed without draining the Pi).
* **The Data Connection:** The LiDAR's primary Data USB cable plugs into the Raspberry Pi (preferably a blue USB 3.0 port).

---

### 🖥️ Step 1: The Edge Server (Raspberry Pi Setup)
The Raspberry Pi runs **Ubuntu 24.04** and uses an isolated Docker container to keep the ROS 2 Jazzy environment clean. 

Huge thanks to [krranky's Delta-2A repository](https://github.com/krranky/delta2a_lidar_ros2.git) which provided the baseline Docker driver for this specific LiDAR.

**1. Give the Pi permission to read the USB hardware:**
```bash
sudo chmod 777 /dev/ttyUSB0
```



2. Download the LiDAR Driver & Docker Environment:

```bash
cd ~
git clone https://github.com/abekmurodov-cpu/LiDAR-Raspberry-Pi-Distributed-System.git
cd delta2a_lidar_ros2/docker
```

3. Configure the ROS 2 Network (DDS):
We must put the robot on a specific network channel so it can talk to the laptop. Open the configuration file:

```bash
nano docker-compose.yml
```

Add the ROS_DOMAIN_ID under the environment section so it looks like this:

```
environment:
      - DISPLAY=${DISPLAY}
      - QT_X11_NO_MITSHM=1
      - ROS_DOMAIN_ID=42
```

(Save and exit using Ctrl+O, Enter, Ctrl+X).


4. Build and Run the Driver:

```bash
docker compose build
docker compose up -d
docker compose exec ros2_jazzy bash
```

5. Launch the Laser:
Once inside the Docker container, start the LiDAR node:
```bash
ros2 launch delta2a_lidar lidar.launch.py
```

(When you see [WARN] Unknown CT=0xA3, the LiDAR is successfully streaming data to the Wi-Fi!)
----------------------------------------------------------------------------------------------------------------------

### 💻 Step 2: The Base Station (Ubuntu Laptop Setup)
The laptop must be connected to the **exact same Wi-Fi network** as the Raspberry Pi.

#### ⚙️ Pre-requisite: Install ROS 2 (Automated Method)
If you do not have ROS 2 installed on your laptop, run this automated script. It will automatically detect your Ubuntu version (22.04, 24.04, or 26.04) and install the correct ROS 2 Desktop package (Humble, Jazzy, or Lyrical) along with RViz2:

```bash
# 1. Setup security keys and repositories
sudo apt update && sudo apt install curl gnupg lsb-release software-properties-common -y
sudo add-apt-repository universe -y
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(source /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
sudo apt update

# 2. Auto-detect the correct ROS 2 version and install it
export ROS_PKG=$(apt-cache search ros- | grep -oP '^ros-[a-z]+-desktop(?=\s)' | head -n 1)
echo "Installing: $ROS_PKG"
sudo apt install $ROS_PKG -y
```

1. Tune into the Robot's Network Channel:
Open a new terminal on your laptop and run:

```bash
source /opt/ros/*/setup.bash
export ROS_DOMAIN_ID=42
```

2. Verify the Wireless Connection:

```bash
ros2 topic list
```

(If you see /scan in the output, your laptop is successfully receiving the LiDAR data wirelessly!)
---------------------------------------------------------------------------------------------------------------------

### 👁️ Step 3: RViz2 Visualization & Bug Fixes
Now we visualize the physical room in 3D using RViz2.
1. Launch RViz2:

```bash
rviz2
```

2. Configure the View:

 By default, RViz2 will be blank or show a warning. Follow these exact steps to fix it:
 
 * 1.In the top-left, change Fixed Frame from map to laser.
 * 2.In the bottom-left, click Add -> By topic -> /scan -> LaserScan.

3. The "QoS Mismatch" Fix (Missing Dots):

 Because LiDARs send data so fast, they use a "Best Effort" network policy. RViz2 defaults to "Reliable". We must match them:
 
 * 1.Expand the LaserScan menu on the left panel.
 * 2.Expand QoS Policies.
 * 3.Change Reliability from Reliable to Best Effort.
 (The red laser dots will instantly appear on your screen!)

4. Make it look professional:

 * 1.Change Size (m) to 0.05 to make the dots thicker.
 * 2.Change Style to Points.
 * 3.Change Color Transformer to AxisColor for a dynamic heat-map look.

---------------------------------------------------------------------------------------------------------------------

### 💾 Step 4: Save your Configuration

To avoid reconfiguring RViz2 every time you reboot:
 
 * 1.In RViz2, click File -> Save Config As.
 * 2.Save it to your home folder as lidar_map.rviz.
 
To quick-launch this setup later, simply run:

```bash
source /opt/ros/*/setup.bash
export ROS_DOMAIN_ID=42
rviz2 -d ~/lidar_map.rviz
```

