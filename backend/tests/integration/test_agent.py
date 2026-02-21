"""Integration tests for the LangGraph agent graph creation and configuration."""

from unittest.mock import patch

from langgraph.checkpoint.memory import InMemorySaver

from app.agent.graph import create_agent_graph, create_llm
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import execute_query, inspect_schema


class TestCreateLlm:
    def test_creates_chat_openai_with_settings(self) -> None:
        with patch("app.agent.graph.settings") as mock_settings:
            mock_settings.litellm_api_url = "https://proxy.example.com/"
            mock_settings.litellm_api_key = "test-key"
            mock_settings.litellm_model = "claude-sonnet-4-5"

            llm = create_llm()

        assert llm.model_name == "claude-sonnet-4-5"
        assert str(llm.openai_api_base) == "https://proxy.example.com/v1"
        assert llm.openai_api_key.get_secret_value() == "test-key"

    def test_strips_trailing_slash_from_base_url(self) -> None:
        with patch("app.agent.graph.settings") as mock_settings:
            mock_settings.litellm_api_url = "https://proxy.example.com///"
            mock_settings.litellm_api_key = "k"
            mock_settings.litellm_model = "m"

            llm = create_llm()

        assert str(llm.openai_api_base) == "https://proxy.example.com/v1"


class TestCreateAgentGraph:
    def test_creates_graph_with_checkpointer(self) -> None:
        checkpointer = InMemorySaver()

        with patch("app.agent.graph.settings") as mock_settings:
            mock_settings.litellm_api_url = "https://proxy.example.com/"
            mock_settings.litellm_api_key = "test-key"
            mock_settings.litellm_model = "claude-sonnet-4-5"

            graph = create_agent_graph(checkpointer)

        assert graph is not None
        assert len(graph.nodes) > 0

    def test_graph_has_tools_node(self) -> None:
        checkpointer = InMemorySaver()

        with patch("app.agent.graph.settings") as mock_settings:
            mock_settings.litellm_api_url = "https://proxy.example.com/"
            mock_settings.litellm_api_key = "test-key"
            mock_settings.litellm_model = "claude-sonnet-4-5"

            graph = create_agent_graph(checkpointer)

        node_names = list(graph.nodes.keys())
        assert "tools" in node_names


class TestSystemPrompt:
    def test_prompt_instructs_schema_inspection(self) -> None:
        assert "inspect_schema" in SYSTEM_PROMPT

    def test_prompt_instructs_select_only(self) -> None:
        assert "SELECT" in SYSTEM_PROMPT

    def test_prompt_instructs_display_hints(self) -> None:
        assert "display" in SYSTEM_PROMPT
        assert "bar_chart" in SYSTEM_PROMPT
        assert "line_chart" in SYSTEM_PROMPT
        assert "pie_chart" in SYSTEM_PROMPT
        assert "scatter_plot" in SYSTEM_PROMPT
        assert "table" in SYSTEM_PROMPT
        assert "text" in SYSTEM_PROMPT

    def test_prompt_instructs_retry(self) -> None:
        assert "retry" in SYSTEM_PROMPT.lower()
        assert "3" in SYSTEM_PROMPT

    def test_prompt_defines_role(self) -> None:
        assert "data analyst assistant" in SYSTEM_PROMPT


class TestToolDefinitions:
    def test_inspect_schema_tool_name(self) -> None:
        assert inspect_schema.name == "inspect_schema"

    def test_execute_query_tool_name(self) -> None:
        assert execute_query.name == "execute_query"

    def test_inspect_schema_has_description(self) -> None:
        assert len(inspect_schema.description) > 0
        assert "schema" in inspect_schema.description.lower()

    def test_execute_query_has_description(self) -> None:
        assert len(execute_query.description) > 0
        assert "SELECT" in execute_query.description
