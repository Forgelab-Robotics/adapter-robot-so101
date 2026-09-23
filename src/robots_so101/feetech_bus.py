"""最小 Feetech STS 总线封装：基于 pyserial 的 STS 协议读写，供 SO101Driver 使用。"""

from __future__ import annotations

import struct
import time
from typing import Any, Optional

# STS 协议常量（参考 Dynamixel/Feetech 格式）
HEADER = bytes([0xFF, 0xFF])
INST_READ = 0x02
INST_WRITE = 0x03
# STS3215 控制表地址（常见取值，与 lerobot/Feetech 表一致时可调整）
GOAL_POSITION_ADDR = 0x2A
PRESENT_POSITION_ADDR = 0x38
TORQUE_ENABLE_ADDR = 0x28
POSITION_LEN = 2
# 位置编码：360° = 4096 份，中位 2047
POSITION_CENTER = 2047
POSITION_STEPS = 4096


def _checksum(packet: bytearray) -> int:
    """计算校验和：~(ID + LEN + INST + params) & 0xFF。"""
    return (~sum(packet[2:]) & 0xFF)


def _make_read_packet(motor_id: int, address: int, length: int) -> bytes:
    """构造读包：0xFF 0xFF ID LEN 0x02 addr len。"""
    # LEN = 参数长度 + 2（指令 + 校验）
    params = bytes([address, length])
    length_byte = len(params) + 2
    packet = bytearray(HEADER)
    packet.append(motor_id)
    packet.append(length_byte)
    packet.append(INST_READ)
    packet.extend(params)
    packet.append(_checksum(packet))
    return bytes(packet)


def _make_write_packet(motor_id: int, address: int, data: bytes) -> bytes:
    """构造写包：0xFF 0xFF ID LEN 0x03 addr data...。"""
    params = bytes([address]) + data
    length_byte = len(params) + 2
    packet = bytearray(HEADER)
    packet.append(motor_id)
    packet.append(length_byte)
    packet.append(INST_WRITE)
    packet.extend(params)
    packet.append(_checksum(packet))
    return bytes(packet)


class FeetechBus:
    """
    最小 Feetech STS 串口总线：按 ID 读写 Present_Position / Goal_Position。
    编码：360° = 4096 份，中位 2047；raw 为 0～4095。
    """

    def __init__(self, port: str, baudrate: int = 1000000, timeout: float = 0.1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._ser: Any = None

    def connect(self) -> None:
        import serial
        self._ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
        )
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()
        time.sleep(0.05)

    def disconnect(self) -> None:
        if self._ser is not None:
            try:
                self._ser.close()
            except Exception:
                pass
            self._ser = None

    @property
    def is_connected(self) -> bool:
        return self._ser is not None and self._ser.is_open

    def _read_response(self, expected_id: int, min_params: int = 0) -> Optional[bytes]:
        """读取响应包，返回参数部分；失败返回 None。"""
        if self._ser is None:
            return None
        # 找 0xFF 0xFF
        state = 0
        buf = bytearray()
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            if self._ser.in_waiting == 0:
                time.sleep(0.001)
                continue
            b = self._ser.read(1)
            if not b:
                continue
            buf.append(b[0])
            if state == 0 and len(buf) >= 2 and buf[-2] == 0xFF and buf[-1] == 0xFF:
                state = 1
                buf = bytearray(buf[-2:])
            elif state == 1 and len(buf) >= 4:
                rid, plen = buf[2], buf[3]
                if rid != expected_id:
                    buf.clear()
                    state = 0
                    continue
                # 总长 = 2 + 2 + plen (id, len, inst, params..., checksum)
                need = 2 + 2 + plen
                while len(buf) < need and time.monotonic() < deadline:
                    if self._ser.in_waiting:
                        buf.extend(self._ser.read(need - len(buf)))
                    else:
                        time.sleep(0.001)
                if len(buf) < need:
                    return None
                packet = bytes(buf[:need])
                checksum = (~sum(packet[2:-1]) & 0xFF)
                if packet[-1] != checksum:
                    return None
                # params 在 id, len, inst 之后
                param_len = plen - 2  # plen 含 inst + checksum
                if param_len < min_params:
                    return None
                return packet[5:5 + param_len]
        return None

    def read_position(self, motor_id: int) -> Optional[int]:
        """读取单个舵机当前位置（raw 0～4095），失败返回 None。"""
        if self._ser is None:
            return None
        packet = _make_read_packet(motor_id, PRESENT_POSITION_ADDR, POSITION_LEN)
        self._ser.reset_input_buffer()
        self._ser.write(packet)
        params = self._read_response(motor_id, min_params=POSITION_LEN)
        if params is None or len(params) < POSITION_LEN:
            return None
        # 小端 2 字节
        raw = struct.unpack_from("<H", params)[0]
        return raw & 0xFFF if raw <= 0xFFF else raw  # 12-bit

    def write_position(self, motor_id: int, raw_position: int) -> bool:
        """写入单个舵机目标位置（raw 0～4095）。"""
        if self._ser is None:
            return False
        raw_position = max(0, min(4095, raw_position))
        data = struct.pack("<H", raw_position)
        packet = _make_write_packet(motor_id, GOAL_POSITION_ADDR, data)
        self._ser.write(packet)
        time.sleep(0.001)
        return True

    def sync_read_positions(self, motor_ids: list[int]) -> dict[int, int]:
        """依次读取多个舵机位置，返回 id -> raw_position；读失败的 id 不包含或值为 0。"""
        result = {}
        for mid in motor_ids:
            pos = self.read_position(mid)
            result[mid] = pos if pos is not None else 0
        return result

    def sync_write_positions(self, id_to_raw: dict[int, int]) -> None:
        """依次写入多个舵机目标位置。"""
        for mid, raw in id_to_raw.items():
            self.write_position(mid, raw)

    def write_register(self, motor_id: int, address: int, value: int, length: int = 1) -> bool:
        """
        通用的寄存器写入方法。
        length=1 用于扭矩开关(0x28)；length=2 用于某些参数设置。
        """
        if self._ser is None:
            return False
        
        # 根据长度打包数据
        if length == 1:
            data = struct.pack("B", value)
        else:
            data = struct.pack("<H", value)
            
        packet = _make_write_packet(motor_id, address, data)
        self._ser.write(packet)
        # 飞特舵机建议写完后给总线一点点时间切换
        time.sleep(0.0005) 
        return True
