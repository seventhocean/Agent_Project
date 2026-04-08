"""Keeper 测试模块"""
import pytest
from keeper.nlu.base import IntentType, ParsedIntent
from keeper.core.context import ContextManager, MemoryManager


class TestContextManager:
    """测试上下文管理器"""

    def test_update_context(self):
        """测试上下文更新"""
        ctx = ContextManager()
        ctx.update("inspect", {"host": "192.168.1.100"})

        assert ctx.current_host == "192.168.1.100"
        assert ctx.last_intent == "inspect"

    def test_get_from_context(self):
        """测试从上下文获取值"""
        ctx = ContextManager()
        ctx.update("inspect", {"host": "192.168.1.100", "threshold": 80})

        assert ctx.get("host") == "192.168.1.100"
        assert ctx.get("threshold") == 80

    def test_clear_context(self):
        """测试清空上下文"""
        ctx = ContextManager()
        ctx.update("inspect", {"host": "192.168.1.100"})
        ctx.clear()

        assert ctx.current_host is None
        assert ctx.last_intent is None


class TestMemoryManager:
    """测试记忆管理器"""

    def test_add_turn(self):
        """测试添加对话轮次"""
        memory = MemoryManager()
        memory.add_turn(
            user_input="检查 192.168.1.100",
            agent_response="CPU 45%",
            intent="inspect",
            entities={"host": "192.168.1.100"}
        )

        assert len(memory.turns) == 1
        assert memory.turns[0].user_input == "检查 192.168.1.100"

    def test_get_recent_turns(self):
        """测试获取最近的对话"""
        memory = MemoryManager(max_turns=10)

        for i in range(15):
            memory.add_turn(f"input {i}", f"response {i}", "inspect", {})

        recent = memory.get_recent_turns(5)
        assert len(recent) == 5
        assert recent[0].user_input == "input 10"  # 保留最新的 10 条
        assert recent[-1].user_input == "input 14"

    def test_get_hosts_mentioned(self):
        """测试获取提到的主机"""
        memory = MemoryManager()
        memory.add_turn("检查 192.168.1.100", "...", "inspect", {"host": "192.168.1.100"})
        memory.add_turn("检查 192.168.1.101", "...", "inspect", {"host": "192.168.1.101"})

        hosts = memory.get_hosts_mentioned()
        assert "192.168.1.100" in hosts
        assert "192.168.1.101" in hosts


class TestServerTools:
    """测试服务器工具"""

    def test_get_cpu_percent(self):
        """测试 CPU 使用率获取"""
        from keeper.tools.server import ServerTools

        cpu = ServerTools.get_cpu_percent()
        assert 0 <= cpu <= 100

    def test_get_memory_info(self):
        """测试内存信息获取"""
        from keeper.tools.server import ServerTools

        mem = ServerTools.get_memory_info()
        assert "percent" in mem
        assert "used_gb" in mem
        assert "total_gb" in mem
        assert 0 <= mem["percent"] <= 100

    def test_get_disk_info(self):
        """测试磁盘信息获取"""
        from keeper.tools.server import ServerTools

        disk = ServerTools.get_disk_info()
        assert "percent" in disk
        assert 0 <= disk["percent"] <= 100

    def test_inspect_local(self):
        """测试本地服务器巡检"""
        from keeper.tools.server import ServerTools

        status = ServerTools.inspect_server("localhost")
        assert status.host is not None
        assert status.cpu_percent >= 0
        assert status.memory_percent >= 0
        assert status.disk_percent >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
