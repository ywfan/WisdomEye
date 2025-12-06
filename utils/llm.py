import os
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests


_PROVIDERS_DEFAULTS: Dict[str, Dict[str, str]] = {
    "dashscope": {"key_env": "DASHSCOPE_API_KEY", "base_env": "DASHSCOPE_BASE_URL", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "default_model": "qwen-plus"},
    "moonshot": {"key_env": "MOONSHOT_API_KEY", "base_env": "MOONSHOT_BASE_URL", "base_url": "https://api.moonshot.cn/v1", "default_model": "moonshot-v1-8k"},
    "aihub": {"key_env": "AIHUB_API_KEY", "base_env": "AIHUB_BASE_URL", "base_url": "https://aihubmix.com/v1", "default_model": "deepseek-chat"},
    "deepseek": {"key_env": "DEEPSEEK_API_KEY", "base_env": "DEEPSEEK_BASE_URL", "base_url": "https://api.deepseek.com/v1", "default_model": "deepseek-chat"},
}


def _mask(secret: Optional[str]) -> str:
    if not secret:
        return ""
    s = str(secret)
    if len(s) <= 4:
        return "***"
    return s[:2] + "***" + s[-2:]


def _load_dotenv(dotenv_path: Optional[str]) -> None:
    p = dotenv_path or str(os.path.join(os.getcwd(), ".env"))
    try:
        with open(p, "r", encoding="utf-8") as f:
            for line in f.readlines():
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                if "=" in s:
                    k, v = s.split("=", 1)
                    val = v.strip()
                    if (val.startswith("\"") and val.endswith("\"")) or (val.startswith("'") and val.endswith("'")):
                        val = val[1:-1]
                    os.environ.setdefault(k.strip(), val)
    except Exception:
        pass


class LLMClient:
    def __init__(self, api_key: Optional[str], base_url: str, model: str, temperature: float = 0.0, max_tokens: Optional[int] = None, timeout: float = 200.0, retries: int = 2):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = float(temperature)
        self.max_tokens = max_tokens
        self.timeout = float(timeout)
        self.retries = int(retries)

    def _approx_tokens(self, s: str) -> int:
        try:
            # naive token estimator ~4 chars per token
            return max(1, int(len(s) / 4))
        except Exception:
            return 0

    def _log_trace(self, record: Dict[str, Any]) -> None:
        try:
            root = Path(os.getcwd()) / "output" / "logs"
            root.mkdir(parents=True, exist_ok=True)
            path = root / "trace.jsonl"
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def chat(self, messages: Union[str, List[Dict[str, str]]], stream: bool = False) -> Union[str, List[str]]:
        try:
            if (os.getenv("FEATURE_NEW_PIPELINE") == "1") and (not stream):
                from infra.llm_adapter import LLMAdapter
                adapter = LLMAdapter(api_key=self.api_key, base_url=self.base_url, model=self.model, temperature=self.temperature, max_tokens=self.max_tokens, timeout=self.timeout, retries=self.retries)
                return adapter.chat(messages, stream=False)
        except Exception:
            pass
        if isinstance(messages, str):
            msgs = [{"role": "user", "content": messages}]
        else:
            msgs = messages
        url = self.base_url + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body: Dict[str, Any] = {"model": self.model, "messages": msgs, "temperature": self.temperature}
        if self.max_tokens:
            body["max_tokens"] = int(self.max_tokens)
        body["stream"] = bool(stream)
        try:
            print(f"[LLM请求] model={self.model} base={self.base_url} temperature={self.temperature} max_tokens={self.max_tokens}")
            for m in msgs:
                c = str(m.get("content", ""))
                print(f"[LLM输入] role={m.get('role','')} content={c[:800]}")
        except Exception:
            pass
        t0 = time.time()
        if not stream:
            last_err = None
            tried_alt = False
            for attempt in range(max(1, self.retries)):
                try:
                    resp = requests.post(url, headers=headers, json=body, timeout=self.timeout)
                    if not resp.ok:
                        try:
                            txt = resp.text or ""
                            print(f"[LLM错误输出] {txt[:400]}")
                        except Exception:
                            pass
                        break
                    try:
                        data = resp.json()
                        choices = data.get("choices") or []
                        if choices:
                            m = choices[0].get("message") or {}
                            out = m.get("content") or choices[0].get("text") or ""
                            try:
                                print(f"[LLM输出] {str(out)[:800]}")
                            except Exception:
                                pass
                            elapsed = time.time() - t0
                            try:
                                prompt_text = "\n".join([str(m.get("content") or "") for m in msgs])
                                self._log_trace({
                                    "kind": "llm_chat",
                                    "model": self.model,
                                    "base": self.base_url,
                                    "temperature": self.temperature,
                                    "stream": False,
                                    "tokens_in": self._approx_tokens(prompt_text),
                                    "tokens_out": self._approx_tokens(out),
                                    "chars_in": len(prompt_text),
                                    "chars_out": len(out),
                                    "elapsed_sec": round(elapsed, 3),
                                    "status": "ok",
                                })
                            except Exception:
                                pass
                            return out
                        # no choices
                        out_txt = resp.text or ""
                        elapsed = time.time() - t0
                        try:
                            prompt_text = "\n".join([str(m.get("content") or "") for m in msgs])
                            self._log_trace({
                                "kind": "llm_chat",
                                "model": self.model,
                                "base": self.base_url,
                                "temperature": self.temperature,
                                "stream": False,
                                "tokens_in": self._approx_tokens(prompt_text),
                                "tokens_out": self._approx_tokens(out_txt),
                                "chars_in": len(prompt_text),
                                "chars_out": len(out_txt),
                                "elapsed_sec": round(elapsed, 3),
                                "status": "ok_no_choices",
                            })
                        except Exception:
                            pass
                        return out_txt
                    except Exception:
                        out_txt = resp.text or ""
                        elapsed = time.time() - t0
                        try:
                            prompt_text = "\n".join([str(m.get("content") or "") for m in msgs])
                            self._log_trace({
                                "kind": "llm_chat",
                                "model": self.model,
                                "base": self.base_url,
                                "temperature": self.temperature,
                                "stream": False,
                                "tokens_in": self._approx_tokens(prompt_text),
                                "tokens_out": self._approx_tokens(out_txt),
                                "chars_in": len(prompt_text),
                                "chars_out": len(out_txt),
                                "elapsed_sec": round(elapsed, 3),
                                "status": "ok_text",
                            })
                        except Exception:
                            pass
                        return out_txt
                except Exception as e:
                    last_err = e
                    try:
                        print(f"[LLM错误] {e}")
                    except Exception:
                        pass
                    if not tried_alt:
                        alt_key = os.getenv("AIHUB_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or None
                        alt_base = os.getenv("AIHUB_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL") or None
                        if alt_key and alt_base:
                            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {alt_key}"}
                            url = alt_base.rstrip("/") + "/chat/completions"
                            tried_alt = True
                            try:
                                print("[LLM切换] fallback_provider=aihub/deepseek")
                            except Exception:
                                pass
                    time.sleep(min(1.0 + attempt, 2.0))
            elapsed = time.time() - t0
            try:
                prompt_text = "\n".join([str(m.get("content") or "") for m in msgs])
                self._log_trace({
                    "kind": "llm_chat",
                    "model": self.model,
                    "base": self.base_url,
                    "temperature": self.temperature,
                    "stream": False,
                    "tokens_in": self._approx_tokens(prompt_text),
                    "tokens_out": 0,
                    "chars_in": len(prompt_text),
                    "chars_out": 0,
                    "elapsed_sec": round(elapsed, 3),
                    "status": f"error:{type(last_err).__name__ if last_err else 'unknown'}",
                })
            except Exception:
                pass
            return ""
        else:
            res: List[str] = []
            tried_alt = False
            for attempt in range(max(1, self.retries)):
                try:
                    with requests.post(url, headers=headers, json=body, timeout=self.timeout, stream=True) as r:
                        if not r.ok:
                            try:
                                return [r.text or json.dumps(r.json())]
                            except Exception:
                                return [r.text or ""]
                        for chunk in r.iter_lines():
                            if not chunk:
                                continue
                            try:
                                s = chunk.decode("utf-8")
                                if s.startswith("data:"):
                                    s = s[5:].strip()
                                if s == "[DONE]":
                                    break
                                obj = json.loads(s)
                                delta = (((obj.get("choices") or [{}])[0]).get("delta") or {}).get("content")
                                if delta:
                                    res.append(delta)
                                    try:
                                        print(f"[LLM流输出] {str(delta)[:400]}")
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                        break
                except Exception as e:
                    try:
                        print(f"[LLM错误] {e}")
                    except Exception:
                        pass
                    if not tried_alt:
                        alt_key = os.getenv("AIHUB_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or None
                        alt_base = os.getenv("AIHUB_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL") or None
                        if alt_key and alt_base:
                            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {alt_key}"}
                            url = alt_base.rstrip("/") + "/chat/completions"
                            tried_alt = True
                            try:
                                print("[LLM切换] fallback_provider=aihub/deepseek")
                            except Exception:
                                pass
                    time.sleep(min(1.0 + attempt, 2.0))
            elapsed = time.time() - t0
            try:
                prompt_text = "\n".join([str(m.get("content") or "") for m in msgs])
                out_joined = "".join(res)
                self._log_trace({
                    "kind": "llm_chat",
                    "model": self.model,
                    "base": self.base_url,
                    "temperature": self.temperature,
                    "stream": True,
                    "tokens_in": self._approx_tokens(prompt_text),
                    "tokens_out": self._approx_tokens(out_joined),
                    "chars_in": len(prompt_text),
                    "chars_out": len(out_joined),
                    "elapsed_sec": round(elapsed, 3),
                    "status": "ok_stream",
                })
            except Exception:
                pass
            return res

    @classmethod
    def from_env(cls, role: Optional[str] = None, dotenv_path: Optional[str] = None, temperature: float = 0.0, max_tokens: Optional[int] = None) -> "LLMClient":
        if dotenv_path:
            _load_dotenv(dotenv_path)
        provider = os.getenv(f"LLM_{(role or 'DEFAULT').upper()}_PROVIDER") or os.getenv("LLM_DEFAULT_PROVIDER") or ""
        provider = provider.strip().lower()
        defaults = _PROVIDERS_DEFAULTS.get(provider) or {}
        api_key = os.getenv(defaults.get("key_env", "")) or ""
        base_url = os.getenv(defaults.get("base_env", "")) or defaults.get("base_url") or ""
        model = os.getenv(f"LLM_{(role or 'DEFAULT').upper()}_MODEL") or os.getenv("LLM_DEFAULT_MODEL") or (defaults.get("default_model") or "qwen-plus")
        return cls(api_key=api_key or None, base_url=base_url, model=model, temperature=temperature, max_tokens=max_tokens)

    def __repr__(self) -> str:
        return f"LLMClient(model={self.model}, base={self.base_url}, key={_mask(self.api_key)})"
