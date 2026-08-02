"""SonarQube-backed SmellDetector adapter (Software Specification §3.2, §5.2).

Implements the same ``detect(module) -> list[SmellInstance]`` contract as
seqrefactor.detect.native, so it is a drop-in replacement wherever a real
SonarQube server is available: it queries the Issues Search Web API
(``/api/issues/search``) for a project that has already been analysed by
`sonar-scanner`, and maps CODE_SMELL issues onto our category vocabulary.

STATUS: this client is a real, complete HTTP implementation, but it has not
been exercised against a live SonarQube server in the environment this
project was built in (no server was reachable on localhost:9000 at build
time -- see README.md "Verification" section). Treat it as implemented but
unverified until run against a real instance; seqrefactor.detect.native is
the detector every test and the reference pipeline run actually exercises.

Configuration is read from the environment (see .env.example):
``SONARQUBE_URL`` (default http://localhost:9000) and ``SONARQUBE_TOKEN``.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

from seqrefactor.model import Module, SmellInstance

# Best-effort mapping from Sonar's Java rule keys to this project's smell
# categories (Table in §7.3 / paper Table I). Sonar's taxonomy is finer
# grained than Fowler's catalogue, so this is a modelling choice, not a
# claim of a canonical mapping -- extend it as needed for a given ruleset.
RULE_KEY_TO_CATEGORY: dict[str, str] = {
    "java:S1448": "GodClass",  # "Classes should not have too many methods"
    "java:S3776": "LongMethod",  # "Cognitive Complexity should not be too high"
    "java:S138": "LongMethod",  # "Methods should not have too many lines"
    "java:S4144": "DuplicatedCode",  # "Methods should not have identical implementations"
    "java:S1192": "DuplicatedCode",  # "String literals should not be duplicated"
    "java:S1301": "BigSwitch",  # "switch statements should have at least 3 cases" (proxy)
    "java:S1141": "MessageChains",  # nested try or deep chains (proxy, ruleset-dependent)
    "java:S1226": "FeatureEnvy",  # parameter reassignment (weak proxy; prefer S3776 co-signal)
}


class SonarUnavailable(RuntimeError):
    """Raised when the SonarQube server cannot be reached or returns an error."""


@dataclass(frozen=True)
class SonarConfig:
    base_url: str
    token: str | None
    project_key: str

    @classmethod
    def from_env(cls, project_key: str) -> "SonarConfig":
        return cls(
            base_url=os.environ.get("SONARQUBE_URL", "http://localhost:9000").rstrip("/"),
            token=os.environ.get("SONARQUBE_TOKEN") or None,
            project_key=project_key,
        )


def _auth_header(token: str | None) -> dict[str, str]:
    if not token:
        return {}
    encoded = base64.b64encode(f"{token}:".encode()).decode()
    return {"Authorization": f"Basic {encoded}"}


def fetch_issues(config: SonarConfig, page_size: int = 500) -> list[dict]:
    """Fetch all CODE_SMELL issues for ``config.project_key``, paginated."""
    issues: list[dict] = []
    page = 1
    while True:
        query = (
            f"{config.base_url}/api/issues/search"
            f"?componentKeys={config.project_key}&types=CODE_SMELL"
            f"&ps={page_size}&p={page}"
        )
        request = urllib.request.Request(query, headers=_auth_header(config.token))
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise SonarUnavailable(f"could not reach SonarQube at {config.base_url}: {exc}") from exc

        page_issues = payload.get("issues", [])
        issues.extend(page_issues)
        total = payload.get("total", len(issues))
        if len(issues) >= total or not page_issues:
            break
        page += 1
    return issues


def _issue_to_smell(issue: dict, index: int) -> SmellInstance | None:
    rule = issue.get("rule", "")
    category = RULE_KEY_TO_CATEGORY.get(rule)
    if category is None:
        return None
    component = issue.get("component", "")
    # component looks like "<projectKey>:src/main/java/pkg/Foo.java"; the qualified
    # element name is recovered from the file path, not from Sonar's textRange alone.
    element = component.split(":", 1)[-1]
    severity_map = {"BLOCKER": 1.0, "CRITICAL": 0.8, "MAJOR": 0.6, "MINOR": 0.3, "INFO": 0.1}
    severity = severity_map.get(issue.get("severity", "MINOR"), 0.3)
    return SmellInstance(
        id=f"sonar-{index}",
        category=category,
        loc=[element],
        severity=severity,
    )


def detect(module: Module, project_key: str | None = None) -> list[SmellInstance]:
    """Query a running SonarQube server for a previously-analysed project.

    This does NOT trigger `sonar-scanner` itself (running a scan is an
    out-of-band CI/build step); it queries issues for a project that has
    already been analysed. ``project_key`` defaults to ``module.name``.
    """
    config = SonarConfig.from_env(project_key or module.name)
    issues = fetch_issues(config)
    smells: list[SmellInstance] = []
    for i, issue in enumerate(issues):
        smell = _issue_to_smell(issue, i)
        if smell is not None:
            smells.append(smell)
    return smells


def is_available(project_key: str) -> bool:
    config = SonarConfig.from_env(project_key)
    try:
        fetch_issues(config, page_size=1)
    except SonarUnavailable:
        return False
    return True
