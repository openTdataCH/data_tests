"""
Utilities (classes, functions) for tests on Bruno API test-files.
Executes a single Bruno-Resource (.bru Request or folder) with bru CLI.
Creates a JSON-Report, parses it and returns errors/successes to DataTest.
"""

import json
import os
import subprocess
import tempfile
from typing import Dict, List, Optional, Tuple


def which(cmd: str) -> Optional[str]:
    paths = os.environ.get("PATH", "").split(os.pathsep)
    exts = [""]
    if os.name == "nt":
        pathext = os.environ.get("PATHEXT", ".EXE;.CMD;.BAT")
        exts = pathext.split(";")
    for p in paths:
        candidate = os.path.join(p, cmd)
        for ext in exts:
            full = candidate + ext
            if os.path.isfile(full) and os.access(full, os.X_OK):
                return full
    return None


def build_env_var_flags(env_vars) -> List[str]:
    flags: List[str] = []
    for key, value in env_vars.items():
        if value is None:
            value = ""
        flags.extend(["--env-var", f"{key}={value}"])
    return flags


class BrunoRunner:
    def __init__(
            self,
            resource_path: str,
            data_test=None,
            env_name: Optional[str] = None,
            working_dir: Optional[str] = None,
            extra_flags: Optional[List[str]] = None,
    ) -> None:
        self.resource_path = resource_path
        self.data_test = data_test
        self.env_name = env_name
        self.working_dir = working_dir
        self.extra_flags = extra_flags or ["--noproxy"]
        self._bru = which("bru") or which("bru.cmd")

    def build_cmd(self, report_path: str, env_vars: Dict[str, str]) -> List[str]:
        cmd: List[str] = [
            "bru", "run", self.resource_path,
            "--format", "json",
            "--output", report_path
        ]

        if self.env_name:
            cmd.extend(["--env", self.env_name])

        if self.extra_flags:
            cmd.extend(self.extra_flags)

        cmd.extend(build_env_var_flags(env_vars))
        return cmd

    def parse_stdout_for_tests(self, stdout: str) -> List[dict]:
        assertions = []
        lines = stdout.splitlines()
        in_test_section = False

        for i, line in enumerate(lines):
            trimmed = line.strip()
            if "Post-Response Tests" in trimmed:
                in_test_section = True
                continue
            if "Execution Summary" in trimmed or "┌───" in trimmed or "Metric" in trimmed:
                in_test_section = False
                break

            if not in_test_section:
                continue

            if "│" in trimmed or "├─" in trimmed or "└─" in trimmed:
                continue

            if "✓" in trimmed:
                name = trimmed.replace("✓", "").strip()
                assertions.append({"name": name, "status": "passed", "message": None})

            elif "✕" in trimmed:
                name = trimmed.replace("✕", "").strip()
                error_msg = ""
                if i + 1 < len(lines):
                    next_line = lines[i+1].strip()
                    if not any(x in next_line for x in ["✓", "✕", "┌", "│"]):
                        error_msg = next_line

                assertions.append({"name": name, "status": "failed", "message": error_msg})

        return assertions

    def parse_json_report(self, payload) -> dict:
        result = {
            "summary": {"requests": 0, "tests": 0, "assertions": {"passed": 0, "failed": 0}},
            "requests": [],
            "failures": []
        }

        def find_key_recursive(data, target_key):
            if isinstance(data, dict):
                if target_key in data:
                    return data[target_key]
                for v in data.values():
                    found = find_key_recursive(v, target_key)
                    if found: return found
            elif isinstance(data, list):
                for item in data:
                    found = find_key_recursive(item, target_key)
                    if found: return found
            return None

        items = payload if isinstance(payload, list) else [payload]

        total_passed = 0
        total_failed = 0
        normalized_requests = []

        for it in items:
            if not isinstance(it, dict): continue

            req_name = it.get("name") or it.get("request", {}).get("name") or "Unknown"

            res_obj = it.get("response") or it.get("result", {}).get("response") or {}
            http_status = res_obj.get("status") if isinstance(res_obj, dict) else it.get("status")

            duration = it.get("runtime") or it.get("duration") or res_obj.get("responseTime") or 0

            raw_tests = find_key_recursive(it, "testResults") or find_key_recursive(it, "assertions") or []

            it_assertions = []
            for t in raw_tests:
                t_desc = t.get("description") or t.get("name") or "Test"
                raw_status = str(t.get("status", "")).lower()
                is_passed = raw_status in ["pass", "passed", "success"]
                t_error = t.get("error") or t.get("message")

                it_assertions.append({
                    "name": t_desc,
                    "status": "passed" if is_passed else "failed",
                    "message": t_error
                })

                if is_passed:
                    total_passed += 1
                else:
                    total_failed += 1
                    result["failures"].append({
                        "request": req_name,
                        "assertion": t_desc,
                        "message": t_error
                    })

            any_fail = any(a["status"] == "failed" for a in it_assertions)
            request_status = "failed" if any_fail else "passed"

            normalized_requests.append({
                "name": req_name,
                "status": request_status,
                "duration_ms": duration,
                "response": {"status": http_status},
                "assertions": it_assertions
            })

        result["requests"] = normalized_requests
        result["summary"] = {
            "requests": len(normalized_requests),
            "tests": total_passed + total_failed,
            "assertions": {"passed": total_passed, "failed": total_failed}
        }
        return result

    def run(
            self,
            env_vars: Optional[Dict[str, str]] = None,
            timeout: Optional[int] = None,
            strict: bool = True
    ) -> Tuple[Optional[dict], int, str]:
        """
        - env_vars: KEY->VALUE mapping, is passed as --env-var KEY=VALUE to bru and put in the sub-Env.
        – strict=True: Return None if returncode != 0 or assertions failed.
        """
        if not self._bru:
            msg = "bru CLI not found. Please install Bruno CLI and add it in PATH."
            self.data_test.log_failure(msg)
            raise FileNotFoundError(msg)

        env_vars = env_vars or {}

        with tempfile.TemporaryDirectory(prefix="bru-run-") as tmpd:
            report_path = os.path.join(tmpd, "report.json")
            cmd_list = self.build_cmd(report_path, env_vars)
            cmd = " ".join([f'"{arg}"' if " " in arg or "\\" in arg or "/" in arg else arg for arg in cmd_list])
            child_env = os.environ.copy()
            child_env.update(env_vars)

            try:
                proc = subprocess.run(
                    cmd,
                    cwd=self.working_dir,
                    env=child_env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=timeout,
                    shell=True
                )
            except subprocess.TimeoutExpired:
                self.data_test.log_failure(f"Timeout when executing: {self.resource_path}")
                return None, 0, ""
            except Exception as e:
                self.data_test.log_failure(f"Error when starting bru: {e}")
                return None, 0, ""

            stdout = proc.stdout or ""
            stderr = proc.stderr or ""

            report: Optional[dict] = None
            if os.path.exists(report_path):
                try:
                    with open(report_path, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                    report = self.parse_json_report(raw)
                except Exception as e:
                    self.data_test.log_warning(f"Parsing JSON-Report was not possible: {e}.")

            if report is None:
                self.data_test.log_failure(f"Critical error: Bruno-CLI did not create a report!")
                self.data_test.log_failure(f"CLI STDOUT:\n{stdout}")
                if stderr:
                    self.data_test.log_failure(f"CLI STDERR:\n{stderr}")
                return None, 0, stdout

            executed_requests = report["summary"]["requests"]
            failed_assertions = report["summary"]["assertions"]["failed"]

            if executed_requests == 0:
                self.data_test.log_warning(f"Bruno executed nothing. CLI Output: {stdout}")
                if stderr:
                    self.data_test.log_warning(f"Bruno Error Output: {stderr}")

            if failed_assertions > 0 and report.get("failures"):
                for f in report["failures"]:
                    req = f.get("request")
                    asrt = f.get("assertion")
                    msg = f.get("message")
                    self.data_test.log_failure(f"Assertion failed - Request: {req} | Test: {asrt} | Details: {msg}")

            if report.get("requests"):
                for r in report["requests"]:
                    r_name = r.get("name")
                    r_status = r.get("status")
                    r_code = None
                    if isinstance(r.get("response"), dict):
                        r_code = r["response"].get("status")
                    if r_status == "failed":
                        self.data_test.log_failure(f"Request failed: {r_name} (HTTP {r_code})")

            success = (proc.returncode == 0) and (failed_assertions == 0)

            report = None
            if os.path.exists(report_path):
                with open(report_path, "r", encoding="utf-8") as f:
                    report = self.parse_json_report(json.load(f))

            if report and report["summary"]["tests"] == 0:
                stdout_tests = self.parse_stdout_for_tests(stdout)
                if stdout_tests:
                    report["requests"][0]["assertions"] = stdout_tests
                    f_count = sum(1 for a in stdout_tests if a["status"] == "failed")
                    p_count = sum(1 for a in stdout_tests if a["status"] == "passed")
                    report["summary"]["tests"] = len(stdout_tests)
                    report["summary"]["assertions"]["failed"] = f_count
                    report["summary"]["assertions"]["passed"] = p_count

                    report["failures"] = [{"assertion": a["name"], "message": a["message"]}
                                          for a in stdout_tests if a["status"] == "failed"]

            return report, 1 if report else 0, stdout
