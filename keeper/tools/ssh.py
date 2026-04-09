"""SSH 远程执行工具"""
import subprocess
import json
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict, Any


@dataclass
class SSHConfig:
    """SSH 配置"""
    host: str
    port: int = 22
    username: str = "root"
    password: Optional[str] = None
    key_file: Optional[str] = None


class SSHTools:
    """SSH 工具类（使用系统 ssh 命令，避免额外依赖）"""

    @classmethod
    def test_connection(cls, host: str, username: str = "root") -> bool:
        """测试 SSH 连接"""
        try:
            result = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
                 f"{username}@{host}", "echo OK"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def execute(cls, config: SSHConfig, command: str) -> Tuple[bool, str]:
        """执行远程命令

        Args:
            config: SSH 配置
            command: 要执行的命令

        Returns:
            (成功标志，输出/错误信息)
        """
        # 构建 SSH 命令
        ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=no"]

        if config.key_file:
            ssh_cmd.extend(["-i", config.key_file])

        ssh_cmd.extend([
            "-p", str(config.port),
            f"{config.username}@{config.host}",
            command,
        ])

        try:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr

        except subprocess.TimeoutExpired:
            return False, "命令执行超时"
        except FileNotFoundError:
            return False, "未找到 ssh 命令，请安装 openssh-client"
        except Exception as e:
            return False, f"执行失败：{str(e)}"

    @classmethod
    def install_package(cls, config: SSHConfig, package: str) -> Tuple[bool, str]:
        """安装软件包

        Args:
            config: SSH 配置
            package: 包名

        Returns:
            (成功标志，输出信息)
        """
        # 检测包管理器
        commands = {
            "apt": f"sudo apt-get update && sudo apt-get install -y {package}",
            "yum": f"sudo yum install -y {package}",
            "dnf": f"sudo dnf install -y {package}",
            "pacman": f"sudo pacman -S --noconfirm {package}",
            "brew": f"brew install {package}",
        }

        # 尝试不同的包管理器
        for pkg_manager, cmd in commands.items():
            success, output = cls.execute(config, f"which {pkg_manager}")
            if success and pkg_manager in output:
                return cls.execute(config, cmd)

        return False, "未找到支持的包管理器"

    @classmethod
    def get_os_info(cls, config: SSHConfig) -> str:
        """获取远程系统信息"""
        success, output = cls.execute(config, "cat /etc/os-release 2>/dev/null || uname -a")
        if success:
            return output
        return "未知系统"

    @classmethod
    def collect_server_status(cls, config: SSHConfig) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """通过 SSH 采集服务器状态

        Args:
            config: SSH 配置

        Returns:
            (成功标志，状态字典或 None)
        """
        # Python 采集脚本（base64 编码避免转义问题）
        python_script = '''
import psutil
import socket
import json
from datetime import datetime

def get_info():
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    try:
        load1, load5, load15 = psutil.getloadavg()
    except:
        load1 = load5 = load15 = psutil.cpu_percent() / 100.0

    processes = []
    for proc in psutil.process_iter(["pid", "name", "memory_percent"]):
        try:
            info = proc.info
            processes.append({
                "pid": info["pid"],
                "name": info["name"],
                "memory_percent": info["memory_percent"] or 0,
            })
        except:
            continue
    processes.sort(key=lambda x: x["memory_percent"], reverse=True)

    return {
        "host": socket.gethostname(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "memory_percent": mem.percent,
        "memory_used_gb": mem.used / (1024 ** 3),
        "memory_total_gb": mem.total / (1024 ** 3),
        "disk_percent": disk.percent,
        "disk_used_gb": disk.used / (1024 ** 3),
        "disk_total_gb": disk.total / (1024 ** 3),
        "load_avg_1m": load1,
        "load_avg_5m": load5,
        "load_avg_15m": load15,
        "boot_time": datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S"),
        "top_processes": processes[:5],
    }

print(json.dumps(get_info()))
'''

        # 通过 SSH 执行 Python 脚本
        cmd = f"python3 -c \"{python_script.replace(chr(10), ';')}\""
        success, output = cls.execute(config, cmd)

        if not success:
            return False, None

        try:
            # 解析 JSON 输出
            status_dict = json.loads(output.strip())
            return True, status_dict
        except (json.JSONDecodeError, Exception):
            return False, None

    @classmethod
    def get_hosts_from_file(cls, hosts_file: str = "/etc/hosts") -> List[str]:
        """从 hosts 文件读取主机列表

        Args:
            hosts_file: hosts 文件路径

        Returns:
            主机 IP 列表
        """
        hosts = []
        try:
            with open(hosts_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    # 跳过注释和空行
                    if not line or line.startswith('#'):
                        continue
                    # 解析 hosts 格式：IP  hostname [alias...]
                    parts = line.split()
                    if len(parts) >= 2:
                        ip = parts[0]
                        # 跳过 IPv6 和本地回环
                        if ':' in ip or ip == '127.0.0.1':
                            continue
                        hosts.append(ip)
        except (FileNotFoundError, PermissionError):
            return []
        return hosts


def format_ssh_result(success: bool, output: str, command: str) -> str:
    """格式化 SSH 执行结果"""
    if success:
        return f"[✓] 命令执行成功:\n{output}"
    else:
        return f"[✗] 命令执行失败:\n{output}"
