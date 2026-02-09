# 变更日志 (CHANGELOG)

本文件记录 Intel Briefing 项目的所有重要变更。

---

## [Unreleased] - 2026-02-09

### 文档
- 更新 README.md：添加 Linux/macOS 安装说明、Docker 使用说明
- 更新项目结构说明，覆盖所有新增文件
- 添加开发者贡献指南（如何添加新 Sensor）
- 添加传感器列表详细信息（API Key 需求、基类信息）
- 创建 CHANGELOG.md 变更日志

### 安全
- 审计所有传感器代码，确认无 API Key 泄露到 print/log
- 确认已移除历史遗留的自动 pip install 代码（供应链风险）
- 清理 x_grok_sensor.py 中重复的 headers 定义

---

## [0.4.0] - 传感器统一接口迁移

### 重构
- 所有传感器迁移到 `BaseSensor` 抽象基类接口
- 统一返回 `SensorResult` 数据结构
- 每个传感器新增 `is_available()` 方法检查依赖
- 每个传感器支持 `fetch_with_cache()` 缓存调用

### 新增传感器
- `wallstreetcn_sensor.py` - 华尔街见闻财经新闻传感器
- `kr36_sensor.py` - 36Kr 科技商业新闻传感器

---

## [0.3.0] - 基础架构优化

### 新增
- `src/sensors/base.py` - 传感器基类，定义统一接口
- `SensorResult` 数据类 - 统一的传感器返回格式
- `cached_fetch()` - 文件缓存机制（MD5 哈希键名，默认 30 分钟 TTL）
- `retry_request()` - 指数退避重试机制（处理 429/5xx，最大 3 次重试）

### 优化
- 日志系统：全面使用 `logging` 模块替代 `print`
- Hacker News：使用 `ThreadPoolExecutor` 并发获取，解决 N+1 问题
- Product Hunt：移除 Grok 回退方案，避免 AI 幻觉数据
- 代码清理：移除冗余 import、未使用变量

---

## [0.2.0] - DevOps 基础设施

### 新增
- `Dockerfile` - Python 3.10-slim 基础镜像
- `docker-compose.yml` - 支持单次运行和定时任务（每天 8:00）
- `.github/workflows/ci.yml` - CI/CD 流水线（flake8 lint + pytest）
- `tests/test_sensors.py` - 基础单元测试（HN、arXiv 传感器）
- `requirements.txt` - 统一依赖管理

---

## [0.1.0] - P0/P1 优化

### 优化
- 移除传感器中 import 时自动 `pip install` 的代码（供应链安全风险）
- 统一日志格式，替换散落的 `print()` 调用
- 并发获取优化，减少串行请求等待时间
- 代码清理和规范化

### 文档
- 添加 `docs/OPTIMIZATION_PLAN.md` 优化计划文档

---

## [0.0.1] - 初始版本

### 新增
- 项目初始化：Intel Briefing 情报聚合系统
- 三司架构：战略部、战术部、Web3部
- 传感器：Hacker News、Product Hunt、arXiv、GitHub Trending、Chrome 扩展、V2EX、小红书、X/Grok
- 报告生成器：Curator 商业简报
- 工具模块：链接验证器
- Antigravity Agent 集成配置
