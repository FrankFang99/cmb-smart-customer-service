"""
MiniMax LLM Client — 项目本地独立 LLM 客户端
=============================================

不依赖 mavis LLM 工具 / 不污染全局 config / token 从环境变量读。
直调 MiniMax 兼容 API (OpenAI 协议) 解决 mavis 默认协议不匹配问题。

环境变量:
  MINIMAX_API_KEY   - MiniMax API key (必填)
  MINIMAX_BASE_URL  - 覆盖默认 baseURL (可选, 默认 https://agent.minimaxi.com/mavis/api/v1/llm/v1)
  MINIMAX_MODEL     - 覆盖默认 model (可选, 默认 MiniMax-M3)

用法:
  from src.llm.minimax_client import chat, embed
  text = chat([{"role": "user", "content": "你好"}])
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx


def _load_dotenv() -> None:
    """手动读项目根 .env (不依赖 python-dotenv)"""
    # 项目根: src/llm/minimax_client.py → 父父父父 = 项目根
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        # 移除可能存在的引号
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1]
        # 不覆盖已存在的环境变量 (允许 shell 临时覆盖)
        os.environ.setdefault(k, v)


_load_dotenv()


DEFAULT_BASE_URL = "https://api.minimaxi.com/v1"  # 2026-06 v3.3.6: 改用官方订阅端点
DEFAULT_MODEL = "MiniMax-M3"
DEFAULT_TIMEOUT = 120.0


class MiniMaxError(RuntimeError):
    pass


def _get_config() -> tuple[str, str, str]:
    api_key = os.environ.get("MINIMAX_API_KEY", "").strip()
    if not api_key:
        raise MiniMaxError(
            "MINIMAX_API_KEY 环境变量未设置。请先在 shell 里:\n"
            "  $env:MINIMAX_API_KEY = 'sk-api-xxx'\n"
            "  或 PowerShell:  [Environment]::SetEnvironmentVariable('MINIMAX_API_KEY', 'sk-api-xxx', 'User')"
        )
    base_url = os.environ.get("MINIMAX_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    model = os.environ.get("MINIMAX_MODEL", DEFAULT_MODEL)
    return api_key, base_url, model


def chat(
    messages: List[Dict[str, str]],
    *,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """普通对话, 返回 assistant 文本。"""
    api_key, base_url, default_model = _get_config()
    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model or default_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }

    try:
        resp = httpx.post(url, headers=headers, json=body, timeout=timeout)
    except httpx.TimeoutException as e:
        raise MiniMaxError(f"MiniMax API 超时: {e}") from e
    except httpx.HTTPError as e:
        raise MiniMaxError(f"MiniMax API 网络错误: {e}") from e

    if resp.status_code != 200:
        raise MiniMaxError(
            f"MiniMax API 错误: HTTP {resp.status_code} - {resp.text[:500]}"
        )

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise MiniMaxError(f"MiniMax API 响应解析失败: {data}") from e


def chat_with_retry(
    messages: List[Dict[str, str]],
    *,
    max_retries: int = 3,
    backoff: float = 2.0,
    **kwargs: Any,
) -> str:
    """带指数退避的重试。"""
    last_err: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            return chat(messages, **kwargs)
        except MiniMaxError as e:
            last_err = e
            if attempt < max_retries - 1:
                wait = backoff ** attempt
                time.sleep(wait)
    raise MiniMaxError(f"MiniMax API 重试 {max_retries} 次失败: {last_err}")


def _cli() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--prompt", required=True)
    p.add_argument("--model", default=None)
    p.add_argument("--system", default=None)
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--max-tokens", type=int, default=4096)
    args = p.parse_args()

    msgs: List[Dict[str, str]] = []
    if args.system:
        msgs.append({"role": "system", "content": args.system})
    msgs.append({"role": "user", "content": args.prompt})
    print(chat(msgs, model=args.model, temperature=args.temperature, max_tokens=args.max_tokens))


if __name__ == "__main__":
    _cli()
