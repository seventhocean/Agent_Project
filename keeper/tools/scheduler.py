"""定时任务调度器"""
import os
import json
import time
import uuid
import threading
import yaml
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List, Callable


@dataclass
class ScheduledTask:
    """定时任务"""
    id: str
    cron_expr: str
    description: str
    task_type: str  # inspect, k8s_inspect, k8s_logs, scan, network_diag, custom
    params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    created_at: str = ""
    last_run: Optional[str] = None
    last_result: Optional[str] = None
    run_count: int = 0


class TaskScheduler:
    """定时任务调度器"""

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path.home() / ".keeper"
        self.tasks_file = self.config_dir / "tasks.yaml"
        self.tasks: List[ScheduledTask] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callback: Optional[Callable] = None
        self._load()

    def _load(self) -> None:
        """从文件加载任务"""
        if self.tasks_file.exists():
            try:
                with open(self.tasks_file) as f:
                    data = yaml.safe_load(f)
                    if data and "tasks" in data:
                        self.tasks = []
                        for t in data["tasks"]:
                            self.tasks.append(ScheduledTask(
                                id=t["id"],
                                cron_expr=t["cron_expr"],
                                description=t["description"],
                                task_type=t["task_type"],
                                params=t.get("params", {}),
                                enabled=t.get("enabled", True),
                                created_at=t.get("created_at", ""),
                                last_run=t.get("last_run"),
                                last_result=t.get("last_result"),
                                run_count=t.get("run_count", 0),
                            ))
            except Exception:
                self.tasks = []

    def save(self) -> None:
        """保存任务到文件"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.tasks_file, "w") as f:
            yaml.safe_dump({
                "tasks": [asdict(t) for t in self.tasks],
            }, f, default_flow_style=False, allow_unicode=True)

    def add_task(
        self,
        cron_expr: str,
        description: str,
        task_type: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> ScheduledTask:
        """添加定时任务"""
        task = ScheduledTask(
            id=str(uuid.uuid4())[:8],
            cron_expr=cron_expr,
            description=description,
            task_type=task_type,
            params=params or {},
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self.tasks.append(task)
        self.save()
        return task

    def remove_task(self, task_id: str) -> bool:
        """删除任务"""
        before = len(self.tasks)
        self.tasks = [t for t in self.tasks if t.id != task_id]
        if len(self.tasks) < before:
            self.save()
            return True
        return False

    def enable_task(self, task_id: str) -> bool:
        """启用任务"""
        for t in self.tasks:
            if t.id == task_id:
                t.enabled = True
                self.save()
                return True
        return False

    def disable_task(self, task_id: str) -> bool:
        """禁用任务"""
        for t in self.tasks:
            if t.id == task_id:
                t.enabled = False
                self.save()
                return True
        return False

    def list_tasks(self) -> List[ScheduledTask]:
        """列出所有任务"""
        return self.tasks

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """获取单个任务"""
        for t in self.tasks:
            if t.id == task_id:
                return t
        return None

    def set_callback(self, callback: Callable) -> None:
        """设置任务执行回调
        回调函数签名: callback(task: ScheduledTask) -> str
        返回执行结果文本
        """
        self._callback = callback

    def start(self) -> None:
        """启动调度器"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="keeper-scheduler")
        self._thread.start()

    def stop(self) -> None:
        """停止调度器"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _loop(self) -> None:
        """调度循环 — 每分钟检查一次"""
        last_check_minute = -1
        while self._running:
            now = datetime.now()
            if now.minute != last_check_minute:
                last_check_minute = now.minute
                self._check_and_run(now)
            time.sleep(10)  # 每 10 秒检查一次

    def _check_and_run(self, now: datetime) -> None:
        """检查并执行到期的任务"""
        for task in self.tasks:
            if not task.enabled:
                continue
            if self._cron_match(task.cron_expr, now):
                result = self._execute_task(task)
                task.last_run = now.strftime("%Y-%m-%d %H:%M:%S")
                task.last_result = result[:500] if result else "无输出"
                task.run_count += 1
                self.save()

    def _execute_task(self, task: ScheduledTask) -> str:
        """执行单个任务"""
        if self._callback:
            try:
                return self._callback(task)
            except Exception as e:
                return f"任务执行失败: {str(e)}"
        return f"任务已触发 (未设置回调): {task.description}"

    def _cron_match(self, cron_expr: str, now: datetime) -> bool:
        """检查 cron 表达式是否匹配当前时间

        支持标准 5 字段 cron: minute hour day-of-month month day-of-week
        """
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            return False

        minute, hour, dom, month, dow = parts

        def field_match(field_val: str, current_val: int) -> bool:
            if field_val == "*":
                return True
            # 步长: */5
            if field_val.startswith("*/"):
                step = int(field_val[2:])
                return current_val % step == 0
            # 范围: 1-5
            if "-" in field_val:
                start, end = field_val.split("-")
                return int(start) <= current_val <= int(end)
            # 列表: 1,3,5
            if "," in field_val:
                return current_val in [int(x) for x in field_val.split(",")]
            # 单值
            return current_val == int(field_val)

        return (
            field_match(minute, now.minute)
            and field_match(hour, now.hour)
            and field_match(dom, now.day)
            and field_match(month, now.month)
            and field_match(dow, now.weekday())  # cron: 0=Sunday, Python: 0=Monday
        )

    def _run_single_task_now(self, task_id: str) -> str:
        """立即执行指定任务"""
        task = self.get_task(task_id)
        if not task:
            return f"任务 {task_id} 不存在"
        result = self._execute_task(task)
        task.last_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        task.last_result = result[:500] if result else "无输出"
        task.run_count += 1
        self.save()
        return result


def format_task_list(tasks: List[ScheduledTask]) -> str:
    """格式化任务列表"""
    if not tasks:
        return "[定时任务] 暂无任务"

    lines = ["[定时任务] 任务列表:"]
    lines.append("━" * 80)
    lines.append(f"{'ID':<10} {'描述':<30} {'Cron':<18} {'类型':<16} {'状态':<8} {'执行次数':<8}")
    lines.append("━" * 80)

    for t in tasks:
        status = "✓ 启用" if t.enabled else "✗ 禁用"
        lines.append(f"  {t.id:<10} {t.description:<30} {t.cron_expr:<18} {t.task_type:<16} {status:<8} {t.run_count:<8}")

    lines.append("━" * 80)
    lines.append(f"共 {len(tasks)} 个任务")
    return "\n".join(lines)


# 常用 cron 表达式模板
CRON_TEMPLATES = {
    "每1分钟": "* * * * *",
    "每5分钟": "*/5 * * * *",
    "每10分钟": "*/10 * * * *",
    "每30分钟": "*/30 * * * *",
    "每小时": "0 * * * *",
    "每天0点": "0 0 * * *",
    "每天6点": "0 6 * * *",
    "每天9点": "0 9 * * *",
    "每天12点": "0 12 * * *",
    "每天18点": "0 18 * * *",
    "工作日9点": "0 9 * * 1-5",
    "工作日18点": "0 18 * * 1-5",
    "每周一9点": "0 9 * * 1",
    "每月1号0点": "0 0 1 * *",
}
