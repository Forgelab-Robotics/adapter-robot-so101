from __future__ import annotations

import unittest

from forge_msgs import JointCommand
from robots_so101.driver import NAME_TO_ID, SO101Driver, _rad_to_raw


class _FakeBus:
    is_connected = True

    def __init__(self) -> None:
        self.position_writes: list[dict[int, int]] = []

    def sync_write_positions(self, values: dict[int, int]) -> None:
        self.position_writes.append(values)


class SparseCommandTest(unittest.TestCase):
    def setUp(self) -> None:
        self.driver = SO101Driver(auto_connect=False)
        self.bus = _FakeBus()
        self.driver.bus = self.bus  # type: ignore[assignment]

    def test_arm_command_does_not_write_gripper(self) -> None:
        self.driver.set_command(
            JointCommand(name=["shoulder_pan"], position=[0.25])
        )

        self.assertEqual(
            self.bus.position_writes,
            [{NAME_TO_ID["shoulder_pan"]: _rad_to_raw(0.25)}],
        )

    def test_gripper_command_does_not_write_arm(self) -> None:
        self.driver.set_command(JointCommand(name=["gripper"], position=[0.5]))

        self.assertEqual(
            self.bus.position_writes,
            [{NAME_TO_ID["gripper"]: _rad_to_raw(0.5)}],
        )

    def test_non_position_command_is_rejected_without_writes(self) -> None:
        with self.assertRaisesRegex(ValueError, "mode='position'"):
            self.driver.set_command(
                JointCommand(
                    name=["gripper"],
                    mode="velocity",
                    position=[0.5],
                    velocity=[0.5],
                )
            )

        self.assertEqual(self.bus.position_writes, [])


if __name__ == "__main__":
    unittest.main()
