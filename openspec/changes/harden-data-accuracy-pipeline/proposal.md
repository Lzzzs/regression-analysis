## Why

当前系统以手工注入数据为主，缺少统一数据源适配层、入库前一致性校验和快照完整性校验，导致“数据准确性”无法形成可重复验证闭环。

## What Changes

- 新增离线数据源适配接口，支持按区间批量拉取价格与汇率并统一转换为系统入库结构。
- 新增入库校验逻辑，检测重复记录、非法字段和交易日对齐问题，输出明确错误信息。
- 新增快照完整性字段（内容校验和）并在加载/回测时校验，防止快照被篡改或损坏后继续使用。
- 新增测试覆盖以上行为，保证 file/redis 任务链路以外的数据正确性同样可回归。

## Capabilities

### New Capabilities
- `data-source-adapters`: 统一数据源拉取接口与离线文件实现，支持价格和汇率按日期区间取数。
- `ingestion-data-validation`: 入库前记录级与批次级校验，包括重复键冲突与交易日对齐。
- `snapshot-integrity-verification`: 快照发布时生成完整性校验和，读取与回测阶段强制验签。

### Modified Capabilities
- `build-portfolio-backtest-lab`: 强化数据质量与快照可信度相关要求。

## Impact

- 影响 `src/portfolio_lab/universe.py` 的 ingestion 和 snapshot 发布流程。
- 影响 `src/portfolio_lab/backtest.py` 的快照加载校验路径。
- 新增数据源适配模块与测试覆盖（`tests/test_portfolio_lab.py`）。
