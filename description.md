# so101 构型说明

## 构型概览

> 当前仓库在 `assets/mjcf/` 和 `assets/glb/` 中未发现可直接用于 Markdown 的机器人预览图。

SO-101 六自由度机械臂，使用 Feetech 舵机并配备末端夹爪。

- **构型类别**：机械臂

## 支持引擎

| 引擎 | 支持情况 | 依据 |
|---|---|---|
| 真机 | 支持 | `src/robots_so101/` |
| MuJoCo | 支持 | `assets/mjcf/SO101.xml` |
| Isaac Sim / Isaac Lab | 支持 Isaac Sim 接入 | `assets/usd/SO101.usda` |

## 模型资产

- [`assets/mjcf/SO101.xml`](assets/mjcf/SO101.xml)
- [`assets/mjcf/Unimanual_SO101_withTable.xml`](assets/mjcf/Unimanual_SO101_withTable.xml)
- [`assets/glb/SO101.glb`](assets/glb/SO101.glb)
- [`assets/usd/SO101.usda`](assets/usd/SO101.usda)


> “支持”仅表示仓库中存在对应驱动、模型或可执行工作流；实际运行仍需满足硬件、SDK 与运行环境要求。
