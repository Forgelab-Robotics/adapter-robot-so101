"""SO101 节点配置加载与校验。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from forge_robot import ActuatorSpec

SO101_ACTUATOR_SPECS = (
    ActuatorSpec(
        name="shoulder_pan",
        kind="revolute",
        min_position=-1.92,
        max_position=1.92,
    ),
    ActuatorSpec(
        name="shoulder_lift",
        kind="revolute",
        min_position=-1.75,
        max_position=1.75,
    ),
    ActuatorSpec(
        name="elbow_flex",
        kind="revolute",
        min_position=-1.69,
        max_position=1.69,
    ),
    ActuatorSpec(
        name="wrist_flex",
        kind="revolute",
        min_position=-1.66,
        max_position=1.66,
    ),
    ActuatorSpec(
        name="wrist_roll",
        kind="revolute",
        min_position=-2.74,
        max_position=2.84,
    ),
    ActuatorSpec(
        name="gripper",
        kind="revolute",
        min_position=-0.174,
        max_position=1.75,
    ),
)

# 与 driver 中关节顺序一致，固定不可配置
SO101_ACTUATOR_ORDER = [spec.name for spec in SO101_ACTUATOR_SPECS]


@dataclass
class SO101NodeConfig:
    """SO101 节点配置。"""

    port: str
    is_follower: bool
    debug: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SO101NodeConfig":
        """从字典解析配置。"""
        port = data.get("port", "/dev/ttyUSB0")
        is_follower = data.get("is_follower", True)
        debug = data.get("debug", False)
        return cls(
            port=port,
            is_follower=is_follower,
            debug=debug,
        )

    @classmethod
    def from_yaml_path(cls, path: str | Path) -> "SO101NodeConfig":
        """从 YAML 文件加载配置。"""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"配置文件不存在: {p}")
        with open(p, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            raise ValueError(f"配置文件为空: {p}")
        return cls.from_dict(data)


def load_config(
    config_path: str | Path | None = None,
    dataflow_config: dict[str, Any] | None = None,
) -> SO101NodeConfig:
    """
    加载配置，支持多种来源（优先级从高到低）：
    1. dataflow_config 中的 config_path 或内联 config
    2. config_path 参数
    3. 环境变量 SO101_NODE_CONFIG

    Args:
        config_path: 可选，YAML 配置文件路径
        dataflow_config: 可选，dora 节点 config 字段

    Returns:
        SO101NodeConfig
    """
    data: dict[str, Any] | None = None

    if dataflow_config:
        if "config" in dataflow_config:
            data = dataflow_config["config"]
        elif "config_path" in dataflow_config:
            return SO101NodeConfig.from_yaml_path(dataflow_config["config_path"])

    path = config_path
    if path is None and data is None:
        path = os.environ.get("SO101_NODE_CONFIG")

    if path:
        return SO101NodeConfig.from_yaml_path(path)

    if data:
        return SO101NodeConfig.from_dict(data)

    raise ValueError(
        "未找到配置。请设置 SO101_NODE_CONFIG 环境变量、"
        "或通过 --config 指定配置文件、或使用 dataflow config。"
    )
