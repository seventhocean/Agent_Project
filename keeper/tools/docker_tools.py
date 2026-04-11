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
    def docker_inspect(cls) -> Dict[str, Any]:
        """Docker 全面巡检

        Returns:
            巡检结果字典
        """
        result = {
            "service_ok": False,
            "version": "",
            "server_version": "",
            "storage_driver": "",
            "containers_total": 0,
            "containers_running": 0,
            "containers_paused": 0,
            "containers_stopped": 0,
            "container_list": [],
            "unhealthy_containers": [],
            "images_total": 0,
            "dangling_images": 0,
            "disk_total": "",
            "disk_used": "",
            "disk_available": "",
            "disk_percent": "",
            "warnings": [],
            "health_score": 100,
        }

        # 1. 服务信息
        try:
            info_result = subprocess.run(
                ["docker", "info", "--format", "{{json .}}"],
                capture_output=True, text=True, timeout=15,
            )
            if info_result.returncode == 0:
                info = json.loads(info_result.stdout.strip())
                result["service_ok"] = True
                result["version"] = info.get("ClientInfo", {}).get("Version", "")
                result["server_version"] = info.get("ServerVersion", "")
                result["storage_driver"] = info.get("Driver", "")
                result["containers_total"] = info.get("Containers", 0)
                result["containers_running"] = info.get("ContainersRunning", 0)
                result["containers_paused"] = info.get("ContainersPaused", 0)
                result["containers_stopped"] = info.get("ContainersStopped", 0)
                images_total = info.get("Images", 0)
                result["images_total"] = images_total
        except Exception:
            pass

        if not result["service_ok"]:
            result["warnings"].append("Docker 服务不可用")
            result["health_score"] = 0
            return result

        # 2. 容器健康状态
        try:
            containers = cls.list_containers()
            result["container_list"] = containers
            for c in containers:
                status_lower = c["status"].lower()
                if "unhealthy" in status_lower:
                    result["unhealthy_containers"].append(c["name"])
                    result["warnings"].append(f"容器 {c['name']} 健康检查失败")
                elif "restarting" in status_lower:
                    result["warnings"].append(f"容器 {c['name']} 正在重启")
                elif "dead" in status_lower:
                    result["warnings"].append(f"容器 {c['name']} 状态异常 (dead)")
        except Exception as e:
            result["warnings"].append(f"容器状态获取失败：{e}")

        # 3. 镜像健康
        try:
            images = cls.list_images()
            result["images_total"] = len(images)
            dangling = [i for i in images if i["is_dangling"]]
            result["dangling_images"] = len(dangling)
            if dangling:
                result["warnings"].append(f"存在 {len(dangling)} 个 dangling 镜像")
        except Exception as e:
            result["warnings"].append(f"镜像列表获取失败：{e}")

        # 4. 磁盘使用
        try:
            df_result = subprocess.run(
                ["docker", "system", "df", "--format", "{{json .}}"],
                capture_output=True, text=True, timeout=15,
            )
            if df_result.returncode == 0:
                for line in df_result.stdout.strip().split("\n"):
                    if not line.strip():
                        continue
                    df_info = json.loads(line)
                    if "ImagesSize" in df_info:
                        total = df_info.get("ImagesSize", 0)
                        used = df_info.get("ImagesSize", 0)
                        # docker system df 不直接给 total，用 df 命令替代
                        break
        except Exception:
            pass

        try:
            df_disk = subprocess.run(
                ["df", "-h", "--output=size,used,avail,pcent", "/var/lib/docker"],
                capture_output=True, text=True, timeout=10,
            )
            if df_disk.returncode == 0:
                lines = df_disk.stdout.strip().split("\n")
                if len(lines) >= 2:
                    parts = lines[-1].split()
                    if len(parts) >= 4:
                        result["disk_total"] = parts[0]
                        result["disk_used"] = parts[1]
                        result["disk_available"] = parts[2]
                        result["disk_percent"] = parts[3]
        except Exception:
            pass

        # 5. 健康评分
        score = 100
        if result["unhealthy_containers"]:
            score -= len(result["unhealthy_containers"]) * 15
        if result["dangling_images"] > 0:
            score -= 5
        disk_pct = result["disk_percent"].rstrip("%")
        try:
            disk_val = float(disk_pct)
            if disk_val > 90:
                score -= 20
            elif disk_val > 80:
                score -= 10
        except ValueError:
            pass
        result["health_score"] = max(0, score)
        return result

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


def format_docker_inspect(data: Dict[str, Any]) -> str:
    """格式化 Docker 巡检报告"""
    lines = ["[Docker] 巡检报告"]
    lines.append("=" * 50)

    if not data["service_ok"]:
        lines.append("  ⛔ Docker 服务不可用，请检查 Docker 是否安装并运行")
        return "\n".join(lines)

    lines.append(f"  Docker 版本：  {data['version']} (client) / {data['server_version']} (server)")
    lines.append(f"  存储驱动：    {data['storage_driver']}")
    lines.append("")

    # 容器状态
    lines.append("━" * 40)
    lines.append("容器状态:")
    lines.append("━" * 40)
    lines.append(f"  运行中：    {data['containers_running']}")
    lines.append(f"  已暂停：    {data['containers_paused']}")
    lines.append(f"  已停止：    {data['containers_stopped']}")
    lines.append(f"  总计：      {data['containers_total']}")
    lines.append("")

    if data["unhealthy_containers"]:
        lines.append("  ⚠ 健康检查失败的容器:")
        for name in data["unhealthy_containers"]:
            lines.append(f"    - {name}")
        lines.append("")

    # 镜像状态
    lines.append("━" * 40)
    lines.append("镜像状态:")
    lines.append("━" * 40)
    lines.append(f"  镜像总数：  {data['images_total']}")
    if data["dangling_images"] > 0:
        lines.append(f"  ⚠ 无用镜像：  {data['dangling_images']} 个（可执行 'docker 清理' 删除）")
    lines.append("")

    # 磁盘使用
    if data["disk_used"]:
        lines.append("━" * 40)
        lines.append("磁盘使用 (/var/lib/docker):")
        lines.append("━" * 40)
        lines.append(f"  总容量：    {data['disk_total']}")
        lines.append(f"  已用：      {data['disk_used']}")
        lines.append(f"  可用：      {data['disk_available']}")
        lines.append(f"  使用率：    {data['disk_percent']}")
        lines.append("")

    # 健康评分
    score = data["health_score"]
    status = "✅ 健康" if score >= 80 else "⚠️  需要注意" if score >= 50 else "❌ 异常"
    lines.append("=" * 50)
    lines.append(f"  健康评分：{score}/100 - {status}")
    lines.append("=" * 50)

    if data["warnings"]:
        lines.append("")
        lines.append("  告警项:")
        for w in data["warnings"]:
            lines.append(f"    ⚠ {w}")

    return "\n".join(lines)
