"""智能根因分析引擎 (RCA)"""
import subprocess
import json
import re
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass


@dataclass
class RCADiagnosis:
    """RCA 诊断结果"""
    summary: str  # 问题摘要
    symptoms: List[str]  # 观察到的症状
    possible_causes: List[str]  # 可能原因
    suggestions: List[str]  # 建议操作
    confidence: str  # 置信度 (high/medium/low)
    raw_data: Dict[str, Any]  # 原始数据


class RCAEngine:
    """根因分析引擎"""

    @classmethod
    def collect_server_data(cls, host: str = "localhost") -> Dict[str, Any]:
        """采集服务器全维度数据"""
        import psutil

        data = {}

        # CPU
        data["cpu_percent"] = psutil.cpu_percent(interval=1)
        data["cpu_count"] = psutil.cpu_count()
        data["cpu_freq"] = psutil.cpu_freq()
        if data["cpu_freq"]:
            data["cpu_freq_mhz"] = round(data["cpu_freq"].current, 1)

        # Memory
        mem = psutil.virtual_memory()
        data["memory_percent"] = mem.percent
        data["memory_used_gb"] = round(mem.used / (1024 ** 3), 2)
        data["memory_total_gb"] = round(mem.total / (1024 ** 3), 2)
        data["memory_available_gb"] = round(mem.available / (1024 ** 3), 2)

        # Swap
        swap = psutil.swap_memory()
        data["swap_percent"] = swap.percent
        data["swap_used_gb"] = round(swap.used / (1024 ** 3), 2)

        # Disk
        disk = psutil.disk_usage("/")
        data["disk_percent"] = disk.percent
        data["disk_used_gb"] = round(disk.used / (1024 ** 3), 2)
        data["disk_total_gb"] = round(disk.total / (1024 ** 3), 2)

        # Load
        try:
            load1, load5, load15 = psutil.getloadavg()
            data["load_avg"] = {"1m": round(load1, 2), "5m": round(load5, 2), "15m": round(load15, 2)}
            data["load_per_cpu"] = round(load1 / (psutil.cpu_count() or 1), 2)
        except Exception:
            data["load_avg"] = {}

        # Top processes
        procs = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
            try:
                info = proc.info
                procs.append({
                    "pid": info["pid"],
                    "name": info["name"],
                    "cpu_percent": info["cpu_percent"] or 0,
                    "memory_percent": info["memory_percent"] or 0,
                    "status": info["status"],
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        procs.sort(key=lambda x: x["cpu_percent"], reverse=True)
        data["top_cpu_processes"] = procs[:10]

        procs.sort(key=lambda x: x["memory_percent"], reverse=True)
        data["top_memory_processes"] = procs[:10]

        # 系统运行时间
        boot_time = psutil.boot_time()
        import datetime
        uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(boot_time)
        data["uptime"] = str(uptime).split(".")[0]

        # 网络统计
        net_io = psutil.net_io_counters()
        data["network"] = {
            "bytes_sent_mb": round(net_io.bytes_sent / (1024 ** 2), 1),
            "bytes_recv_mb": round(net_io.bytes_recv / (1024 ** 2), 1),
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
            "errin": net_io.errin,
            "errout": net_io.errout,
        }

        # journalctl 错误日志摘要
        try:
            cmd = ["journalctl", "--no-pager", "-n", "50", "-p", "err", "--no-hostname"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            err_logs = result.stdout.strip()
            data["error_logs"] = err_logs[:2000] if err_logs else ""
        except Exception:
            data["error_logs"] = ""

        return data

    @classmethod
    def analyze_server(cls, data: Dict[str, Any]) -> str:
        """生成服务器诊断报告文本（供 LLM 消费）"""
        lines = ["=== 服务器诊断数据 ===\n"]

        # 基本信息
        lines.append(f"CPU 使用率: {data['cpu_percent']}% ({data['cpu_count']} 核心)")
        if data.get("cpu_freq_mhz"):
            lines.append(f"CPU 频率: {data['cpu_freq_mhz']}MHz")
        lines.append(f"内存使用: {data['memory_percent']}% ({data['memory_used_gb']}GB / {data['memory_total_gb']}GB)")
        lines.append(f"可用内存: {data['memory_available_gb']}GB")
        if data["swap_percent"] > 0:
            lines.append(f"Swap 使用: {data['swap_percent']}% ({data['swap_used_gb']}GB)")
        lines.append(f"磁盘使用: {data['disk_percent']}% ({data['disk_used_gb']}GB / {data['disk_total_gb']}GB)")
        lines.append(f"系统运行: {data['uptime']}")
        lines.append("")

        # 负载
        if data.get("load_avg"):
            load = data["load_avg"]
            lines.append(f"系统负载: 1m={load['1m']}, 5m={load['5m']}, 15m={load['15m']}")
            if data.get("load_per_cpu"):
                status = "偏高" if data["load_per_cpu"] > 1.5 else "正常"
                lines.append(f"每核心负载: {data['load_per_cpu']} ({status})")
            lines.append("")

        # Top CPU 进程
        lines.append("Top CPU 进程:")
        for i, p in enumerate(data.get("top_cpu_processes", [])[:5], 1):
            lines.append(f"  {i}. {p['name']} (PID:{p['pid']}) CPU:{p['cpu_percent']}% MEM:{p['memory_percent']}%")
        lines.append("")

        # Top Memory 进程
        lines.append("Top 内存进程:")
        for i, p in enumerate(data.get("top_memory_processes", [])[:5], 1):
            lines.append(f"  {i}. {p['name']} (PID:{p['pid']}) CPU:{p['cpu_percent']}% MEM:{p['memory_percent']}%")
        lines.append("")

        # 网络
        net = data.get("network", {})
        if net:
            lines.append(f"网络: 发送 {net.get('bytes_sent_mb', 0)}MB, 接收 {net.get('bytes_recv_mb', 0)}MB")
            if net.get("errin", 0) > 0 or net.get("errout", 0) > 0:
                lines.append(f"⚠ 网络错误: 入 {net['errin']}, 出 {net['errout']}")
            lines.append("")

        # 错误日志
        if data.get("error_logs"):
            lines.append("错误日志摘要 (最近 50 条):")
            lines.append(data["error_logs"][:1500])
            lines.append("")

        return "\n".join(lines)

    @classmethod
    def compare_hosts(
        cls,
        data_a: Dict[str, Any],
        data_b: Dict[str, Any],
        host_a: str,
        host_b: str,
    ) -> str:
        """生成双机对比报告文本"""
        lines = [f"=== 服务器对比分析: {host_a} vs {host_b} ===\n"]

        comparisons = [
            ("CPU 使用率", "cpu_percent", "%"),
            ("内存使用", "memory_percent", "%"),
            ("磁盘使用", "disk_percent", "%"),
            ("内存总量", "memory_total_gb", "GB"),
            ("Swap 使用", "swap_percent", "%"),
        ]

        for label, key, unit in comparisons:
            va = data_a.get(key, "N/A")
            vb = data_b.get(key, "N/A")
            diff = ""
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                delta = va - vb
                if abs(delta) > 5:
                    diff = f" (差异: {delta:+.1f}{unit})"
            lines.append(f"{label}: {host_a}={va}{unit} vs {host_b}={vb}{unit}{diff}")

        # 负载对比
        load_a = data_a.get("load_avg", {})
        load_b = data_b.get("load_avg", {})
        if load_a and load_b:
            lines.append(f"\n系统负载 1m: {host_a}={load_a.get('1m', 'N/A')} vs {host_b}={load_b.get('1m', 'N/A')}")

        # 进程对比
        top_cpu_a = data_a.get("top_cpu_processes", [])
        top_cpu_b = data_b.get("top_cpu_processes", [])
        if top_cpu_a and top_cpu_b:
            lines.append(f"\n{host_a} Top CPU 进程:")
            for i, p in enumerate(top_cpu_a[:3], 1):
                lines.append(f"  {i}. {p['name']} CPU:{p['cpu_percent']}%")
            lines.append(f"\n{host_b} Top CPU 进程:")
            for i, p in enumerate(top_cpu_b[:3], 1):
                lines.append(f"  {i}. {p['name']} CPU:{p['cpu_percent']}%")

        return "\n".join(lines)

    @classmethod
    def collect_k8s_rca_data(cls, k8s_client) -> str:
        """收集 K8s 集群异常数据"""
        lines = ["=== K8s 集群异常数据 ===\n"]

        try:
            # 异常 Pods
            all_pods = k8s_client.core_v1.list_pod_for_all_namespaces()
            abnormal = []
            for pod in all_pods.items:
                phase = pod.status.phase
                if phase in ("Pending", "Failed", "Unknown"):
                    reasons = []
                    for cs in (pod.status.container_statuses or []):
                        if cs.state.waiting:
                            reasons.append(f"{cs.name}: {cs.state.waiting.reason}")
                        if cs.state.terminated:
                            reasons.append(f"{cs.name}: {cs.state.terminated.reason}")
                            if cs.state.terminated.exit_code:
                                reasons.append(f"  exit_code={cs.state.terminated.exit_code}")
                    restarts = sum(cs.restart_count for cs in (pod.status.container_statuses or []))
                    abnormal.append({
                        "name": f"{pod.metadata.namespace}/{pod.metadata.name}",
                        "phase": phase,
                        "reasons": reasons,
                        "restarts": restarts,
                        "node": pod.spec.node_name or "unscheduled",
                    })

            if abnormal:
                lines.append(f"异常 Pod ({len(abnormal)} 个):")
                for p in abnormal:
                    lines.append(f"  - {p['name']} phase={p['phase']} node={p['node']} restarts={p['restarts']}")
                    for r in p["reasons"]:
                        lines.append(f"    {r}")
            else:
                lines.append("未发现异常 Pod")

            # Warning 事件
            events = k8s_client.core_v1.list_event_for_all_namespaces(
                field_selector="type=Warning",
            )
            if events.items:
                lines.append(f"\nWarning 事件 ({len(events.items)} 条，最近 20 条):")
                sorted_events = sorted(
                    events.items,
                    key=lambda e: e.last_timestamp or e.event_time or __import__("datetime").datetime.min,
                    reverse=True,
                )[:20]
                for ev in sorted_events:
                    obj = ev.involved_object
                    obj_ref = f"{obj.kind}/{obj.name}"
                    ts = ev.last_timestamp or ev.event_time
                    lines.append(f"  - {obj.metadata.namespace}/{obj_ref}: {ev.reason} - {ev.message[:100]} [{ts}]")
            else:
                lines.append("\n无 Warning 事件")

        except Exception as e:
            lines.append(f"采集失败: {str(e)}")

        return "\n".join(lines)

    @classmethod
    def generate_diagnosis_prompt(cls, data_text: str, symptom: str = "") -> str:
        """生成 LLM 诊断 Prompt"""
        prompt = f"""你是一个资深运维工程师，请根据以下服务器监控数据进行分析。

## 监控数据
{data_text}

## 分析要求
请按照以下格式回复：

**问题摘要：** 一句话概括当前系统状态
**健康状况：** 健康 / 需要注意 / 异常
**观察到的症状：** 列出所有异常指标（使用项目符号）
**可能原因：** 按可能性从高到低排列
**建议操作：** 具体可执行的命令或步骤
**风险评估：** 高 / 中 / 低

请简洁明了，优先关注实际可能影响服务的问题。"""

        if symptom:
            prompt = f"""你是一个资深运维工程师，用户反馈的症状是：{symptom}

请根据以下服务器监控数据进行分析，重点关注可能导致该症状的原因。

## 监控数据
{data_text}

## 分析要求
请按照以下格式回复：

**问题摘要：** 针对 "{symptom}" 的诊断结论
**健康状况：** 健康 / 需要注意 / 异常
**观察到的症状：** 列出所有异常指标
**可能原因：** 结合用户反馈的症状，按可能性排列
**建议操作：** 具体可执行的命令或步骤
**风险评估：** 高 / 中 / 低"""

        return prompt

    @classmethod
    def generate_compare_prompt(cls, compare_text: str) -> str:
        """生成 LLM 对比分析 Prompt"""
        return f"""你是一个资深运维工程师，请分析以下两台服务器的差异。

## 对比数据
{compare_text}

## 分析要求
请分析：
1. 两台机器的主要差异是什么？
2. 这些差异是否可能导致性能问题？
3. 是否有配置不一致的风险？
4. 建议如何优化？

请简洁明了地回答。"""

    @classmethod
    def generate_k8s_diagnosis_prompt(cls, k8s_text: str) -> str:
        """生成 K8s 诊断 Prompt"""
        return f"""你是一个资深 K8s 运维工程师，请分析以下集群异常数据。

## 集群异常数据
{k8s_text}

## 分析要求
1. 识别最关键的问题
2. 分析可能的根因
3. 给出修复建议（包含具体的 kubectl 命令）
4. 评估对业务的影响

请简洁明了地回答。"""
