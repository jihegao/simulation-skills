# 仿真分发器 Agent 说明

本文档描述 Simulation Skills 套件作为“仿真分发器件”时的轻量工作边界。当前目标不是一次性实现所有仿真运行时，而是先把方法覆盖、路由判断、最小产物和未来工具组合边界固化下来。

## 当前定位

`sim-adapter` 是入口分发器，负责判断一个问题是否需要仿真增强推理，并选择最小可表达机制的方法族。具体方法实现仍由平级 skill、示例、脚本或未来工具层承担。

现有已落地能力：

- `abm-modeling`：Mesa/ABM 建模、实验、可视化和结果解释。
- `discrete-event-modeling`：SimPy/DES 建模、队列、资源、库存、维修和实验解释。
- `simulation-model-conversion`：从描述、AnyLogic/Mesa/SimPy 结构或视觉原型转换为可运行仿真产物。
- `examples/`：保存可运行案例和已迁移的机制复现。

当前只在路由层覆盖、尚未做成完整方法 skill 的能力：

- 系统动力学：存量、流量、反馈、延迟、饱和和长期政策杠杆。
- Monte Carlo / 敏感性分析：参数不确定、风险分布、情景采样、敏感性排序。
- 网络仿真：传播、路由、依赖、级联、匹配、供应网络和图拓扑影响。
- 物理 / 连续仿真：ODE、刚体、碰撞、轨迹、控制、热/流体/结构等连续机制。
- 混合仿真编排：多个机制必须同时出现时，明确唯一权威时间、状态和指标来源。

## 路由原则

分发器先判断问题机制，而不是先判断领域标签。

| 主导机制 | 优先方法 | 当前落点 |
| --- | --- | --- |
| 个体异质性、局部规则、适应、空间/网络交互、涌现 | ABM | `abm-modeling` |
| 到达、服务、排队、资源约束、维修、库存、流程时序 | DES | `discrete-event-modeling` |
| 聚合存量、流量、反馈、延迟、长期策略 | 系统动力学 | 先产出 stock-flow spec，未来补 `system-dynamics-modeling` |
| 输入参数不确定，但内部动态较轻 | Monte Carlo / 敏感性 | 先产出采样表和脚本计划，未来补独立轻量 skill |
| 图拓扑驱动传播、路由、依赖、级联 | 网络仿真 | 先产出 graph spec，必要时组合 ABM/DES |
| 运动、力、碰撞、控制、微分方程或连续物理过程 | 物理 / 连续仿真 | 先推荐 SciPy ODE、PyBullet、MuJoCo、Box2D 或领域 solver |
| 多机制不可拆分 | 混合仿真 | 先指定权威核心，再组合其他层 |

## 轻量补全路线

优先补文档和分发协议，再补运行时。

1. `system-dynamics-modeling`
   - 最小产物：stock-flow spec、方程、单位、参数表、初始值、校准需求、情景输出表。
   - 首个案例：复用 `examples/global_warming_system_dynamics`，沉淀为标准模板。

2. `monte-carlo-sensitivity`
   - 最小产物：变量分布表、相关性假设、采样数、种子、输出分位数、敏感性排序。
   - 首个案例：需求/成本/可靠性/交付周期类风险比较。

3. `network-simulation`
   - 最小产物：节点/边 schema、传播或路由规则、拓扑指标、级联阈值、实验输出。
   - 首个案例：供应网络中断、影响传播或依赖级联。

4. `physics-continuous-simulation`
   - 最小产物：状态变量、微分方程或物理引擎选择、步长、稳定性检查、边界条件。
   - 首个案例：把 `examples/biped_microgravity` 从静态检查扩展为可选连续动力学模板。

5. `hybrid-simulation-patterns`
   - 最小产物：混合模型协议，而不是先做重运行时。
   - 必须明确：哪个引擎拥有时间推进、哪个对象拥有状态、哪个输出作为指标真源。

## 未来工具层组合

方法 skill 不应过早绑定单一工具。工具层可以按任务灵活组合：

- Python runners：用于可重复实验、CSV/JSON 输出、回归测试和批量 sweep。
- Browser / static HTML：用于轻量可视化、教学演示、回放和参数探索。
- Solara / Mesa UI：用于 ABM 检查和交互调试，不替代实验输出。
- SciPy / NetworkX / SimPy / Mesa：作为轻量 Python-first 默认栈。
- PyBullet / MuJoCo / Box2D / 领域 solver：仅在连续物理机制确实是核心时引入。
- JSON / modeling-ir：用于跨系统交换，不把外部平台内部结构引入 skill。

工具层的完成标准不是“支持所有引擎”，而是每条路线都能输出清晰的机制说明、可复现实验入口、原始证据和 claim boundary。

## 分发器输出合同

每次路由应输出：

- Trigger：为什么这是复杂系统或不确定性问题。
- Method：选择的方法族，以及为什么不用更重的方法。
- Existing route：是否有可复用案例、runner、模板或历史路径。
- Minimum model：实体/存量、状态、事件/方程/规则、参数、指标。
- Experiment：baseline、干预项、horizon、seeds、sweep 或采样方案。
- Evidence boundary：结果能支持什么，不能证明什么。
- Next tool：需要加载的 skill、脚本、示例或未来工具层。

## 不做的事

- 不把完整方法 skill 嵌套进 `sim-adapter`。
- 不把示例页面或截图当成唯一证据。
- 不在没有机制映射和实验边界时承诺“等价复现”。
- 不因为领域相似就复用旧路线；必须检查主导机制、数据形状、实现栈和验证方式是否匹配。
