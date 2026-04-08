# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

**Keeper** - 智能运维 Agent，类似 Claude Code 的对话式 CLI 工具

**MVP 状态：** ✅ 基础框架已完成 (2026-04-08)

## 快速命令

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行测试
pytest tests/test_keeper.py -v

# 启动交互模式
keeper chat

# 单命令执行
keeper run 检查 192.168.1.100

# 查看状态
keeper status

# 初始化配置
keeper init
```

## 技术架构

### 核心模块

| 模块 | 文件 | 说明 |
|------|------|------|
| NLU 引擎 | `keeper/nlu/` | LangChain + LLM 意图识别 |
| Agent 核心 | `keeper/core/` | 意图分发、上下文管理 |
| 工具 | `keeper/tools/` | 服务器采集 (psutil)、扫描 (Nmap) |
| CLI | `keeper/cli.py` | Click + Prompt Toolkit 交互 |
| 配置 | `keeper/config.py` | 环境变量 + YAML 配置 |

### 目录结构

```
├── keeper/
│   ├── __init__.py
│   ├── cli.py            # Click 入口 + 交互模式
│   ├── config.py         # 配置管理
│   ├── nlu/
│   │   ├── base.py       # NLU 抽象基类
│   │   └── langchain_engine.py  # LangChain 引擎实现
│   ├── core/
│   │   ├── agent.py      # Agent 核心
│   │   └── context.py    # 上下文管理 + 记忆系统
│   └── tools/
│       ├── server.py     # 服务器工具 (psutil)
│       └── scanner.py    # 扫描工具 (Nmap)
├── tests/
│   └── test_keeper.py    # 单元测试
├── keeper_entry.py       # 入口脚本
├── pyproject.toml        # 项目配置
├── requirements.txt      # 依赖列表
└── README.md
```

### NLU 流程

```
用户输入 → LangChain + LLM → 意图识别 → 参数提取 → 工具调用 → 结果生成 → 回复用户
                              ↓
                        上下文记忆 (指代消解)
```

### 支持的意图类型

- `inspect` - 服务器资源巡检
- `scan` - 漏洞扫描
- `config` - 配置管理
- `logs` - 日志查询
- `help` - 帮助
- `unknown` - 未知意图

### 记忆系统

- **短期记忆：** 最近 10 轮对话，存储在 `MemoryManager`
- **上下文：** 当前主机、环境、意图，存储在 `ContextManager`
- **指代消解：** LLM 自动理解"它"、"这台"等指代

## 配置

### 配置文件位置

| 文件 | 路径 | 说明 |
|------|------|------|
| 主配置 | `~/.keeper/config.yaml` | 环境配置、阈值、主机列表 |
| LLM 配置 | `~/.keeper/llm_config.yaml` | LLM 设置（provider, model, base_url） |
| API Key | `~/.keeper/api_key` | 敏感信息，权限 600（仅所有者可读写） |

### 配置命令

```bash
# 设置 LLM 配置
keeper config set --api-key YOUR_API_KEY \
  --base-url https://api.qnaigc.com/v1 \
  --model claude-sonnet-4-6

# 查看配置
keeper config show

# 清除配置
keeper config clear
```

### 配置加载顺序

1. 环境变量（仅作为默认值）
2. 配置文件（`~/.keeper/`）
3. `keeper config set` 命令保存的配置

### 配置文件结构

```yaml
# ~/.keeper/config.yaml
current_profile: dev

profiles:
  dev:
    hosts: [localhost]
    thresholds: {cpu: 90, memory: 90, disk: 95}
```

```yaml
# ~/.keeper/llm_config.yaml
provider: openai_compatible
base_url: https://api.qnaigc.com/v1
model: claude-sonnet-4-6
```

## 开发注意事项

1. **虚拟环境：** 所有命令需先激活 `venv/bin/activate`
2. **测试：** 修改代码后运行 `pytest tests/test_keeper.py -v`
3. **LLM 依赖：** 需要有效的 API Key 才能测试 NLU 功能
4. **本地采集：** `ServerTools.inspect_server("localhost")` 无需远程连接

## 待实现功能 (Phase 2+)

- [ ] Nmap 漏洞扫描完整集成
- [ ] SSH 远程服务器采集
- [ ] 多主机批量巡检
- [ ] HTML/JSON 报告生成
- [ ] 智能告警分析
- [ ] 自动修复建议
