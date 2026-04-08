"""服务器工具 - 资源采集和监控"""
import psutil
import socket
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class ServerStatus:
    """服务器状态"""
    host: str
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    load_avg_1m: float
    load_avg_5m: float
    load_avg_15m: float
    boot_time: str
    top_processes: List[Dict[str, Any]]


class ServerTools:
    """服务器工具类"""

    @staticmethod
    def get_hostname() -> str:
        """获取主机名"""
        return socket.gethostname()

    @staticmethod
    def get_cpu_percent() -> float:
        """获取 CPU 使用率"""
        return psutil.cpu_percent(interval=0.5)

    @staticmethod
    def get_memory_info() -> Dict[str, float]:
        """获取内存信息"""
        mem = psutil.virtual_memory()
        return {
            "percent": mem.percent,
            "used_gb": mem.used / (1024 ** 3),
            "total_gb": mem.total / (1024 ** 3),
        }

    @staticmethod
    def get_disk_info(path: str = "/") -> Dict[str, float]:
        """获取磁盘信息"""
        disk = psutil.disk_usage(path)
        return {
            "percent": disk.percent,
            "used_gb": disk.used / (1024 ** 3),
            "total_gb": disk.total / (1024 ** 3),
        }

    @staticmethod
    def get_load_avg() -> Dict[str, float]:
        """获取系统负载"""
        try:
            load1, load5, load15 = psutil.getloadavg()
        except (AttributeError, OSError):
            # Windows 不支持
            load1 = load5 = load15 = psutil.cpu_percent() / 100.0
        return {
            "1m": load1,
            "5m": load5,
            "15m": load15,
        }

    @staticmethod
    def get_top_processes(n: int = 5) -> List[Dict[str, Any]]:
        """获取资源占用 Top N 进程"""
        processes = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = proc.info
                processes.append({
                    "pid": info["pid"],
                    "name": info["name"],
                    "cpu_percent": info["cpu_percent"] or 0,
                    "memory_percent": info["memory_percent"] or 0,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # 按内存占用排序
        processes.sort(key=lambda x: x["memory_percent"], reverse=True)
        return processes[:n]

    @staticmethod
    def get_boot_time() -> str:
        """获取开机时间"""
        boot_timestamp = psutil.boot_time()
        return datetime.fromtimestamp(boot_timestamp).strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def inspect_server(cls, host: Optional[str] = None) -> ServerStatus:
        """巡检服务器状态

        Args:
            host: 主机名或 IP，None 表示本地

        Returns:
            ServerStatus: 服务器状态
        """
        target_host = host or cls.get_hostname()

        # 如果是本地，直接采集
        if host in (None, "localhost", "127.0.0.1", cls.get_hostname()):
            return ServerStatus(
                host=target_host,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                cpu_percent=cls.get_cpu_percent(),
                memory_percent=cls.get_memory_info()["percent"],
                memory_used_gb=cls.get_memory_info()["used_gb"],
                memory_total_gb=cls.get_memory_info()["total_gb"],
                disk_percent=cls.get_disk_info()["percent"],
                disk_used_gb=cls.get_disk_info()["used_gb"],
                disk_total_gb=cls.get_disk_info()["total_gb"],
                load_avg_1m=cls.get_load_avg()["1m"],
                load_avg_5m=cls.get_load_avg()["5m"],
                load_avg_15m=cls.get_load_avg()["15m"],
                boot_time=cls.get_boot_time(),
                top_processes=cls.get_top_processes(5),
            )
        else:
            # TODO: 远程主机采集（需要 SSH 或 Agent）
            raise NotImplementedError(f"远程主机 {host} 的采集功能尚未实现")


def format_status_report(status: ServerStatus, thresholds: Dict[str, int]) -> str:
    """格式化状态报告

    Args:
        status: 服务器状态
        thresholds: 阈值配置 {"cpu": 80, "memory": 85, "disk": 90}

    Returns:
        str: 格式化的报告文本
    """
    lines = []
    lines.append(f"[✓] 服务器健康检查 - {status.host}")
    lines.append("━" * 40)

    # CPU
    cpu_ok = status.cpu_percent < thresholds.get("cpu", 80)
    cpu_icon = "✓" if cpu_ok else "⚠️"
    lines.append(f"  CPU:     {status.cpu_percent:.1f}%  (阈值：{thresholds.get('cpu', 80)}%)  {cpu_icon}")

    # 内存
    mem_ok = status.memory_percent < thresholds.get("memory", 85)
    mem_icon = "✓" if mem_ok else "⚠️"
    lines.append(f"  内存：   {status.memory_percent:.1f}%  (阈值：{thresholds.get('memory', 85)}%)  {mem_icon}")
    lines.append(f"         已用：{status.memory_used_gb:.2f}GB / {status.memory_total_gb:.2f}GB")

    # 磁盘
    disk_ok = status.disk_percent < thresholds.get("disk", 90)
    disk_icon = "✓" if disk_ok else "⚠️"
    lines.append(f"  磁盘：   {status.disk_percent:.1f}%  (阈值：{thresholds.get('disk', 90)}%)  {disk_icon}")
    lines.append(f"         已用：{status.disk_used_gb:.2f}GB / {status.disk_total_gb:.2f}GB")

    # 负载
    cpu_cores = psutil.cpu_count() or 1
    load_threshold = cpu_cores * 2
    load_ok = status.load_avg_1m < load_threshold
    load_icon = "✓" if load_ok else "⚠️"
    lines.append(f"  负载：   {status.load_avg_1m:.2f}  (阈值：{load_threshold})  {load_icon}")
    lines.append(f"         1 分钟:{status.load_avg_1m:.2f} | 5 分钟:{status.load_avg_5m:.2f} | 15 分钟:{status.load_avg_15m:.2f}")

    # 开机时间
    lines.append(f"  开机时间：{status.boot_time}")

    # Top 进程
    lines.append("\n  资源占用 Top 进程:")
    for i, proc in enumerate(status.top_processes, 1):
        lines.append(f"    {i}. {proc['name']} (PID:{proc['pid']}) - 内存:{proc['memory_percent']:.1f}%")

    # 健康评分
    issues = sum([
        0 if cpu_ok else 1,
        0 if mem_ok else 1,
        0 if disk_ok else 1,
        0 if load_ok else 1,
    ])
    score = max(0, 100 - issues * 15)
    lines.append(f"\n健康评分：{score}/100")

    if issues == 0:
        lines.append("状态：✅ 所有指标正常")
    else:
        lines.append(f"状态：⚠️ 发现 {issues} 项异常")

    return "\n".join(lines)
