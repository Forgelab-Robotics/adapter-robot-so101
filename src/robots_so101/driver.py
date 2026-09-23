"""SO101 机械臂硬件驱动，实现 forge_robot.BaseRobotDriver 协议。"""

from __future__ import annotations

import math

from forge_common import get_logger
from forge_msgs import JointCommand, JointState
from forge_robot import (
    BaseRobotDriver,
    clip_and_validate_position_command,
    specs_by_name,
)

from robots_so101.config import SO101_ACTUATOR_ORDER, SO101_ACTUATOR_SPECS
from robots_so101.feetech_bus import (
    POSITION_CENTER,
    POSITION_STEPS,
    TORQUE_ENABLE_ADDR,
    FeetechBus,
)

logger = get_logger(__name__)

# 执行器名称 -> 舵机 ID（1～6）
NAME_TO_ID = {name: i + 1 for i, name in enumerate(SO101_ACTUATOR_ORDER)}

_ACTUATOR_SPECS_DICT = specs_by_name(SO101_ACTUATOR_SPECS)


def _rad_to_raw(rad: float) -> int:
    """弧度转 STS raw：360° = 4096 份，中位 2047。"""
    deg = math.degrees(rad)
    raw = int(deg / 360.0 * POSITION_STEPS + POSITION_CENTER)
    return max(0, min(4095, raw))


def _raw_to_rad(raw: int) -> float:
    """STS raw 转弧度。"""
    deg = (raw - POSITION_CENTER) * 360.0 / POSITION_STEPS
    return math.radians(deg)


class SO101Driver(BaseRobotDriver):
    """
    SO101 机械臂硬件驱动。

    通过串口与 Feetech STS 舵机通信。单位：关节与夹爪均为弧度。
    """

    @property
    def joint_order(self) -> list[str]:
        return list(SO101_ACTUATOR_ORDER)

    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        is_follower: bool = True,
        auto_connect: bool = True,
    ):
        self.port = port
        self.is_follower = is_follower
        self.bus: FeetechBus | None = None

        # 获取舵机 ID [1, 2, 3, 4, 5, 6] 用于后续设计调用
        self.motor_ids = [NAME_TO_ID[name] for name in SO101_ACTUATOR_ORDER]

        if auto_connect:
            self.connect()

    def connect(self) -> None:
        if self.bus is not None and self.bus.is_connected:
            logger.warning("Robot is already connected.")
            return

        self.bus = FeetechBus(port=self.port)
        logger.info("Connecting to SO101 at port %s...", self.port)
        self.bus.connect()
        if not self.bus.is_connected:
            raise RuntimeError("Failed to connect to the robot.")
        logger.info("Successfully connected to SO101.")

        if self.is_follower:
            logger.info("Slave: Torque control on.")
            self.set_torque(True)
        else:
            logger.info("Master: Torque control close.")
            self.set_torque(False)

    def set_torque(self, enable: bool) -> None:
        """开启或关闭所有舵机的扭矩输出。"""
        if self.bus and self.bus.is_connected:
            for mid in self.motor_ids:
                self.bus.write_register(mid, TORQUE_ENABLE_ADDR, 1 if enable else 0) # STS3215舵机扭矩开启/关闭: 地址 0x28 (0: 关闭, 1: 开启)

    def disconnect(self) -> None:
        if self.bus is None:
            logger.warning("Robot is not connected.")
            return
        logger.info("Disconnecting from SO101...")
        self.bus.disconnect()
        self.bus = None
        logger.info("Disconnected from SO101.")

    def get_state(self) -> JointState:
        """从硬件读取状态，转为 JointState（弧度）。"""
        if self.bus is None or not self.bus.is_connected:
            raise RuntimeError("Robot is not connected. Call connect() first.")

        motor_ids = [NAME_TO_ID[name] for name in SO101_ACTUATOR_ORDER]
        raw_positions = self.bus.sync_read_positions(motor_ids)

        positions = []
        for name in SO101_ACTUATOR_ORDER:
            mid = NAME_TO_ID[name]
            raw = raw_positions.get(mid, 0)
            positions.append(_raw_to_rad(raw))
        return JointState(name=self.joint_order, position=positions)

    def set_command(self, command: JointCommand) -> None:
        """下发 JointCommand（弧度），内部会裁剪到限位。"""
        if self.bus is None or not self.bus.is_connected:
            raise RuntimeError("Robot is not connected. Call connect() first.")

        if getattr(command, "mode", "position") != "position":
            raise ValueError("SO101 requires JointCommand mode='position'")
        safe_command = clip_and_validate_position_command(command, _ACTUATOR_SPECS_DICT)
        if not safe_command.position:
            raise ValueError("SO101 requires a position JointCommand")
        positions = dict(zip(safe_command.name, safe_command.position, strict=True))
        id_to_raw = {
            NAME_TO_ID[name]: _rad_to_raw(rad)
            for name, rad in positions.items()
        }
        self.bus.sync_write_positions(id_to_raw)
