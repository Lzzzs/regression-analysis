## Why

当前回测结果主要以原始 JSON 展示，用户需要手动解读字段，难以快速判断收益、风险和区间表现。对于“自行搭配组合并立即分析”的目标，结果页需要更直观的可视化，同时字段应统一中文显示，降低理解成本并兼容后续新增字段。

## What Changes

- 在任务详情页新增核心指标卡片，突出年化收益、波动率、最大回撤与风险调整后收益指标。
- 在任务详情页新增净值曲线与回撤曲线图，支持区间起止标注与最值展示。
- 新增前端字段本地化层，对任务状态、事件、输入摘要与结果字段进行中文映射，并为未来新增字段提供 token 级兜底翻译。

## Capabilities

### New Capabilities
- `web-backtest-result-visualization`: 任务详情页可视化展示核心指标、净值和回撤趋势。
- `web-field-localization`: Web 页面对回测任务相关字段和值进行中文映射，未知字段可兜底转换。

### Modified Capabilities
- `web-experiment-console`: 任务详情从“原始结果查看”升级为“可视化 + 中文化”展示。

## Impact

- 影响 `apps/web/app/jobs/[id]/page.tsx`。
- 影响 `apps/web/app/jobs/page.tsx` 与 `apps/web/app/page.tsx` 的字段显示一致性。
- 新增 `apps/web/lib/field_localizer.ts` 作为通用本地化工具。
