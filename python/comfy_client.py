import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import requests


DEFAULT_BASE_URL = "http://127.0.0.1:8188"
DEFAULT_POLL_INTERVAL = 1.0
IMAGE_OUTPUT_KEYS = ("images",)
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


class ComfyClientError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        error_type: str = "api_error",
        payload: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.payload = payload or {}


class ComfyClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def health_check(self) -> dict[str, Any]:
        return self._request_json("GET", "/system_stats")

    def queue_prompt(self, prompt: dict[str, Any], client_id: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"prompt": prompt}
        if client_id:
            payload["client_id"] = client_id
        return self._request_json("POST", "/prompt", json_payload=payload)

    def get_history(self, prompt_id: str) -> dict[str, Any]:
        history = self._request_json("GET", f"/history/{prompt_id}")
        if not isinstance(history, dict):
            raise ComfyClientError("Unexpected history payload received from ComfyUI.")
        return history

    def get_prompt_result(self, prompt_id: str) -> dict[str, Any] | None:
        history = self.get_history(prompt_id)
        entry = history.get(prompt_id)
        if entry is None:
            return None
        if not isinstance(entry, dict):
            raise ComfyClientError("Unexpected prompt history entry received from ComfyUI.")
        return entry

    def wait_for_prompt_result(
        self,
        prompt_id: str,
        *,
        output_dir: Path | None = None,
        timeout: int = 180,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
    ) -> dict[str, Any]:
        deadline = time.time() + timeout

        while time.time() < deadline:
            history_entry = self.get_prompt_result(prompt_id)
            if history_entry is not None:
                result = self.build_prompt_result(
                    prompt_id=prompt_id,
                    history_entry=history_entry,
                    output_dir=output_dir,
                )
                if result["completed"] or result["error_text"] is not None:
                    return result
            time.sleep(poll_interval)

        raise ComfyClientError(
            f"Timed out after {timeout}s while waiting for prompt_id {prompt_id}",
            error_type="timeout",
        )

    def build_prompt_result(
        self,
        *,
        prompt_id: str,
        history_entry: dict[str, Any],
        output_dir: Path | None = None,
    ) -> dict[str, Any]:
        status = history_entry.get("status")
        status_dict = status if isinstance(status, dict) else {}
        outputs = history_entry.get("outputs")
        outputs_dict = outputs if isinstance(outputs, dict) else {}
        messages = status_dict.get("messages")
        message_list = messages if isinstance(messages, list) else []
        output_files = self.extract_output_files(history_entry, output_dir=output_dir)
        error_text = self.extract_history_error(history_entry)

        return {
            "prompt_id": prompt_id,
            "completed": bool(status_dict.get("completed", False)),
            "status_str": status_dict.get("status_str"),
            "messages": message_list,
            "outputs": outputs_dict,
            "output_files": output_files,
            "output_file": output_files[0] if output_files else None,
            "history_nodes_seen": len(outputs_dict),
            "history": history_entry,
            "error_text": error_text,
        }

    def extract_output_files(
        self,
        history_entry: dict[str, Any],
        *,
        output_dir: Path | None = None,
    ) -> list[str]:
        outputs = history_entry.get("outputs")
        if not isinstance(outputs, dict):
            return []

        files: list[str] = []
        seen_files: set[str] = set()
        for _, node_output in sorted(outputs.items(), key=self._node_sort_key):
            if not isinstance(node_output, dict):
                continue
            for key in IMAGE_OUTPUT_KEYS:
                assets = node_output.get(key)
                if not isinstance(assets, list):
                    continue
                for asset in assets:
                    if not isinstance(asset, dict):
                        continue
                    filename = asset.get("filename")
                    if not isinstance(filename, str) or not filename:
                        continue
                    if Path(filename).suffix.lower() not in IMAGE_EXTENSIONS:
                        continue
                    if output_dir is None:
                        normalized = filename
                    else:
                        subfolder = asset.get("subfolder")
                        if not isinstance(subfolder, str):
                            subfolder = ""
                        normalized = str((output_dir / subfolder / filename).resolve())
                    if normalized in seen_files:
                        continue
                    seen_files.add(normalized)
                    files.append(normalized)
        return files

    def extract_history_error(self, history_entry: dict[str, Any]) -> str | None:
        status = history_entry.get("status")
        if not isinstance(status, dict):
            return None

        messages = status.get("messages")
        if isinstance(messages, list):
            for message in messages:
                if not isinstance(message, list) or len(message) != 2:
                    continue
                message_type = str(message[0]).lower()
                if message_type not in {"execution_error", "execution_interrupted"}:
                    continue
                details = message[1]
                if isinstance(details, dict):
                    for key in ("exception_message", "error", "message", "exception_type"):
                        value = details.get(key)
                        if isinstance(value, str) and value:
                            return value
                return str(message_type)

        status_str = status.get("status_str")
        if isinstance(status_str, str) and status_str.lower() not in {"success", "completed"}:
            return f"execution status {status_str}"

        return None

    def latest_output_file(self, output_dir: Path) -> Path | None:
        output_dir = output_dir.resolve()
        if not output_dir.exists():
            return None

        candidates = sorted(
            (path.resolve() for path in output_dir.rglob("*") if path.is_file()),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        return candidates[0] if candidates else None

    def _node_sort_key(self, item: tuple[Any, Any]) -> tuple[int, int, str]:
        node_id = str(item[0])
        if node_id.isdigit():
            return (0, int(node_id), node_id)
        return (1, 0, node_id.lower())

    def _request_json(
        self,
        method: str,
        path: str,
        json_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = requests.request(method, url, json=json_payload, timeout=self.timeout)
        except requests.ConnectionError as exc:
            raise ComfyClientError(
                f"Could not connect to ComfyUI at {self.base_url}. Is scripts/run_comfyui.ps1 running?",
                error_type="api_error",
            ) from exc
        except requests.Timeout as exc:
            raise ComfyClientError(
                f"Request to {url} timed out after {self.timeout}s.",
                error_type="timeout",
            ) from exc
        except requests.RequestException as exc:
            raise ComfyClientError(f"HTTP request to {url} failed: {exc}", error_type="api_error") from exc

        payload: dict[str, Any] | None = None
        try:
            parsed = response.json()
            if isinstance(parsed, dict):
                payload = parsed
        except ValueError:
            payload = None

        if response.status_code >= 400:
            if payload is not None:
                raise ComfyClientError(
                    f"ComfyUI returned HTTP {response.status_code} for {url}: {json.dumps(payload, ensure_ascii=True)}",
                    error_type="api_error",
                    payload=payload,
                )
            body = response.text.strip()
            raise ComfyClientError(
                f"ComfyUI returned HTTP {response.status_code} for {url}: {body}",
                error_type="api_error",
            )

        if payload is None:
            raise ComfyClientError(
                f"ComfyUI returned invalid JSON for {url}: {response.text[:300]}",
                error_type="api_error",
            )

        return payload


def _load_prompt_file(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ComfyClientError(f"Could not read workflow file: {path}") from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ComfyClientError(f"Invalid JSON in workflow file {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ComfyClientError(f"Workflow file {path} must contain a JSON object at the top level.")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Queue an API workflow against a local ComfyUI instance.")
    parser.add_argument("workflow", type=Path, help="Path to an API-format workflow JSON file.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="ComfyUI base URL.")
    parser.add_argument("--timeout", type=int, default=30, help="Per-request timeout in seconds.")
    parser.add_argument("--wait", action="store_true", help="Wait for prompt completion.")
    parser.add_argument("--output-dir", type=Path, help="Output directory for output path resolution.")
    parser.add_argument("--wait-timeout", type=int, default=180, help="Timeout for --wait.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        workflow = _load_prompt_file(args.workflow)
        client = ComfyClient(base_url=args.base_url, timeout=args.timeout)
        result = client.queue_prompt(workflow)
        print(json.dumps(result, indent=2))

        prompt_id = result.get("prompt_id")
        if not isinstance(prompt_id, str) or not prompt_id:
            raise ComfyClientError("ComfyUI response did not contain prompt_id.")

        if args.wait:
            prompt_result = client.wait_for_prompt_result(
                prompt_id,
                output_dir=args.output_dir,
                timeout=args.wait_timeout,
            )
            print(json.dumps(prompt_result, indent=2))
    except ComfyClientError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
