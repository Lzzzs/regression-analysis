## Context

已有 `LocalJSONMarketDataAdapter` 适合单一离线数据文件，但不适合多市场异构 provider 路由。当前缺少对“资产 -> 市场 -> provider -> 统一 row”这一链路的显式建模。

## Goals / Non-Goals

**Goals:**
- 定义价格 provider 与 FX provider 接口。
- 提供市场路由 adapter，把 selected assets 分发到对应 provider。
- 在 adapter 层做统一归一化与校验，保证进入 `UniverseStore` 的结构一致。

**Non-Goals:**
- 不接入实时网络 API。
- 不做 provider 级缓存和重试。
- 不实现复杂符号映射中心服务。

## Decisions

### 1) 抽象三层接口
- 决策：`PriceDataProvider` / `FXDataProvider` / `RoutedMarketDataAdapter`。
- 原因：把“数据获取”与“市场路由/归一化”解耦，便于替换任意 provider。

### 2) 路由依赖显式映射
- 决策：初始化时传入 `asset_market_map` 与可选 `asset_symbol_map`。
- 原因：避免在 adapter 内硬编码品种规则，便于审计和测试。

### 3) CSV provider 作为标准离线插件
- 决策：提供 `LocalCSVPriceProvider`、`LocalCSVFXProvider`。
- 原因：CSV 简单透明，便于手工核对与回放。

### 4) 归一化阶段立即校验
- 决策：在 adapter 内校验正价格/正汇率、合法日期与 FX pair 格式。
- 原因：把坏数据拦在入库前，降低后续快照与回测污染风险。

## Risks / Trade-offs

- [映射缺失导致任务失败] -> 报错明确包含资产或市场。
- [provider 返回字段不一致] -> 通过归一化收敛字段，并补默认 source。
- [CSV 性能有限] -> 作为离线基线实现，后续可替换为数据库/API provider。
