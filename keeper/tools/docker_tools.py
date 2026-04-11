"""Docker 容器管理工具"""
import subprocess
import json
import re
from typing import List, Dict, Any, Optional, Tuple


class DockerTools:
    """Docker 容器管理工具类"""

    @classmethod
    def is_docker_available(cls) -> bool:
        """检查 Docker 是否可用"""
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @classmethod
    def list_containers(cls, all_containers: bool = True, filter_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出容器

        Args:
            all_containers: 是否包含已停止的容器
            filter_name: 按名称过滤

        Returns:
            容器信息列表
        """
        try:
            cmd = ["docker", "ps", "--format", "{{json .}", "--no-trunc"]
            if all_containers:
                cmd.insert(2, "-a")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return []

            containers = []
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    container = {
                        "id": data.get("ID", "")[:12],
                        "name": data.get("Names", ""),
                        "image": data.get("Image", ""),
                        "status": data.get("Status", ""),
                        "ports": data.get("Ports", ""),
                        "created": data.get("CreatedAt", ""),
                        "state": data.get("State", ""),
                    }
                    containers.append(container)
                except json.JSONDecodeError:
                    continue

            if filter_name:
                containers = [c for c in containers if filter_name.lower() in c["name"].lower()]

            return containers
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []

    @classmethod
    def get_container_stats(cls, container_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取容器资源统计

        Args:
            container_name: 指定容器名称，None 表示所有容器

        Returns:
            容器统计信息列表
        """
        try:
            cmd = ["docker", "stats", "--no-stream", "--no-trunc",
                   "--format", "{{json .}}"]
            if container_name:
                cmd.append(container_name)

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return []

            stats = []
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    stat = {
                        "name": data.get("Name", ""),
                        "cpu_percent": data.get("CPUPerc", "0%"),
                        "mem_usage": data.get("MemUsage", ""),
                        "mem_percent": data.get("MemPerc", "0%"),
                        "net_io": data.get("NetIO", ""),
                        "block_io": data.get("BlockIO", ""),
                        "pids": data.get("PIDs", ""),
                    }
                    stats.append(stat)
                except json.JSONDecodeError:
                    continue

            return stats
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []

    @classmethod
    def get_container_logs(
        cls,
        container_name: str,
        lines: int = 100,
        keyword: Optional[str] = None,
        follow: bool = False,
    ) -> Tuple[bool, str]:
        """获取容器日志

        Args:
            container_name: 容器名称
            lines: 日志行数
            keyword: 关键词过滤
            follow: 是否持续跟踪

        Returns:
            (success, output)
        """
        try:
            cmd = ["docker", "logs", "--tail", str(lines)]
            if follow:
                cmd.append("--follow")
            cmd.append(container_name)

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            # docker logs 输出到 stderr
            output = result.stderr or result.stdout

            if result.returncode != 0:
                return False, f"容器 '{container_name}' 不存在或日志获取失败"

            if not output.strip():
                return False, f"容器 '{container_name}' 无日志输出"

            # 关键词过滤
            if keyword:
                filtered = [
                    line for line in output.split("\n")
                    if keyword.lower() in line.lower()
                ]
                output = "\n".join(filtered)
                if not output.strip():
                    return False, f"未找到包含关键词 '{keyword}' 的日志"

            return True, output
        except subprocess.TimeoutExpired:
            return False, "日志获取超时"
        except FileNotFoundError:
            return False, "未找到 docker 命令，请安装 Docker"
        except Exception as e:
            return False, f"获取日志失败：{str(e)}"

    @classmethod
    def inspect_container(cls, container_name: str) -> Tuple[bool, Dict[str, Any]]:
        """检查容器详细配置

        Args:
            container_name: 容器名称

        Returns:
            (success, config_dict)
        """
        try:
            cmd = ["docker", "inspect", container_name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

            if result.returncode != 0:
                return False, {"error": f"容器 '{container_name}' 不存在"}

            data = json.loads(result.stdout)
            if not data:
                return False, {"error": f"容器 '{container_name}' 不存在"}

            info = data[0]
            config = {
                "name": info.get("Name", "").lstrip("/"),
                "id": info.get("Id", "")[:12],
                "image": info.get("Image", ""),
                "state": info.get("State", {}).get("Status", ""),
                "created": info.get("Created", ""),
                "hostname": info.get("Config", {}).get("Hostname", ""),
                "env": info.get("Config", {}).get("Env", []),
                "ports": info.get("NetworkSettings", {}).get("Ports", {}),
                "networks": list(info.get("NetworkSettings", {}).get("Networks", {}).keys()),
                "mounts": [],
                "restart_policy": info.get("HostConfig", {}).get("RestartPolicy", {}).get("Name", "no"),
                "memory_limit": info.get("HostConfig", {}).get("Memory", 0),
                "cpu_shares": info.get("HostConfig", {}).get("CpuShares", 0),
            }

            # 解析挂载
            for mount in info.get("Mounts", []):
                config["mounts"].append({
                    "type": mount.get("Type", ""),
                    "source": mount.get("Source", ""),
                    "destination": mount.get("Destination", ""),
                    "mode": mount.get("Mode", ""),
                })

            return True, config
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError) as e:
            return False, {"error": str(e)}

    @classmethod
    def list_images(cls) -> List[Dict[str, Any]]:
        """列出镜像

        Returns:
            镜像信息列表
        """
        try:
            cmd = ["docker", "images", "--format", "{{json .}}", "--no-trunc"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                return []

            images = []
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    image = {
                        "repository": data.get("Repository", ""),
                        "tag": data.get("Tag", ""),
                        "id": data.get("ID", "")[:12],
                        "size": data.get("Size", ""),
                        "created": data.get("CreatedAt", ""),
                        "is_dangling": data.get("Repository", "") == "<none>",
                    }
                    images.append(image)
                except json.JSONDecodeError:
                    continue

            return images
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []

    @classmethod
    def prune_images(cls) -> Tuple[bool, str]:
        """清理无用镜像

        Returns:
            (success, output)
        """
        try:
            cmd = ["docker", "image", "prune", "-f"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                return False, result.stderr or "清理失败"

            return True, result.stdout or "镜像清理完成"
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            return False, str(e)

    @classmethod
    def restart_container(cls, container_name: str) -> Tuple[bool, str]:
        """重启容器

        Args:
            container_name: 容器名称

        Returns:
            (success, output)
        """
        try:
            cmd = ["docker", "restart", container_name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                return False, result.stderr or f"重启容器 '{container_name}' 失败"

            return True, f"容器 '{container_name}' 已重启"
        except subprocess.TimeoutExpired:
            return False, "重启操作超时"
        except FileNotFoundError:
            return False, "未找到 docker 命令"

    @classmethod
    def stop_container(cls, container_name: str) -> Tuple[bool, str]:
        """停止容器"""
        try:
            cmd = ["docker", "stop", container_name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                return False, result.stderr or f"停止容器 '{container_name}' 失败"

            return True, f"容器 '{container_name}' 已停止"
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            return False, str(e)

    @classmethod
    def start_container(cls, container_name: str) -> Tuple[bool, str]:
        """启动容器"""
        try:
            cmd = ["docker", "start", container_name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                return False, result.stderr or f"启动容器 '{container_name}' 失败"

            return True, f"容器 '{container_name}' 已启动"
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            return False, str(e)


def format_docker_containers(containers: List[Dict[str, Any]], stats: List[Dict[str, Any]]) -> str:
    """格式化容器列表"""
    if not containers:
        return "[Docker] 未找到容器"

    lines = ["[Docker] 容器列表:"]
    lines.append("━" * 90)
    lines.append(f"{'名称':<25} {'镜像':<20} {'状态':<25} {'端口':<15}")
    lines.append("━" * 90)

    for c in containers:
        lines.append(f"  {c['name']:<25} {c['image']:<20} {c['status']:<25} {c['ports']:<15}")

    # 如果有统计信息，追加
    if stats:
        lines.append("")
        lines.append("━" * 90)
        lines.append(f"{'名称':<25} {'CPU%':<8} {'内存%':<8} {'内存使用':<18} {'PIDs':<6}")
        lines.append("━" * 90)

        # 按名称匹配
        stats_map = {s["name"]: s for s in stats}
        for c in containers:
            # docker stats 名称可能带 / 前缀
            short_name = c["name"].lstrip("/")
            stat = stats_map.get(c["name"]) or stats_map.get(short_name)
            if stat:
                lines.append(f"  {c['name']:<25} {stat['cpu_percent']:<8} {stat['mem_percent']:<8} {stat['mem_usage']:<18} {stat['pids']:<6}")
            else:
                lines.append(f"  {c['name']:<25} {'-':<8} {'-':<8} {'-':<18} {'-':<6}")

    lines.append("━" * 90)
    lines.append(f"共 {len(containers)} 个容器")
    return "\n".join(lines)


def format_docker_images(images: List[Dict[str, Any]]) -> str:
    """格式化镜像列表"""
    if not images:
        return "[Docker] 未找到镜像"

    lines = ["[Docker] 镜像列表:"]
    lines.append("━" * 80)
    lines.append(f"{'仓库':<30} {'标签':<15} {'大小':<10} {'状态':<8}")
    lines.append("━" * 80)

    for img in images:
        icon = "⚠ dangling" if img["is_dangling"] else "✓"
        lines.append(f"  {img['repository']:<30} {img['tag']:<15} {img['size']:<10} {icon:<8}")

    lines.append("━" * 80)
    lines.append(f"共 {len(images)} 个镜像")

    dangling = [i for i in images if i["is_dangling"]]
    if dangling:
        lines.append(f"⚠ 发现 {len(dangling)} 个 dangling 镜像，可执行 'docker 清理' 删除")

    return "\n".join(lines)
