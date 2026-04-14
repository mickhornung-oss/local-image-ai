from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "http://127.0.0.1:8090"
DEFAULT_SERIES_PATH = REPO_ROOT / "docs" / "identity_research_test_series_v1.json"
RUNS_ROOT = REPO_ROOT / "data" / "identity_research_runs"
RESULTS_ROOT = REPO_ROOT / "data" / "results"
SUPPORTED_PROVIDERS = ("instantid", "pulid_v11")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_id_now() -> str:
    return f"identity-research-run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"


def http_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict | None = None,
    timeout: int = 900,
) -> tuple[int, dict]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib_request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib_request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.load(resp)
    except urllib_error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"status": "error", "raw_body": raw}
        return exc.code, parsed


def load_series(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_reference_image_id(base_url: str, explicit_reference_image_id: str | None) -> tuple[str, dict]:
    if explicit_reference_image_id:
        status_code, health = http_json(f"{base_url.rstrip('/')}/health", timeout=60)
        if status_code != 200:
            raise RuntimeError("health_unavailable")
        return explicit_reference_image_id, health

    status_code, health = http_json(f"{base_url.rstrip('/')}/health", timeout=60)
    if status_code != 200:
        raise RuntimeError("health_unavailable")
    reference_payload = health.get("reference_image")
    if not isinstance(reference_payload, dict):
        raise RuntimeError("missing_reference_image")
    image_id = str(reference_payload.get("image_id") or "").strip()
    if not image_id:
        raise RuntimeError("missing_reference_image")
    return image_id, health


def read_result_metadata(result_id: str) -> dict | None:
    candidate = RESULTS_ROOT / f"{Path(result_id).name}.json"
    if not candidate.exists():
        return None
    return json.loads(candidate.read_text(encoding="utf-8"))


def build_report_markdown(manifest: dict) -> str:
    lines: list[str] = []
    lines.append(f"# Identity Research A/B Run {manifest['run_id']}")
    lines.append("")
    lines.append(f"- created_at: `{manifest['created_at']}`")
    lines.append(f"- reference_image_id: `{manifest['reference_image_id']}`")
    lines.append(f"- series_id: `{manifest['series_id']}`")
    lines.append(f"- providers: `{', '.join(manifest['providers'])}`")
    lines.append("")
    lines.append("## Ergebnisuebersicht")
    lines.append("")
    lines.append(f"- total_runs: `{manifest['summary']['total_runs']}`")
    lines.append(f"- successful_runs: `{manifest['summary']['successful_runs']}`")
    lines.append(f"- failed_runs: `{manifest['summary']['failed_runs']}`")
    lines.append("")
    lines.append("## Testfaelle")
    lines.append("")
    for case in manifest["cases"]:
        lines.append(f"### {case['case_id']} - {case['title']}")
        lines.append("")
        lines.append(f"- prompt: `{case['prompt']}`")
        for provider_result in case["results"]:
            lines.append(f"- {provider_result['provider']}: status=`{provider_result['status']}` http=`{provider_result['http_status']}`")
            if provider_result.get("result_id"):
                lines.append(f"  result_id: `{provider_result['result_id']}`")
            if provider_result.get("output_file"):
                lines.append(f"  output_file: `{provider_result['output_file']}`")
            if provider_result.get("metadata_file"):
                lines.append(f"  metadata_file: `{provider_result['metadata_file']}`")
            if provider_result.get("duration_seconds") is not None:
                lines.append(f"  duration_seconds: `{provider_result['duration_seconds']}`")
            if provider_result.get("blocker"):
                lines.append(f"  blocker: `{provider_result['blocker']}`")
        lines.append("")
    lines.append("## Manuelles Bewertungsraster")
    lines.append("")
    lines.append("- Identitaetstreue: offen")
    lines.append("- Prompttreue: offen")
    lines.append("- Gesicht: offen")
    lines.append("- Haende: offen")
    lines.append("- Gesamteindruck: offen")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a small A/B identity research comparison on the isolated experimental endpoint.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--series-file", type=Path, default=DEFAULT_SERIES_PATH)
    parser.add_argument("--reference-image-id")
    parser.add_argument("--negative-prompt", default="")
    parser.add_argument("--providers", nargs="+", default=list(SUPPORTED_PROVIDERS))
    args = parser.parse_args()

    providers = [str(provider).strip().lower() for provider in args.providers if str(provider).strip()]
    if providers != list(SUPPORTED_PROVIDERS):
        unknown = [provider for provider in providers if provider not in SUPPORTED_PROVIDERS]
        if unknown:
            print(json.dumps({"status": "error", "blocker": "unsupported_identity_research_provider", "providers": unknown}, ensure_ascii=True))
            return 2

    series = load_series(args.series_file.resolve())
    cases = series.get("cases")
    if not isinstance(cases, list) or not cases:
        print(json.dumps({"status": "error", "blocker": "invalid_test_series"}, ensure_ascii=True))
        return 2

    reference_image_id, health_payload = resolve_reference_image_id(args.base_url, args.reference_image_id)
    run_id = run_id_now()
    run_dir = (RUNS_ROOT / run_id).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    readiness_summary: dict[str, dict] = {}
    for provider in providers:
        status_code, payload = http_json(
            f"{args.base_url.rstrip('/')}/experimental/identity-research/readiness?provider={provider}",
            timeout=120,
        )
        readiness_summary[provider] = {
            "http_status": status_code,
            "payload": payload,
        }

    manifest: dict = {
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "base_url": args.base_url.rstrip("/"),
        "reference_image_id": reference_image_id,
        "reference_image": health_payload.get("reference_image") if isinstance(health_payload.get("reference_image"), dict) else None,
        "series_id": str(series.get("series_id") or "identity_research_series"),
        "series_file": str(args.series_file.resolve()),
        "providers": providers,
        "readiness": readiness_summary,
        "cases": [],
        "summary": {
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
        },
    }

    generate_url = f"{args.base_url.rstrip('/')}/experimental/identity-research/generate"
    for case in cases:
        case_id = str(case.get("case_id") or "").strip()
        title = str(case.get("title") or case_id).strip() or case_id
        prompt = str(case.get("prompt") or "").strip()
        if not case_id or not prompt:
            continue
        case_result = {
            "case_id": case_id,
            "title": title,
            "prompt": prompt,
            "results": [],
        }
        for provider in providers:
            started_at = time.perf_counter()
            status_code, response_payload = http_json(
                generate_url,
                method="POST",
                payload={
                    "prompt": prompt,
                    "negative_prompt": args.negative_prompt,
                    "reference_image_id": reference_image_id,
                    "provider": provider,
                },
                timeout=1800,
            )
            duration_seconds = round(time.perf_counter() - started_at, 3)
            result_id = str(response_payload.get("result_id") or "").strip() or None
            metadata_payload = read_result_metadata(result_id) if result_id else None
            metadata_file = str((RESULTS_ROOT / f"{result_id}.json").resolve()) if result_id and metadata_payload is not None else None
            output_file = str(metadata_payload.get("source_output_file") or "").strip() or response_payload.get("output_file")
            success = status_code == 200 and response_payload.get("status") == "ok"
            case_result["results"].append(
                {
                    "provider": provider,
                    "status": "success" if success else "failure",
                    "http_status": status_code,
                    "result_id": result_id,
                    "output_file": output_file,
                    "metadata_file": metadata_file,
                    "duration_seconds": duration_seconds,
                    "blocker": str(response_payload.get("blocker") or "").strip() or None,
                    "error_type": str(response_payload.get("error_type") or "").strip() or None,
                    "response": response_payload,
                }
            )
            manifest["summary"]["total_runs"] += 1
            if success:
                manifest["summary"]["successful_runs"] += 1
            else:
                manifest["summary"]["failed_runs"] += 1
        manifest["cases"].append(case_result)

    manifest_path = run_dir / "manifest.json"
    report_path = run_dir / "report.md"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=True, indent=2), encoding="utf-8")
    report_path.write_text(build_report_markdown(manifest), encoding="utf-8")

    print(json.dumps({
        "status": "ok",
        "run_id": run_id,
        "manifest": str(manifest_path.resolve()),
        "report": str(report_path.resolve()),
        "summary": manifest["summary"],
    }, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
