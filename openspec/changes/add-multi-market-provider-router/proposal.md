## Why

要让组合回测长期可用，数据接入必须支持多市场（A 股、美股、加密）并且能按 provider 插拔；否则每新增一个市场都要改核心入库逻辑，扩展成本高且易引入误差。

## What Changes

- 新增 provider 协议（价格、汇率）和按市场路由的统一 adapter。
- 新增 CSV provider 实现，作为离线且可审计的数据源插件。
- 新增归一化与数据合法性校验（日期、正价格、正汇率、source 兜底）。
- 新增路由测试，覆盖多市场成功链路和缺失 provider 的失败链路。

## Capabilities

### New Capabilities
- `multi-market-provider-routing`: 按资产所属市场将价格取数分发给对应 provider。
- `provider-data-normalization`: provider 返回值统一归一化为系统 ingestion 结构并做基础合法性校验。

### Modified Capabilities
- `data-source-adapters`: 扩展为支持 provider 路由与 CSV provider 插件。

## Impact

- 影响 `src/portfolio_lab/data_adapters.py`、`src/portfolio_lab/__init__.py`。
- 影响 `tests/test_portfolio_lab.py` 的数据接入相关测试覆盖。
