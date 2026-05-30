from setuptools import setup
import os
from glob import glob

package_name = 'delta2a_lidar'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='azim',
    maintainer_email='user@example.com',
    description='ROS2 driver for 3iRobotics Delta-2A LiDAR',
    license='MIT',
    entry_points={
        'console_scripts': [
            'lidar_node = delta2a_lidar.lidar_node:main',
        ],
    },
)
