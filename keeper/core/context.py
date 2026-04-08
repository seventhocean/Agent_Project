"""Agent 核心模块 - 上下文管理和记忆系统"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from collections import deque


@dataclass
class ConversationTurn:
    """一轮对话"""
    user_input: str
    agent_response: str
    intent: str
    entities: Dict[str, Any]


class ContextManager:
    """上下文管理器"""

    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self.current_host: Optional[str] = None
        self.current_profile: Optional[str] = None
        self.last_intent: Optional[str] = None
        self.entities_cache: Dict[str, Any] = {}

    def update(self, intent: str, entities: Dict[str, Any]) -> None:
        """更新上下文"""
        self.last_intent = intent

        if entities.get("host"):
            self.current_host = entities["host"]
        if entities.get("profile"):
            self.current_profile = entities["profile"]

        # 缓存实体供后续指代使用
        self.entities_cache.update(entities)

    def get(self, key: str) -> Optional[Any]:
        """从上下文获取值"""
        return getattr(self, key, None) or self.entities_cache.get(key)

    def clear(self) -> None:
        """清空上下文"""
        self.current_host = None
        self.current_profile = None
        self.last_intent = None
        self.entities_cache = {}


class MemoryManager:
    """记忆管理器 - 短期记忆"""

    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self.turns: deque[ConversationTurn] = deque(maxlen=max_turns)

    def add_turn(self, user_input: str, agent_response: str,
                 intent: str, entities: Dict[str, Any]) -> None:
        """添加一轮对话到记忆"""
        turn = ConversationTurn(
            user_input=user_input,
            agent_response=agent_response,
            intent=intent,
            entities=entities,
        )
        self.turns.append(turn)

    def get_recent_turns(self, n: int = 5) -> List[ConversationTurn]:
        """获取最近 N 轮对话"""
        return list(self.turns)[-n:]

    def get_hosts_mentioned(self) -> List[str]:
        """获取记忆中提到的所有主机"""
        hosts = set()
        for turn in self.turns:
            if turn.entities.get("host"):
                hosts.add(turn.entities["host"])
        return list(hosts)

    def clear(self) -> None:
        """清空记忆"""
        self.turns.clear()


@dataclass
class AgentState:
    """Agent 状态"""
    context: ContextManager = field(default_factory=ContextManager)
    memory: MemoryManager = field(default_factory=MemoryManager)
    current_profile: str = "default"
    is_running: bool = False
