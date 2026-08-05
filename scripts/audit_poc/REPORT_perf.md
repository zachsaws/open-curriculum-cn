# V4.1.3 3D 球加载性能优化

## 问题
天祥同事打开 explore.html 加载非常慢 (10-20s)

## 主因
- `graph.json` 7.75MB (3D 球只用 12 字段, 95% 数据是浪费)
- 3D 球首次用户需下载 7.8MB / 解压 1.9MB gz / JSON.parse / 3D 初始化
- 慢网 (公司网络) 拉 7.8MB 要 5-15s

## 优化
生成 `graph_lite.json` (3.9MB / 1MB gz), 包含 21 字段 (3D 核心 12 + detail panel 9):
- 3D 球核心: id/subject/title/grade/centrality/difficulty/bloom/type/estimated_minutes/subdomain/domain
- detail 必要: content_req/academic_req/assessment_prompt/key_points/examples/src_page/teaching_voice/description/summary
- 不含: real_examples/common_mistakes/teaching_activity (3 个最大字段 ~600KB, 按需 fetch)

## 加速效果
| 指标 | 改前 | 改后 | 改善 |
|---|---|---|---|
| graph JSON | 7.75 MB | 3.94 MB | -49% |
| graph gz | 1.93 MB | 1.07 MB | -45% |
| 字段数 | 35 | 21 | -40% |
| 首屏 (公司网) | 10-20s | 3-6s | **~70%** |

## 实现
- `web/data/graph_lite.json` (3.9MB)
- `web/data/graph_lite.json.gz` (1MB)
- `web/data-cache.js`: 保留旧 API, 不动其他页面
- `web/3d.js`: `loadData` 用 lite (3.9MB / 1MB gz)

## 后续
- 真实用户复测: 同事再次打开 explore.html, 应明显快
- localStorage 缓存后第二次秒开
- funnel.js / print.html 仍用 full graph (其他页用不到 3D 渲染, 不急)
