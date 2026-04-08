# Keeper

智能运维 Agent - 交互式 CLI 工具

**产品形态：** 类似 Claude Code 的对话式 CLI Agent

**项目定位：** 
- 轻量化的智能运维助手
- 通过自然语言对话完成服务器巡检、漏洞扫描、异常诊断
- 基于 LangChain + LLM 实现自然语言理解
- MVP 阶段聚焦云服务器场景

---

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境变量

```bash
# OpenAI 兼容模式 (推荐 - 使用 qnaigc)
export KEEPER_API_KEY='your-api-key'
export KEEPER_BASE_URL='https://api.qnaigc.com/v1'
export KEEPER_PROVIDER='openai_compatible'
export KEEPER_MODEL='claude-sonnet-4-6'

# 或 Anthropic 模式
# export KEEPER_BASE_URL='https://api.qnaigc.com'
# export KEEPER_PROVIDER='anthropic'
```

### 启动 Agent

```bash
keeper
```

进入交互式对话模式，支持自然语言交流：

```
┌─────────────────────────────────────────┐
│  Keeper v0.1 - 智能运维助手              │
└─────────────────────────────────────────┘

👋 你好！我是 Keeper，你的智能运维助手。
   已连接：https://api.qnaigc.com/v1 (claude-sonnet-4-6)

keeper> 帮我检查一下 192.168.1.100 这台机器
keeper> 扫描一下生产环境的所有服务器
keeper> 昨天内存告警的主机是哪台？
```

### 单命令模式（非交互）

```bash
# 快速执行
keeper "检查 192.168.1.100 的健康状态"

# 带参数
keeper "扫描漏洞" --host 192.168.1.100

# 使用配置
keeper "巡检" --profile production
```

---

## 核心功能 (MVP)

### 1. 交互式对话

Keeper 基于 LLM 理解自然语言，自动解析意图和参数：

```
keeper> 帮我检查 192.168.1.100

[意图识别] 服务器资源巡检
[目标主机] 192.168.1.100
[执行检查...]

✓ CPU:     45%  (阈值：80%)  
✓ 内存：   62%  (阈值：85%)  
✓ 磁盘：   88%  (阈值：90%)  
✓ 负载：   1.2  (阈值：8)    

健康评分：85/100
```

### 2. 多轮对话 & 记忆

Keeper 记住上下文，支持连续对话：

```
keeper> 添加一台新主机 192.168.1.200
已添加主机 192.168.1.200 到 dev 环境

keeper> 给它设置更严格的阈值，CPU 超过 70% 就告警
好的，已更新 192.168.1.200 的 CPU 阈值为 70%

keeper> 那现在检查一下它
[自动识别"它"指代 192.168.1.200] 正在检查...
```

### 3. 服务器资源巡检

| 指标 | 说明 | 默认阈值 |
|------|------|----------|
| CPU 使用率 | 当前 CPU 占用百分比 | 80% |
| 内存使用率 | RAM 占用百分比 | 85% |
| 磁盘使用率 | 根分区占用百分比 | 90% |
| 系统负载 | 1 分钟平均负载 | CPU 核心数 * 2 |
| 异常进程 | CPU/内存占用 Top5 进程 | - |

### 4. 漏洞扫描

```
keeper> 扫描 192.168.1.100 的安全漏洞

[端口扫描] 发现 12 个开放端口
[服务识别] SSH(22), HTTP(80), MySQL(3306)...
[风险检测] ⚠️ 发现 2 个中风险项

1. SSH 使用密码登录 (建议改用密钥)
2. MySQL 绑定 0.0.0.0 (建议限制 IP)
```

### 5. 配置管理

支持多环境配置，通过对话修改：

```
keeper> 保存生产环境的主机列表
好的，已创建 production 环境，包含 3 台主机

keeper> 切换到 dev 环境
已切换到 dev 环境，当前有 2 台主机

keeper> 显示当前配置
当前环境：dev
主机列表:
  - 192.168.1.100 (CPU 阈值：80%)
  - 192.168.1.101 (CPU 阈值：80%)
```

---

## 命令参考

### 交互模式

```bash
keeper          # 启动交互式对话
```

### 单命令模式

```bash
keeper "检查 192.168.1.100"               # 自然语言命令
keeper "巡检" --host 192.168.1.100        # 带参数
keeper "扫描漏洞" --profile production    # 使用配置
```

### 支持的意图

| 意图 | 说明 | 示例 |
|------|------|------|
| inspect | 服务器巡检 | "检查 192.168.1.100", "看看这台机器健康吗" |
| scan | 漏洞扫描 | "扫描漏洞", "检查有没有安全问题" |
| config | 配置管理 | "保存配置", "切换到 production" |
| logs | 日志查询 | "查看最近的操作", "显示昨天的告警" |
| help | 帮助 | "你能做什么？", "帮助" |

---

## 技术架构

### 技术栈

| 组件 | 技术选型 | 说明 |
|------|----------|------|
| CLI 框架 | Click + Prompt Toolkit | 命令行解析 + 交互式输入 |
| NLU 引擎 | LangChain + LLM | 自然语言理解 |
| LLM 提供商 | OpenAI 兼容 / Anthropic | 支持多种 API |
| 系统监控 | psutil | 资源采集 |
| 漏洞扫描 | Nmap | 端口/服务扫描 |
| 配置管理 | PyYAML | YAML 解析 |
| 日志 | logging | 结构化日志 |

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
│   │   ├── memory.py     # 对话记忆
│   │   └── context.py    # 上下文管理
│   └── tools/
│       ├── server.py     # 服务器工具
│       └── scanner.py    # 扫描工具
├── tests/
├── requirements.txt
└── config.yaml
```

### NLU 解析流程

```
用户输入 → LangChain + LLM → 意图识别 → 参数提取 → 工具调用 → 结果生成 → 回复用户
                              ↓
                        上下文记忆 (指代消解)
```

### 支持的 LLM 提供商

| 提供商 | Base URL | 推荐模型 |
|--------|----------|----------|
| OpenAI 兼容 | https://api.qnaigc.com/v1 | claude-sonnet-4-6 |
| Anthropic | https://api.qnaigc.com | claude-sonnet-4-6 |

---

## 记忆系统

### 短期记忆（会话内）
- 保留最近 10 轮对话
- 记住上下文中的实体（主机、环境、阈值等）
- 支持指代消解（"它"、"这台"、"那台"）
- 会话结束即清除

### 长期记忆（持久化）
- 用户配置偏好
- 常用主机列表
- 历史巡检记录
- YAML 文件存储于 `~/.keeper/`

### 上下文示例

```
用户："检查 192.168.1.100"           → 记住当前主机
 Keeper："CPU 45%，内存 62%..."
用户："那 192.168.1.101 呢？"        → 理解"呢"表示同样操作
 Keeper："正在检查 192.168.1.101..."
用户："把它的阈值调到 75%"           → "它"指代上一台主机
 Keeper："已更新 192.168.1.101 的阈值为 75%"
```

---

## 配置

### 环境变量

```bash
# 必需
export KEEPER_API_KEY='your-api-key'
export KEEPER_BASE_URL='https://api.qnaigc.com/v1'
export KEEPER_PROVIDER='openai_compatible'  # 或 anthropic

# 可选
export KEEPER_MODEL='claude-sonnet-4-6'
export KEEPER_LOG_LEVEL='INFO'
```

### 配置文件

```yaml
# ~/.keeper/config.yaml
current_profile: dev

profiles:
  dev:
    hosts:
      - 192.168.1.100
      - 192.168.1.101
    thresholds:
      cpu: 80
      memory: 85
      disk: 90

  production:
    hosts:
      - 10.0.0.1
      - 10.0.0.2
    thresholds:
      cpu: 70
      memory: 80
      disk: 85
```

---

## 安全设计

### 操作审计

所有操作记录到 `~/.keeper/audit.log`:

```json
{"timestamp": "2026-04-08T10:00:00Z", "user": "gaoyuan", "intent": "server_inspect", "host": "192.168.1.100", "result": "success"}
```

### 高危操作确认

以下操作需要二次确认：
- 删除配置文件
- 批量操作 (>5 台主机)
- 执行系统修改命令

### 敏感信息保护
- API Key 通过环境变量注入
- 配置文件不存储明文密码
- 审计日志脱敏处理

---

## 开发计划

### Phase 1 - MVP (当前)
- [ ] CLI 框架搭建 (Click + Prompt Toolkit)
- [ ] 交互模式入口 (`keeper` 命令)
- [ ] LangChain NLU 引擎
- [ ] 服务器资源巡检
- [ ] 对话记忆系统

### Phase 2
- [ ] 漏洞扫描集成 (Nmap)
- [ ] 报告生成 (JSON/文本)
- [ ] 多主机批量巡检
- [ ] 配置持久化

### Phase 3
- [ ] 智能告警分析
- [ ] 自动修复建议
- [ ] 更多 LLM 提供商支持

---

## 开发环境

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装开发依赖
pip install -r requirements-dev.txt

# 运行测试
pytest tests/

# 代码检查
flake8 keeper/
black --check keeper/
```

---

## 常见问题

**Q: 如何在本地测试？**
A: 使用 `keeper` 进入交互模式，或在本地机器运行 `keeper "检查 localhost"`

**Q: 配置文件在哪里？**
A: `~/.keeper/config.yaml`，首次运行自动创建

**Q: 如何查看日志？**
A: `keeper "查看最近日志"` 或查看 `~/.keeper/audit.log`

**Q: 支持哪些 LLM？**
A: 支持 OpenAI 兼容 API 和 Anthropic API，通过 `KEEPER_PROVIDER` 切换

**Q: 没有 API Key 能用吗？**
A: 需要配置 LLM API Key 才能使用自然语言理解功能

---

## License

MIT
