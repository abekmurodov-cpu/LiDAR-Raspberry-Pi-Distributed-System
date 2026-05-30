#!/bin/bash
set -e
source "/opt/ros/jazzy/setup.bash"
if [ -f "/home/azim/jazzy_ws/install/setup.bash" ]; then
  source "/home/azim/jazzy_ws/install/setup.bash"
fi
exec "$@"
