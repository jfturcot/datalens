import logging

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.prebuilt import create_react_agent

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import execute_query, inspect_schema
from app.config import settings

logger = logging.getLogger(__name__)


def create_llm() -> ChatOpenAI:
    """Create the ChatOpenAI instance pointing at the LiteLLM proxy."""
    base_url = settings.litellm_api_url.rstrip("/") + "/v1"
    return ChatOpenAI(
        base_url=base_url,
        api_key=settings.litellm_api_key,  # type: ignore[arg-type]
        model=settings.litellm_model,
    )


def create_agent_graph(checkpointer: AsyncPostgresSaver):
    """Create the LangGraph ReAct agent with tools and checkpointing."""
    llm = create_llm()
    tools = [inspect_schema, execute_query]

    graph = create_react_agent(
        model=llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )

    logger.info("Agent graph created with model=%s", settings.litellm_model)
    return graph
