"""Qwen MCP 服务器测试"""

from types import SimpleNamespace

import pytest

from hello_mcp.servers import qwen_agent


@pytest.fixture
def mock_generation(monkeypatch):
    """替换 DashScope Generation.call，返回固定回复并记录入参"""
    calls: list[dict] = []

    def fake_call(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            status_code=200,
            output=SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="Mock response"))]
            ),
        )

    monkeypatch.setattr(qwen_agent, "Generation", SimpleNamespace(call=fake_call))
    return calls


class _Boom:
    @staticmethod
    def call(**kwargs):
        raise ValueError("API Error")


def _error_response(status_code: int = 401, code: str = "InvalidApiKey", message: str = "bad key"):
    return SimpleNamespace(status_code=status_code, code=code, message=message, output=None)


def test_ask_qwen_returns_answer(mock_generation):
    result = qwen_agent.ask_qwen.fn("测试问题")

    assert result == "Mock response"
    assert len(mock_generation) == 1


def test_ask_qwen_passes_key_and_messages(mock_generation):
    """回归：真实使用环境变量里的密钥，并保留 system/user 结构"""
    qwen_agent.ask_qwen.fn("什么是 MCP")

    kwargs = mock_generation[0]
    assert kwargs["api_key"] == "test-dashscope-key"
    assert kwargs["result_format"] == "message"
    assert kwargs["messages"][0]["content"] == "You are a helpful assistant."
    assert kwargs["messages"][1] == {"role": "user", "content": "什么是 MCP"}


def test_ask_qwen_raises_on_failure_with_cause(mock_generation, monkeypatch):
    monkeypatch.setattr(qwen_agent, "Generation", _Boom)

    with pytest.raises(RuntimeError, match="调用 Qwen 模型失败") as excinfo:
        qwen_agent.ask_qwen.fn("测试问题")

    assert isinstance(excinfo.value.__cause__, ValueError)


def test_ask_qwen_raises_when_key_missing(mock_generation, monkeypatch):
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

    with pytest.raises(ValueError, match="DASHSCOPE_API_KEY 环境变量未设置"):
        qwen_agent.ask_qwen.fn("测试问题")


def test_ask_qwen_surfaces_dashscope_error(monkeypatch, recording_ctx):
    """DashScope 返回非 200 时给出状态码与原因，而不是 cryptic AttributeError"""
    monkeypatch.setattr(
        qwen_agent,
        "Generation",
        SimpleNamespace(call=lambda **kwargs: _error_response()),
    )

    with pytest.raises(RuntimeError, match="调用 Qwen 模型失败") as excinfo:
        qwen_agent.ask_qwen.fn("测试问题", recording_ctx)

    assert "DashScope 返回错误 401" in str(excinfo.value)
    assert isinstance(excinfo.value.__cause__, RuntimeError)
    assert any("DashScope 返回错误 401" in msg for msg in recording_ctx.errors)


def test_ask_qwen_rejects_empty_choices(monkeypatch):
    monkeypatch.setattr(
        qwen_agent,
        "Generation",
        SimpleNamespace(
            call=lambda **kwargs: SimpleNamespace(
                status_code=200,
                output=SimpleNamespace(choices=[]),
            )
        ),
    )

    with pytest.raises(RuntimeError, match="未返回有效结果"):
        qwen_agent.ask_qwen.fn("测试问题")


def test_ask_qwen_rejects_empty_content(monkeypatch):
    monkeypatch.setattr(
        qwen_agent,
        "Generation",
        SimpleNamespace(
            call=lambda **kwargs: SimpleNamespace(
                status_code=200,
                output=SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content=""))]
                ),
            )
        ),
    )

    with pytest.raises(RuntimeError, match="空内容"):
        qwen_agent.ask_qwen.fn("测试问题")


async def test_code_review_includes_code_in_prompt(mock_generation):
    code = "def foo(): pass"

    result = await qwen_agent.code_review.fn(code)

    assert result == "Mock response"
    kwargs = mock_generation[0]
    assert kwargs["messages"][0]["content"] == "You are a professional Python code reviewer."
    assert code in kwargs["messages"][1]["content"]


async def test_tools_log_through_context(mock_generation, recording_ctx):
    qwen_agent.ask_qwen.fn("测试问题", recording_ctx)
    await qwen_agent.code_review.fn("def foo(): pass", recording_ctx)

    assert any("正在向 Qwen 提问" in msg for msg in recording_ctx.infos)
    assert any("Qwen 回答" in msg for msg in recording_ctx.infos)
    assert "代码审查完成" in recording_ctx.infos


async def test_code_review_raises_on_failure_with_cause(monkeypatch, recording_ctx):
    monkeypatch.setattr(qwen_agent, "Generation", _Boom)

    with pytest.raises(RuntimeError, match="代码审查失败") as excinfo:
        await qwen_agent.code_review.fn("def foo(): pass", recording_ctx)

    assert isinstance(excinfo.value.__cause__, ValueError)
    assert any("代码审查失败" in msg for msg in recording_ctx.errors)
