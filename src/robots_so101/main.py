#!/usr/bin/env python3
"""SO101 统一入口：dora 节点与串口工具。"""

from __future__ import annotations

import sys
import time

import typer
from forge_common import get_logger

logger = get_logger(__name__)

app = typer.Typer(
    name="robots_so101",
    help="SO101 机械臂 dora 节点与设备工具。无子命令时默认运行节点；可用 run / test / list-devices / activate-devices。",
    no_args_is_help=False,
)


def _resolve_port_and_follower(port: str | None, config: str | None) -> tuple[str, bool]:
    """--port 优先；否则读取配置；都没有时使用 ttyACM0。"""
    from robots_so101.config import load_config

    if config is not None:
        c = load_config(config_path=config)
        return (port if port is not None else c.port, c.is_follower)
    try:
        c = load_config()
    except Exception:
        return port or "/dev/ttyACM0", True
    return (port if port is not None else c.port, c.is_follower)


def _run_node(config_path: str | None) -> int:
    """运行 SO101 dora 节点。"""
    from forge_robot.node_runner import run_dora_robot_node

    from robots_so101.config import load_config
    from robots_so101.driver import SO101Driver

    config = load_config(config_path=config_path)
    driver = SO101Driver(
        port=config.port,
        is_follower=config.is_follower,
        auto_connect=True,
    )

    last_time = time.time()
    event_count = 0
    original_read = driver.get_state

    def monitored_read(*args: object, **kwargs: object) -> object:
        nonlocal last_time, event_count

        result = original_read(*args, **kwargs)
        try:
            event_count += 1
            now = time.time()
            if now - last_time >= 1.0:
                hz = event_count / (now - last_time)
                role = "Follower" if config.is_follower else "Leader"
                logger.info(f"[{role}] 运行频率: {hz:.2f} Hz")
                event_count = 0
                last_time = now
        except Exception as e:
            logger.error(f"监控逻辑出错: {e}")

        return result

    driver.get_state = monitored_read

    return run_dora_robot_node(
        driver,
        joint_order=driver.joint_order,
        is_follower=bool(getattr(config, "is_follower", True)),
        debug=bool(getattr(config, "debug", False)),
    )


@app.callback(invoke_without_command=True)
def _main(
    ctx: typer.Context,
    config: str | None = typer.Option(None, "--config", help="YAML 配置文件路径"),
) -> None:
    """无子命令时默认运行 SO101 dora 节点。"""
    if ctx.invoked_subcommand is not None:
        return
    sys.exit(_run_node(config_path=config))


@app.command()
def run(
    config: str | None = typer.Option(None, "--config", help="YAML 配置文件路径"),
) -> None:
    """运行 SO101 dora 节点。"""
    sys.exit(_run_node(config_path=config))


@app.command("test")
def test(
    port: str | None = typer.Option(
        None,
        "--port",
        "-p",
        help="串口路径；未指定时从 --config 或 SO101_NODE_CONFIG 读取，否则 /dev/ttyACM0",
    ),
    config: str | None = typer.Option(None, "--config", help="YAML 配置（port、is_follower）"),
    duration: float = typer.Option(15.0, "-d", "--duration", help="运行秒数"),
    open_position: float = typer.Option(1.0, "--open", help="夹爪张开位置（弧度）"),
    close_position: float = typer.Option(0.0, "--close", help="夹爪闭合位置（弧度）"),
) -> None:
    """循环夹爪开合，用于确认串口与机械臂对应关系。"""
    from forge_msgs import JointCommand

    from robots_so101.config import SO101_ACTUATOR_ORDER
    from robots_so101.driver import SO101Driver

    resolved_port, _ = _resolve_port_and_follower(port, config)
    driver = SO101Driver(port=resolved_port, is_follower=True, auto_connect=True)
    try:
        state = driver.get_state()
        base_values = dict(zip(state.name, state.position, strict=False))

        start = time.monotonic()
        last_phase: int | None = None
        while (time.monotonic() - start) < duration:
            phase = int((time.monotonic() - start) / 0.75) % 2
            if phase != last_phase:
                target = open_position if phase else close_position
                positions = [
                    target if name == "gripper" else base_values.get(name, 0.0)
                    for name in SO101_ACTUATOR_ORDER
                ]
                driver.set_command(
                    JointCommand(name=list(SO101_ACTUATOR_ORDER), position=positions)
                )
                last_phase = phase
            time.sleep(0.02)
    finally:
        driver.disconnect()


@app.command("list-devices")
def list_devices(
    json_output: bool = typer.Option(True, "--json/--no-json", help="输出 JSON"),
) -> None:
    """列出 SO101 串口设备，便于确认连接的 device。"""
    from robots_so101.device_tools import cmd_list_devices

    sys.exit(cmd_list_devices(use_json=json_output))


@app.command("activate-devices")
def activate_devices(
    json_output: bool = typer.Option(True, "--json/--no-json", help="输出 JSON"),
) -> None:
    """
    对匹配到的全部串口设备临时 chmod 666（Linux，需 pkexec）。

    长期建议 Linux：`sudo usermod -aG dialout $USER` 后重新登录。
    """
    from robots_so101.device_tools import cmd_activate_devices

    sys.exit(cmd_activate_devices(use_json=json_output))


def main() -> None:
    app()


if __name__ == "__main__":
    main()
