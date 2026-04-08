"""SSH 远程执行工具"""
import subprocess
from dataclasses import dataclass
from typing import Optional, Tuple


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


def format_ssh_result(success: bool, output: str, command: str) -> str:
    """格式化 SSH 执行结果"""
    if success:
        return f"[✓] 命令执行成功:\n{output}"
    else:
        return f"[✗] 命令执行失败:\n{output}"
