# -*- mode: python ; coding: utf-8 -*-
# ruff: noqa: F821
# pyright: reportUndefinedVariable=false, reportMissingModuleSource=false
# 在项目根目录执行：uv run --extra pyinstaller pyinstaller --noconfirm --clean scripts/robots_so101.spec
# 或：./scripts/build_pyinstaller.sh

from __future__ import annotations

import os

from PyInstaller.utils.hooks import collect_submodules

_spec_dir = os.path.dirname(os.path.abspath(SPEC))
_package_dir = os.path.dirname(_spec_dir)
_src_dir = os.path.join(_package_dir, "src")

a = Analysis(
    [os.path.join(_src_dir, "robots_so101", "main.py")],
    pathex=[_src_dir, _package_dir],
    binaries=[],
    hiddenimports=collect_submodules("serial")
    + [
        "robots_so101",
        "robots_so101.config",
        "robots_so101.driver",
        "robots_so101.feetech_bus",
        "robots_so101.device_tools",
        "typer",
        "click",
        "yaml",
        "pydantic",
        "pydantic_core",
        "pyarrow",
        "numpy",
        "forge_common",
        "forge_msgs",
        "forge_msgs.joint",
        "forge_robot",
        "forge_robot.node_runner",
        "forge_robot.robot_protocol",
        "dora",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="robots_so101",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
