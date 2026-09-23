# SO101

[查看机器人构型说明](description.md)

SO101 机械臂资源与运行入口，包含 MuJoCo MJCF 描述文件、真机 dora 节点、串口工具和 PyInstaller 单文件打包脚本。

## 目录结构

```text
.
|- assets/
|  |- mjcf/
|     |- SO101.xml
|- configs/
|  |- config.example.yaml
|- scripts/
|  |- build_pyinstaller.sh
|  |- robots_so101.spec
|- src/
|  |- robots_so101/
|     |- main.py
|     |- config.py
|     |- driver.py
|     |- feetech_bus.py
|     |- device_tools.py
|- pyproject.toml
```

## MJCF 资源

主模型文件位于 `assets/mjcf/SO101.xml`，可作为 MuJoCo 场景或机器人节点配置的模型输入。

## 配置

复制 `configs/config.example.yaml` 为 `configs/config.yaml` 并按实际串口修改。配置来源优先级：

1. 命令行 `--config /path/to/config.yaml`
2. 环境变量 `SO101_NODE_CONFIG`
3. dora dataflow 节点的 `config` / `config_path`

## 运行

`robots-so101` 是统一 CLI 入口。无子命令或使用 `run` 时运行节点：

```bash
uv sync
uv run robots-so101 --config configs/config.yaml
uv run robots-so101 run --config configs/config.yaml
```

串口工具与测试命令：

```bash
uv run robots-so101 list-devices --json
uv run robots-so101 activate-devices --json
uv run robots-so101 test --config configs/config.yaml --duration 15
```

`list-devices` 和 `activate-devices` 仅匹配 `ttyACM*` 设备。`list-devices` 的 JSON 结构与 Piper 统一：`{"ports": [{"name", "address", "status"}]}`，其中 `name` 可直接作为串口路径使用，`status` 表示对应字符设备权限是否已是 `chmod 666`。`test` 会循环夹爪开合，用于确认串口与机械臂对应关系。`activate-devices` 会对匹配到的串口设备临时执行 `chmod 666`（Linux，需 `pkexec`）。长期推荐将用户加入 `dialout` 组：

```bash
sudo usermod -aG dialout $USER
# 注销后重新登录
```

## Python 包

项目使用 `uv_build`，包模块名为 `robots_so101`，入口定义在 `pyproject.toml`：

```toml
[project.scripts]
robots-so101 = "robots_so101.main:main"
robots_so101 = "robots_so101.main:main"

[tool.uv.build-backend]
module-name = "robots_so101"
```

## PyInstaller 单文件打包

安装打包依赖：

```bash
uv sync --extra pyinstaller
```

执行打包脚本，产物位于 `dist/robots_so101`：

```bash
chmod +x scripts/build_pyinstaller.sh
./scripts/build_pyinstaller.sh
```

也可以直接运行 PyInstaller：

```bash
uv run --extra pyinstaller pyinstaller --noconfirm --clean scripts/robots_so101.spec
```

打包后示例：

```bash
./dist/robots_so101 --config configs/config.yaml
./dist/robots_so101 list-devices --json
./dist/robots_so101 activate-devices --json
```

若运行时缺少模块，可在 `scripts/robots_so101.spec` 的 `hiddenimports` 中补充。

## 主要依赖

- `dora-rs`：dora 节点运行。
- `robot-core`：机器人驱动协议与节点 runner。
- `forge-msgs`：`JointCommand` / `JointState` 消息与 Arrow 序列化。
- `pyserial`：Feetech STS 舵机串口通信。
- `mujoco`：MJCF 模型与仿真相关工作流。
