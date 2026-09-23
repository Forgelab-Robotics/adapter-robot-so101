"""SO101 设备 CLI 实现（list / activate），JSON 格式遵循 forge_robot.device_tools。"""

from __future__ import annotations

import glob
import os
import platform
import shlex
import stat
import subprocess
import sys

from forge_robot.device_tools import (
    address_info,
    error_result,
    ok_result,
    print_json_result,
)


def get_device_names() -> list[str]:
    """查询并返回 SO101 可用的 ttyACM* 设备路径列表。"""
    try:
        import serial.tools.list_ports

        ports = list(serial.tools.list_ports.comports())
    except Exception:
        return []
    return [
        p.device
        for p in ports
        if os.path.basename(p.device).startswith("ttyACM")
    ]


def _list_serial_devices() -> tuple[list[dict], str | None]:
    """返回 (devices, error_message)。error_message 非空表示查询失败。"""
    try:
        import serial.tools.list_ports

        ports = list(serial.tools.list_ports.comports())
    except Exception as e:
        return [], str(e)

    devices: list[dict] = []
    for p in ports:
        if not os.path.basename(p.device).startswith("ttyACM"):
            continue
        try:
            st = os.stat(p.device)
            mode_bits = st.st_mode & 0o777
            accessible = stat.S_ISCHR(st.st_mode) and mode_bits == 0o666
        except OSError:
            accessible = False
        devices.append(
            address_info(
                name=p.device,
                address=p.hwid or p.description or "",
                status=accessible,
            )
        )
    return devices, None


def _print_list_devices_text(devices: list[dict]) -> None:
    if not devices:
        print("  (无串口)")
        return
    for d in devices:
        flag = "666" if d.get("status") else "NO"
        print(f"  {d['name']} {d['address']} {flag}")


def cmd_list_devices(*, use_json: bool = True) -> int:
    """列出 SO101 串口设备（ttyACM*）。"""
    devices, err = _list_serial_devices()
    if err is not None:
        result = error_result(err, devices=[])
        if use_json:
            print_json_result(result)
        else:
            print(f"Error: {err}", file=sys.stderr)
        return 1

    result = ok_result(devices=devices)
    if use_json:
        print_json_result(result)
    else:
        _print_list_devices_text(devices)
    return 0


def _all_serial_device_paths() -> list[str]:
    """匹配 ttyACM* 设备路径（与 list-devices 一致）。"""
    return sorted(glob.glob("/dev/ttyACM*"))


def cmd_activate_devices(*, use_json: bool = True) -> int:
    """
    对匹配到的全部串口设备临时放宽权限（通常为 chmod 666）。

    Linux 长期建议：`sudo usermod -aG dialout $USER` 后重新登录。
    需要 pkexec；无 pkexec 时可手动 `sudo chmod 666 /dev/ttyACM0`。
    """
    paths = _all_serial_device_paths()
    if not paths:
        msg = "未找到匹配的串口设备（如 /dev/ttyACM*）。"
        result = error_result(msg, devices=[])
        if use_json:
            print_json_result(result)
        else:
            print(msg, file=sys.stderr)
        return 2

    system = platform.system()
    if system != "Linux":
        msg = (
            f"当前系统为 {system}，activate-devices 主要针对 Linux /dev/ttyACM*。"
            "macOS 上串口多为 /dev/cu.*，一般可直接访问；若仍 Permission denied，"
            "请在「系统设置 → 隐私」中检查串口权限，或使用 sudo chmod 666 <设备>。"
        )
        result = error_result(
            msg,
            devices=[address_info(name=p, status=False) for p in paths],
        )
        if use_json:
            print_json_result(result)
        else:
            print(msg, file=sys.stderr)
        return 1

    quoted = " ".join(shlex.quote(d) for d in paths)
    inner = (
        f"for d in {quoted}; do "
        f'if [ -c "$d" ]; then chmod 666 "$d" && echo "activated:$d"; '
        f'else echo "skip:$d"; fi; done'
    )

    try:
        proc = subprocess.run(
            ["pkexec", "bash", "-c", inner],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        msg = (
            "未找到 pkexec。请手动执行：sudo chmod 666 <设备路径>，"
            "或将用户加入 dialout 组：sudo usermod -aG dialout $USER"
        )
        result = error_result(msg, devices=[])
        if use_json:
            print_json_result(result)
        else:
            print(msg, file=sys.stderr)
        return 1
    except subprocess.TimeoutExpired:
        msg = "pkexec 超时"
        result = error_result(msg, devices=[])
        if use_json:
            print_json_result(result)
        else:
            print(msg, file=sys.stderr)
        return 1

    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    activated: list[str] = []
    for line in stdout.splitlines():
        if line.startswith("activated:"):
            activated.append(line.split(":", 1)[1])

    ok = proc.returncode == 0 and bool(activated)
    message = stdout or stderr or ("成功" if ok else "失败")
    if not ok and proc.returncode == 0 and not activated:
        message = "未激活任何设备（路径不存在或不是字符设备）。" + (stdout or stderr)

    devices = [address_info(name=p, status=p in activated) for p in paths]
    if ok:
        result = ok_result(
            message=message,
            devices=devices,
            activated=activated,
            requested=paths,
        )
        exit_code = 0
    else:
        result = error_result(
            message,
            devices=devices,
            activated=activated,
            requested=paths,
        )
        exit_code = 1

    if use_json:
        print_json_result(result)
    else:
        if ok:
            for name in activated:
                print(f"activated: {name}")
            print(message)
        else:
            print(message, file=sys.stderr)
    return exit_code
