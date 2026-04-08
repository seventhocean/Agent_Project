#!/usr/bin/env python3
"""
Keeper 功能演示脚本

运行此脚本测试 Keeper 的核心功能（无需 API Key）
"""

from keeper.tools.server import ServerTools, format_status_report
from keeper.tools.scanner import ScannerTools, format_scan_result
from keeper.core.context import ContextManager, MemoryManager

def demo_server_inspect():
    """演示服务器巡检功能"""
    print("=" * 50)
    print("演示：服务器资源巡检")
    print("=" * 50)

    # 巡检本地服务器
    status = ServerTools.inspect_server("localhost")

    # 使用默认阈值生成报告
    thresholds = {"cpu": 80, "memory": 85, "disk": 90}
    report = format_status_report(status, thresholds)

    print(report)
    print()


def demo_context_memory():
    """演示上下文和记忆系统"""
    print("=" * 50)
    print("演示：上下文和记忆系统")
    print("=" * 50)

    # 上下文管理
    ctx = ContextManager()
    ctx.update("inspect", {"host": "192.168.1.100", "threshold": 80})

    print(f"当前主机：{ctx.current_host}")
    print(f"上一个意图：{ctx.last_intent}")
    print(f"阈值：{ctx.get('threshold')}")

    # 记忆管理
    memory = MemoryManager()
    memory.add_turn("检查 192.168.1.100", "CPU 45%", "inspect", {"host": "192.168.1.100"})
    memory.add_turn("扫描漏洞", "发现 2 个风险", "scan", {"host": "192.168.1.100"})

    print(f"\n记忆中的对话轮次：{len(memory.turns)}")
    print(f"提到的主机：{memory.get_hosts_mentioned()}")
    print()


def demo_scanner():
    """演示扫描功能（仅本地测试）"""
    print("=" * 50)
    print("演示：端口扫描（仅测试工具类）")
    print("=" * 50)

    # 演示工具类的风险解析功能
    from keeper.tools.scanner import PortInfo

    # 模拟扫描结果
    open_ports = [
        PortInfo(port=22, protocol="tcp", state="open", service="ssh", version="OpenSSH 8.9"),
        PortInfo(port=80, protocol="tcp", state="open", service="http", version="nginx 1.18"),
        PortInfo(port=443, protocol="tcp", state="open", service="https", version="nginx 1.18"),
        PortInfo(port=3306, protocol="tcp", state="open", service="mysql", version="MySQL 8.0"),
    ]

    risks = ScannerTools._analyze_risks(open_ports)

    print(f"开放端口：{len(open_ports)} 个")
    for port in open_ports:
        print(f"  {port.port}/{port.protocol}  {port.service} ({port.version})")

    print(f"\n风险检测：{len(risks)} 项")
    if risks:
        for risk in risks:
            level_icon = "🔴" if risk["level"] == "high" else "🟡"
            print(f"  {level_icon} 端口 {risk['port']} ({risk['service']}): {risk['description']}")
    else:
        print("  ✅ 未发现明显风险")
    print()


def main():
    """运行所有演示"""
    print("\n🔧 Keeper 功能演示\n")

    # 演示 1：服务器巡检
    demo_server_inspect()

    # 演示 2：上下文记忆
    demo_context_memory()

    # 演示 3：扫描功能
    demo_scanner()

    print("=" * 50)
    print("演示完成！")
    print("=" * 50)
    print("\n提示：设置 API Key 后可以运行 'keeper chat' 体验完整功能")
    print()


if __name__ == "__main__":
    main()
