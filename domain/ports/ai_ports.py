from typing import Protocol, List, Dict, Any, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class AIOrchestrationPort(Protocol):
    """Port for interacting with Vertex AI and building agentic workflows."""

    async def generate_structured_insight(self, prompt: str, schema: Type[T]) -> T:
        """Generate a structured response from an LLM based on a schema."""
        ...

    async def search_financial_docs(self, query: str) -> List[Dict[str, Any]]:
        """Perform RAG (Retrieval-Augmented Generation) on financial data."""
        ...

    async def execute_agent_task(self, task_description: str, tools: List[str]) -> Any:
        """Execute a specific task using an AI agent and available MCP tools."""
        ...
