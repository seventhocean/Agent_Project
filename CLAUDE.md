# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

**Keeper** - 智能运维 Agent，类似 Claude Code 的对话式 CLI 工具

**版本：** v0.2.0 (2026-04-09)

## 快速命令

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行测试
pytest tests/ -v

# 启动交互模式（直接进入对话）
keeper

# 单命令执行
keeper run 检查 192.168.1.100

# 执行 Shell 命令
keeper exec -- df -h /
keeper exec -- ps aux --sort=-%mem

# 配置管理
keeper config set --threshold 80 --metric cpu
keeper config show

# 审计日志
keeper logs --hours 24
keeper logs --host 192.168.1.100
```

## 技术架构

### 核心模块

| 模块 | 文件 | 说明 |
|------|------|------|
| NLU 引擎 | `keeper/nlu/` | LangChain + LLM 意图识别 |
| Agent 核心 | `keeper/core/` | 意图分发、上下文管理、审计日志 |
| 工具 | `keeper/tools/` | 服务器采集、扫描、报告导出、日志查询 |
| CLI | `keeper/cli.py` | Click + Prompt Toolkit 交互 |
| 配置 | `keeper/config.py` | 环境变量 + YAML 配置 |

### 意图路由 (`keeper/core/agent.py`)

| 意图 | 处理器 | 功能 |
|------|--------|------|
| `inspect` | `_handle_inspect` | 服务器资源巡检 |
| `scan` | `_handle_scan` | 漏洞扫描 |
| `config` | `_handle_config` | 配置管理 |
| `logs` | `_handle_logs` | 日志查询（审计/系统/Docker） |
| `export` | `_handle_export` | 报告导出（JSON/HTML/MD） |
| `install` | `_handle_install` | 软件安装 |
| `confirm` | `_handle_confirm` | 确认执行 |

## 配置

### 配置文件位置

| 文件 | 路径 | 说明 |
|------|------|------|
| 配置文件 | `~/.keeper/config.yaml` | 所有配置（LLM、环境、阈值、主机列表） |

### 配置结构

```yaml
# ~/.keeper/config.yaml
current_profile: dev
profiles:
  dev:
    hosts: [localhost]
    thresholds: {cpu: 90, memory: 90, disk: 95}
llm:
  provider: openai_compatible
  api_key: sk-xxx
  base_url: https://api.qnaigc.com/v1
  model: doubao-seed-2.0-mini
```

### 配置命令

```bash
keeper config set --api-key YOUR_API_KEY --model claude-sonnet-4-6
keeper config set --threshold 80 --metric cpu
keeper config show
keeper config clear
```

## 开发注意事项

1. **虚拟环境：** 所有命令需先激活 `venv/bin/activate`
2. **测试：** 修改代码后运行 `pytest tests/ -v`
3. **LLM 依赖：** 需要有效的 API Key 才能测试 NLU 功能
4. **本地采集：** `ServerTools.inspect_server("localhost")` 无需远程连接
5. **Nmap 依赖：** 漏洞扫描需要系统安装 `nmap` 包
6. **CLI 入口：** `keeper` 直接进入交互模式（`invoke_without_command=True`）

## 已实现功能

### Phase 1 - MVP ✅
- CLI 框架、NLU 引擎、服务器巡检、配置管理、对话记忆

### Phase 2 - 增强功能 ✅
- 报告导出 (JSON/HTML/Markdown)、审计日志持久化、系统日志查询 (journalctl/文件/Docker)、多主机批量巡检、SSH 远程采集

## 待实现功能

### Phase 2 已实现功能详情

#### 报告导出
- **对话触发**：巡检后说 "导出为 JSON" / "生成 HTML 报告"
- **实现**：`keeper/tools/reporter.py` (ReportExporter.export_json/html/markdown)

#### 审计日志
- **自动记录**：每次 `Agent.process()` 自动写入 `~/.keeper/audit.log` (JSON Lines 格式)
- **实现**：`keeper/core/audit.py` (AuditLogger)
- **查询**：对话中说 "查看最近操作" 或命令行 `keeper logs --hours 24`

#### 系统日志查询
- **支持**：journalctl、/var/log 文件、Docker 容器日志
- **实现**：`keeper/tools/logs.py` (LogTools)
- [ ] K8s 客户端封装 (kubernetes Python SDK)
- [ ] Node/Pod/Deployment 状态检查
- [ ] ConfigMap/Secret/PVC 巡检
- [ ] Namespace 资源配额监控
- [ ] 异常 Pod 检测 (Pending/Failed/CrashLoopBackOff)
- [ ] Service/Ingress 配置检查
- [ ] 存储状态检查 (PVC/PV)

### Phase 4 - 智能分析与变更
- [ ] 根因分析 (RCA)
- [ ] 告警分析
- [ ] 自动修复建议
- [ ] 变更管理 (扩缩容/重启)

### Phase 5 - 安全与集成
- [ ] 安全基线检查
- [ ] 操作审计报表
- [ ] 告警集成 (Prometheus)
- [ ] IM 通知集成
