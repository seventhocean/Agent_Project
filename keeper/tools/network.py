"""网络诊断工具"""
import socket
import subprocess
import re
from typing import Optional, Dict, Any, Tuple, List


class NetworkTools:
    """网络诊断工具类"""

    @classmethod
    def ping(cls, host: str, count: int = 4, timeout: int = 10) -> Dict[str, Any]:
        """Ping 测试

        Args:
            host: 目标主机
            count: 发送包数
            timeout: 超时秒数

        Returns:
            诊断结果字典
        """
        try:
            # Linux ping 命令
            cmd = ["ping", "-c", str(count), "-W", "2", host]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

            output = result.stdout + result.stderr

            # 解析 ping 统计
            rtt_match = re.search(
                r"rtt min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)",
                output,
            )
            packet_match = re.search(
                r"(\d+) packets? transmitted, (\d+) (?:packets? )?received, (\d+)% packet loss",
                output,
            )

            info: Dict[str, Any] = {
                "host": host,
                "success": result.returncode == 0,
                "packet_sent": 0,
                "packet_received": 0,
                "packet_loss": 100.0,
                "rtt_min": 0,
                "rtt_avg": 0,
                "rtt_max": 0,
                "reachable": False,
            }

            if packet_match:
                info["packet_sent"] = int(packet_match.group(1))
                info["packet_received"] = int(packet_match.group(2))
                info["packet_loss"] = float(packet_match.group(3))
                info["reachable"] = info["packet_received"] > 0

            if rtt_match:
                info["rtt_min"] = float(rtt_match.group(1))
                info["rtt_avg"] = float(rtt_match.group(2))
                info["rtt_max"] = float(rtt_match.group(3))

            return info
        except subprocess.TimeoutExpired:
            return {
                "host": host,
                "success": False,
                "reachable": False,
                "packet_loss": 100.0,
                "error": "Ping 超时",
            }
        except FileNotFoundError:
            return {
                "host": host,
                "success": False,
                "reachable": False,
                "packet_loss": 100.0,
                "error": "未找到 ping 命令",
            }
        except Exception as e:
            return {
                "host": host,
                "success": False,
                "reachable": False,
                "packet_loss": 100.0,
                "error": str(e),
            }

    @classmethod
    def check_port(cls, host: str, port: int, timeout: int = 5) -> Dict[str, Any]:
        """端口连通性检测

        Args:
            host: 目标主机
            port: 目标端口
            timeout: 超时秒数

        Returns:
            诊断结果
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            start_time = __import__("time").time()
            result_code = sock.connect_ex((host, port))
            elapsed = (__import__("time").time() - start_time) * 1000
            sock.close()

            return {
                "host": host,
                "port": port,
                "open": result_code == 0,
                "response_time_ms": round(elapsed, 2),
                "error": None,
            }
        except socket.timeout:
            return {
                "host": host,
                "port": port,
                "open": False,
                "response_time_ms": timeout * 1000,
                "error": "连接超时",
            }
        except socket.gaierror:
            return {
                "host": host,
                "port": port,
                "open": False,
                "response_time_ms": 0,
                "error": f"无法解析主机名: {host}",
            }
        except Exception as e:
            return {
                "host": host,
                "port": port,
                "open": False,
                "response_time_ms": 0,
                "error": str(e),
            }

    @classmethod
    def dns_lookup(cls, domain: str, server: Optional[str] = None) -> Dict[str, Any]:
        """DNS 解析

        Args:
            domain: 域名
            server: DNS 服务器（可选）

        Returns:
            解析结果
        """
        try:
            # 使用 dig 命令
            cmd = ["dig", "+short", domain]
            if server:
                cmd.append(f"@{server}")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            output = result.stdout.strip()

            # 同时获取解析时间
            cmd_full = ["dig", "+stats", domain]
            if server:
                cmd_full.append(f"@{server}")
            result_full = subprocess.run(cmd_full, capture_output=True, text=True, timeout=15)
            full_output = result_full.stdout

            # 提取解析时间
            time_match = re.search(r"Query time: (\d+) msec", full_output)
            query_time = int(time_match.group(1)) if time_match else 0

            # 提取 DNS 服务器
            server_match = re.search(r"SERVER: ([\d.:a-f#]+)", full_output)
            dns_server = server_match.group(1) if server_match else "unknown"

            # 提取 IP 地址
            ips = [line.strip() for line in output.split("\n") if line.strip()]
            # 过滤掉非 IP 行（如 CNAME）
            a_records = [ip for ip in ips if re.match(r"^\d+\.\d+\.\d+\.\d+$", ip)]
            cname_records = [ip for ip in ips if not re.match(r"^\d+\.\d+\.\d+\.\d+$", ip)]

            return {
                "domain": domain,
                "dns_server": dns_server,
                "query_time_ms": query_time,
                "a_records": a_records,
                "cname_records": cname_records,
                "resolved": len(a_records) > 0,
                "error": None,
            }
        except subprocess.TimeoutExpired:
            return {
                "domain": domain,
                "resolved": False,
                "error": "DNS 查询超时",
            }
        except FileNotFoundError:
            # 降级到 socket.getaddrinfo
            try:
                addrs = socket.getaddrinfo(domain, None, socket.AF_INET)
                ips = list(set([addr[4][0] for addr in addrs]))
                return {
                    "domain": domain,
                    "dns_server": "system",
                    "query_time_ms": 0,
                    "a_records": ips,
                    "cname_records": [],
                    "resolved": len(ips) > 0,
                    "error": None,
                }
            except socket.gaierror as e:
                return {
                    "domain": domain,
                    "resolved": False,
                    "error": str(e),
                }
        except Exception as e:
            return {
                "domain": domain,
                "resolved": False,
                "error": str(e),
            }

    @classmethod
    def http_check(
        cls,
        url: str,
        method: str = "GET",
        timeout: int = 10,
        expected_status: int = 200,
    ) -> Dict[str, Any]:
        """HTTP 健康检查

        Args:
            url: 目标 URL
            method: HTTP 方法
            timeout: 超时秒数
            expected_status: 期望状态码

        Returns:
            检查结果
        """
        try:
            cmd = [
                "curl", "-o", "/dev/null", "-w",
                "http_code:%{http_code}\ntime_total:%{time_total}\ntime_connect:%{time_connect}\n"
                "time_starttransfer:%{time_starttransfer}\nsize_download:%{size_download}\n"
                "redirect_url:%{redirect_url}\nssl_verify:%{ssl_verify_result}\n",
                "-s", "-L", "--max-time", str(timeout),
                "-X", method.upper(),
                url,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
            output = result.stdout

            # 解析输出
            data = {}
            for line in output.strip().split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    data[key.strip()] = value.strip()

            http_code = int(data.get("http_code", "0"))
            time_total = float(data.get("time_total", "0"))
            time_connect = float(data.get("time_connect", "0"))
            time_ttfb = float(data.get("time_starttransfer", "0"))

            return {
                "url": url,
                "method": method.upper(),
                "http_code": http_code,
                "expected_status": expected_status,
                "status_ok": http_code == expected_status,
                "reachable": http_code > 0,
                "time_total_ms": round(time_total * 1000, 2),
                "time_connect_ms": round(time_connect * 1000, 2),
                "time_ttfb_ms": round(time_ttfb * 1000, 2),
                "error": None,
            }
        except subprocess.TimeoutExpired:
            return {
                "url": url,
                "method": method.upper(),
                "reachable": False,
                "http_code": 0,
                "error": "HTTP 请求超时",
            }
        except FileNotFoundError:
            return {
                "url": url,
                "method": method.upper(),
                "reachable": False,
                "http_code": 0,
                "error": "未找到 curl 命令",
            }
        except Exception as e:
            return {
                "url": url,
                "method": method.upper(),
                "reachable": False,
                "http_code": 0,
                "error": str(e),
            }

    @classmethod
    def traceroute(cls, host: str, max_hops: int = 20) -> Tuple[bool, str]:
        """路由追踪

        Args:
            host: 目标主机
            max_hops: 最大跳数

        Returns:
            (success, output)
        """
        try:
            # 先尝试 traceroute，再尝试 tracepath
            for cmd_name in ["traceroute", "tracepath"]:
                try:
                    cmd = [cmd_name, "-m", str(max_hops), "-w", "2", host]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    if result.returncode == 0 or result.stdout.strip():
                        return True, result.stdout or result.stderr
                except FileNotFoundError:
                    continue

            return False, "未找到 traceroute 或 tracepath 命令，请安装: apt install traceroute"
        except subprocess.TimeoutExpired:
            return False, "路由追踪超时"
        except Exception as e:
            return False, f"路由追踪失败：{str(e)}"


def format_ping_result(info: Dict[str, Any]) -> str:
    """格式化 ping 结果"""
    lines = [f"[网络诊断] Ping {info['host']}:"]
    lines.append("━" * 50)

    if info.get("error"):
        lines.append(f"  ✗ {info['error']}")
        return "\n".join(lines)

    status = "✓ 可达" if info["reachable"] else "✗ 不可达"
    lines.append(f"  状态：{status}")
    lines.append(f"  数据包：{info['packet_sent']} 发送, {info['packet_received']} 接收, {info['packet_loss']}% 丢失")

    if info.get("rtt_avg"):
        lines.append(f"  延迟：min={info['rtt_min']:.1f}ms, avg={info['rtt_avg']:.1f}ms, max={info['rtt_max']:.1f}ms")

    return "\n".join(lines)


def format_port_result(info: Dict[str, Any]) -> str:
    """格式化端口检测结果"""
    lines = [f"[网络诊断] 端口检测 {info['host']}:{info['port']}:"]
    lines.append("━" * 50)

    if info.get("error"):
        lines.append(f"  ✗ {info['error']}")
    elif info["open"]:
        lines.append(f"  ✓ 端口开放 (响应时间: {info['response_time_ms']}ms)")
    else:
        lines.append(f"  ✗ 端口不可达")

    return "\n".join(lines)


def format_dns_result(info: Dict[str, Any]) -> str:
    """格式化 DNS 结果"""
    lines = [f"[网络诊断] DNS 解析 {info['domain']}:"]
    lines.append("━" * 50)

    if info.get("error"):
        lines.append(f"  ✗ {info['error']}")
        return "\n".join(lines)

    lines.append(f"  DNS 服务器：{info['dns_server']}")
    lines.append(f"  查询时间：{info['query_time_ms']}ms")

    if info["resolved"]:
        lines.append(f"  ✓ 解析成功：")
        for ip in info["a_records"]:
            lines.append(f"    {ip}")
        for cname in info.get("cname_records", []):
            lines.append(f"    CNAME: {cname}")
    else:
        lines.append(f"  ✗ 解析失败")

    return "\n".join(lines)


def format_http_result(info: Dict[str, Any]) -> str:
    """格式化 HTTP 结果"""
    lines = [f"[网络诊断] HTTP 检测 {info['method']} {info['url']}:"]
    lines.append("━" * 50)

    if info.get("error"):
        lines.append(f"  ✗ {info['error']}")
        return "\n".join(lines)

    status_ok = "✓" if info["status_ok"] else "⚠"
    lines.append(f"  {status_ok} HTTP {info['http_code']} (期望: {info['expected_status']})")
    lines.append(f"  连接时间：{info['time_connect_ms']:.0f}ms")
    lines.append(f"  首字节：  {info['time_ttfb_ms']:.0f}ms")
    lines.append(f"  总耗时：  {info['time_total_ms']:.0f}ms")

    return "\n".join(lines)
