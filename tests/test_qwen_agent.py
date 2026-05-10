"""Qwen MCP 服务器测试"""

from unittest.mock import MagicMock, patch

import pytest

from hello_mcp.servers.qwen_agent import ask_qwen, code_review

# 通过 .fn 获取底层可调用函数（FastMCP 将工具包装成 FunctionTool 对象）
_ask_qwen = ask_qwen.fn
_code_review = code_review.fn


@pytest.fixture
def mock_config():
    """模拟配置"""
    with patch("hello_mcp.servers.qwen_agent.load_config") as mock:
        mock.return_value = MagicMock(DASHSCOPE_API_KEY="test-key")
        yield mock


@pytest.fixture
def mock_generation():
    """模拟 DashScope Generation"""
    with patch("hello_mcp.servers.qwen_agent.Generation") as mock:
        mock_response = MagicMock()
        mock_response.output.choices = [MagicMock(message=MagicMock(content="Mock response"))]
        mock.call.return_value = mock_response
        yield mock


def test_ask_qwen_returns_answer(mock_config, mock_generation):
    """测试 ask_qwen 返回模型回答"""
    result = _ask_qwen("测试问题")

    assert result == "Mock response"
    mock_generation.call.assert_called_once()


def test_ask_qwen_raises_on_failure(mock_config):
    """测试 ask_qwen 在 API 失败时抛出异常"""
    with patch("hello_mcp.servers.qwen_agent.Generation") as mock:
        mock.call.side_effect = Exception("API Error")

        with pytest.raises(RuntimeError, match="调用 Qwen 模型失败"):
            _ask_qwen("测试问题")


def test_code_review_returns_feedback(mock_config, mock_generation):
    """测试 code_review 返回审查建议"""
    code = "def foo(): pass"
    result = _code_review(code)

    assert isinstance(result, str)
    assert len(result) > 0


def test_code_review_raises_on_failure(mock_config):
    """测试 code_review 在 API 失败时抛出异常"""
    with patch("hello_mcp.servers.qwen_agent.Generation") as mock:
        mock.call.side_effect = Exception("API Error")

        with pytest.raises(RuntimeError, match="代码审查失败"):
            _code_review("def foo(): pass")
