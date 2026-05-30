FROM ros:jazzy-ros-base

ARG USERNAME=azim
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-pip \
    git sudo \
    ros-jazzy-rviz2 \
    ros-jazzy-rviz-default-plugins \
    && pip3 install pyserial --break-system-packages \
    && rm -rf /var/lib/apt/lists/*

RUN if getent passwd $USER_UID; then \
        USER_OLD=$(getent passwd $USER_UID | cut -d: -f1); \
        usermod -l $USERNAME $USER_OLD; \
        groupmod -n $USERNAME $(getent group $USER_GID | cut -d: -f1); \
        usermod -d /home/$USERNAME -m $USERNAME; \
    else \
        groupadd --gid $USER_GID $USERNAME; \
        useradd --uid $USER_UID --gid $USER_GID -m $USERNAME; \
    fi \
    && echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

USER $USERNAME
WORKDIR /home/$USERNAME/jazzy_ws

# context is ~/jazzy_ws, so src/ is directly visible
COPY --chown=$USERNAME:$USERNAME src ./src

RUN . /opt/ros/jazzy/setup.sh \
    && colcon build

RUN echo "source /opt/ros/jazzy/setup.bash" >> /home/$USERNAME/.bashrc \
    && echo "source /home/$USERNAME/jazzy_ws/install/setup.bash" >> /home/$USERNAME/.bashrc

# entrypoint is inside docker/ subfolder relative to context
COPY docker/entrypoint.sh /entrypoint.sh
USER root
RUN chmod +x /entrypoint.sh
USER $USERNAME

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
