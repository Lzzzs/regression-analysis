# Changelog

## 2026-02-27

### Added
- 一键回测编排接口 `POST /jobs/auto`（自动生成快照 + 创建任务）
- Web 结果可视化：核心指标卡片、净值曲线、回撤曲线
- Web 字段中文化工具：已知字段映射 + 未知字段 token 兜底
- 本地运行脚本：`scripts/dev_up.sh`、`scripts/dev_down.sh`
- 环境变量示例：`.env.example`、`apps/web/.env.local.example`

### Changed
- 任务详情页从纯 JSON 升级为“可视化 + 中文字段 + 明细并存”
- README 改为可发布版本，补齐本地启动、API、测试、部署说明

### Archived OpenSpec Change
- `add-web-result-visualization` -> `openspec/changes/archive/2026-02-27-add-web-result-visualization`
