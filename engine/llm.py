"""
LLM调用适配层 — 引擎内部需要做语义理解时调用。
不绑定任何特定模型，通过环境变量配置。
"""

import os, json, subprocess, sys
from pathlib import Path

def llm_call(prompt: str, system: str = "You are a skill distillation engine. Respond with valid JSON only.") -> str:
    """
    调用LLM并返回文本响应。超时 5 秒。
    配置方式（优先级从高到低）：
      1. LLM_COMMAND 环境变量
      2. OPENAI_API_KEY 环境变量
      3. 无配置 → 立即 raise（不阻塞）
    """
    timeout = int(os.environ.get("LLM_TIMEOUT", "5"))

    # 检查是否有任何 backend 可用
    has_llm = os.environ.get("LLM_COMMAND") or os.environ.get("OPENAI_API_KEY")
    if not has_llm and not _cli_available():
        raise RuntimeError("no LLM backend — set LLM_COMMAND or OPENAI_API_KEY")

    # 方案1：自定义命令
    cmd_template = os.environ.get("LLM_COMMAND")
    if cmd_template:
        escaped = prompt.replace("'", "'\\''")
        cmd = cmd_template.replace("{prompt}", escaped)
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()

    # 方案2：OpenAI 兼容 API
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        try:
            import urllib.request
            base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
            data = json.dumps({
                "model": os.environ.get("LLM_MODEL", "gpt-4o-mini"),
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 4096
            }).encode()
            req = urllib.request.Request(
                f"{base}/chat/completions",
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
            )
            resp = urllib.request.urlopen(req, timeout=timeout)
            body = json.loads(resp.read())
            return body["choices"][0]["message"]["content"]
        except Exception as e:
            sys.stderr.write(f"[llm.py] OpenAI call failed: {e}\n")

    raise RuntimeError(
        "llm_call failed: No LLM backend responded.\n"
        "Set: export LLM_COMMAND='...' or export OPENAI_API_KEY=sk-..."
    )


def _cli_available() -> bool:
    try:
        subprocess.run(["which", "claude"], capture_output=True, timeout=2)
        return True
    except Exception:
        return False


def llm_call_json(prompt: str, system: str = "") -> dict:
    """调用LLM并解析JSON响应"""
    full_prompt = prompt
    if system:
        full_prompt = system + "\n\n" + prompt
    
    response = llm_call(full_prompt)
    
    # 尝试提取JSON（可能被包裹在```json ... ```中）
    if "```json" in response:
        start = response.index("```json") + 7
        end = response.index("```", start)
        response = response[start:end].strip()
    elif "```" in response:
        start = response.index("```") + 3
        end = response.index("```", start)
        response = response[start:end].strip()
    
    return json.loads(response)
