"""
AI Agent 基类
基于 DeepSeek LLM 的智能审核 Agent，所有专用 Agent 继承此类
"""
import time
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Callable

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage, BaseMessage

from app.config import settings

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    AI Agent 基类

    使用 DeepSeek API 作为 LLM 后端，提供基础的 LLM 调用能力
    子类需要实现 execute() 方法定义具体的审核逻辑
    """

    def __init__(
        self,
        name: str,
        system_prompt: str = "你是一个专业的财务审核AI助手。",
        temperature: float = None,
        max_tokens: int = None,
    ):
        """
        初始化 Agent

        Args:
            name: Agent名称
            system_prompt: 系统提示词
            temperature: LLM温度参数
            max_tokens: 最大输出Token数
        """
        self.name = name
        self.system_prompt = system_prompt
        self.messages: List[BaseMessage] = []
        self.tools: Dict[str, Callable] = {}
        self.start_time: Optional[float] = None

        # 初始化 DeepSeek LLM
        self.llm = ChatOpenAI(
            openai_api_key=settings.DEEPSEEK_API_KEY,
            openai_api_base=settings.DEEPSEEK_API_BASE,
            model_name=settings.MODEL_NAME,
            temperature=temperature if temperature is not None else settings.TEMPERATURE,
            max_tokens=max_tokens if max_tokens is not None else settings.MAX_TOKENS,
        )

        # 设置系统消息
        self.messages.append(SystemMessage(content=system_prompt))

        logger.info(f"[{self.name}] Agent 初始化完成，模型: {settings.MODEL_NAME}")

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行 Agent 的核心任务

        Args:
            context: 上下文信息（包含报销单数据、规则等）

        Returns:
            执行结果字典，至少包含 status 和 result 字段
        """
        pass

    async def chat(self, user_message: str) -> str:
        """
        与 LLM 进行对话

        Args:
            user_message: 用户消息

        Returns:
            LLM的回复文本
        """
        self.messages.append(HumanMessage(content=user_message))

        try:
            response = await self.llm.ainvoke(self.messages)
            self.messages.append(AIMessage(content=response.content))
            return response.content
        except Exception as e:
            logger.error(f"[{self.name}] LLM 调用失败: {e}")
            raise

    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return self.system_prompt

    def update_system_prompt(self, prompt: str):
        """更新系统提示词"""
        self.system_prompt = prompt
        # 更新消息列表中的第一条系统消息
        if self.messages and isinstance(self.messages[0], SystemMessage):
            self.messages[0] = SystemMessage(content=prompt)

    def add_tool(self, name: str, func: Callable):
        """注册工具函数"""
        self.tools[name] = func
        logger.info(f"[{self.name}] 注册工具: {name}")

    def clear_memory(self):
        """清除对话记忆，保留系统提示词"""
        self.messages = [SystemMessage(content=self.system_prompt)]
        self.start_time = None

    def _start_timer(self):
        """开始计时"""
        self.start_time = time.time()

    def _get_duration_ms(self) -> float:
        """获取执行耗时（毫秒）"""
        if self.start_time:
            return (time.time() - self.start_time) * 1000
        return 0

    def _build_result(
        self,
        status: str = "success",
        result: Dict[str, Any] = None,
        message: str = None,
    ) -> Dict[str, Any]:
        """构建标准化的执行结果"""
        return {
            "agent_name": self.name,
            "status": status,
            "result": result or {},
            "message": message or f"[{self.name}] 执行{'成功' if status == 'success' else '失败'}",
            "duration_ms": self._get_duration_ms(),
        }
