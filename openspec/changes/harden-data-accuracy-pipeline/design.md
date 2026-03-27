## Context

当前 `UniverseStore` 直接接收外部 rows 并覆盖写入，缺少批次级去重约束与来源抽象；快照文件也缺少完整性字段，回测时无法判断文件是否被改写。

## Goals / Non-Goals

**Goals:**
- 定义可插拔数据源适配接口，并提供离线 JSON 文件实现。
- 在 ingestion 阶段增加重复键冲突、未知资产、交易日对齐等可解释校验。
- 在 snapshot 阶段落地 checksum，并在读取阶段强制校验。

**Non-Goals:**
- 不接入在线行情 API。
- 不实现数据库持久化。
- 不引入复杂多版本 schema 迁移。

## Decisions

### 1) 增加 `MarketDataAdapter` 抽象
- 决策：新增独立模块提供 `fetch_prices`/`fetch_fx` 接口，`UniverseStore` 通过 `ingest_from_adapter` 消费。
- 原因：把“取数”与“校验/入库”职责分离，后续接不同源只需新 adapter。
- 备选：在 `UniverseStore` 直接写多源分支，会导致核心类持续膨胀。

### 2) 批次级校验采用“键唯一 + 源一致”
- 决策：价格键为 `(asset_id, day)`，汇率键为 `(pair, day)`；同一批次出现重复且值不一致时报错。
- 原因：防止静默覆盖，保证输入数据可审计。
- 备选：允许后写覆盖前写，不利于追踪偏差来源。

### 3) 快照完整性字段使用 canonical JSON SHA256
- 决策：对不含 `integrity` 字段的 payload 做 `sort_keys=True` 序列化后计算 SHA256，写入 `integrity.checksum_sha256`。
- 原因：实现简单、确定性强，便于跨环境复核。
- 备选：按文件字节流计算，容易受格式化差异影响。

### 4) 校验位置放在 `load_snapshot` 与 Backtest 入口
- 决策：`UniverseStore.load_snapshot` 与 `BacktestEngine._load_snapshot` 都进行完整性校验。
- 原因：无论上层从哪里加载快照，都能阻断损坏数据进入计算链路。
- 备选：仅在回测时校验，会放过其他调用场景。

## Risks / Trade-offs

- [历史快照不含完整性字段] -> 兼容逻辑：缺失时报明确错误，测试中按新格式生成。
- [更严格校验导致旧数据导入失败] -> 报错包含冲突键和行号，便于快速修复。
- [adapter 接口过早抽象] -> 先提供最小接口，仅覆盖当前需要的价格/汇率拉取。

## Migration Plan

1. 新增 adapter 模块与离线实现。
2. 在 `UniverseStore` 引入批次校验与 adapter ingestion。
3. 在快照发布与加载增加 checksum 逻辑。
4. 更新测试并执行全量回归。

## Open Questions

- 后续是否需要把数据源元信息（版本号、下载时间）纳入 checksum 覆盖范围。
