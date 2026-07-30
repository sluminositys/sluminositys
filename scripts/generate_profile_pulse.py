"""Generate a compact SVG telemetry card from the public GitHub API."""

from __future__ import annotations

import argparse
import html
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


def fetch_json(url: str, token: str | None) -> object:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "sluminositys-profile-workflow",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def generate(username: str, token: str | None) -> str:
    encoded_username = quote(username, safe="")
    user = fetch_json(f"https://api.github.com/users/{encoded_username}", token)
    repos = fetch_json(
        f"https://api.github.com/users/{encoded_username}/repos"
        "?per_page=100&type=owner&sort=updated",
        token,
    )
    if not isinstance(user, dict) or not isinstance(repos, list):
        raise TypeError("Unexpected GitHub API response")

    public_repos = int(user.get("public_repos", 0))
    followers = int(user.get("followers", 0))
    project_repos = [
        repo
        for repo in repos
        if not repo.get("fork") and repo.get("name", "").lower() != username.lower()
    ]
    now = datetime.now(timezone.utc)
    active_90d = 0
    for repo in project_repos:
        updated_at_value = str(repo.get("updated_at", ""))
        if not updated_at_value:
            continue
        updated_at_dt = datetime.fromisoformat(updated_at_value.replace("Z", "+00:00"))
        if (now - updated_at_dt).days <= 90:
            active_90d += 1
    source_mb = round(sum(int(repo.get("size", 0)) for repo in repos) / 1024)

    latest = project_repos[0] if project_repos else (repos[0] if repos else {})
    latest_name = html.escape(str(latest.get("name", "awaiting signal")))
    updated_at = str(latest.get("updated_at", ""))
    latest_date = updated_at[:10] if updated_at else "—"
    refreshed = now.strftime("%Y-%m-%d %H:%M UTC")

    metrics = (
        ("PUBLIC REPOS", public_repos, "#22d3ee"),
        ("ACTIVE · 90D", active_90d, "#60a5fa"),
        ("SOURCE MB", source_mb, "#a78bfa"),
        ("FOLLOWERS", followers, "#34d399"),
    )
    cards = []
    for index, (label, value, color) in enumerate(metrics):
        x = 34 + index * 241
        cards.append(
            f'''<g transform="translate({x} 70)">
  <rect width="208" height="92" rx="14" fill="#0f172a" stroke="{color}" stroke-opacity=".34"/>
  <text x="18" y="34" fill="{color}" font-size="25" font-weight="700">{value}</text>
  <text x="18" y="64" fill="#94a3b8" font-size="11" font-weight="600" letter-spacing="1.8">{label}</text>
</g>'''
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="230" viewBox="0 0 1000 230" role="img" aria-labelledby="title desc">
<title id="title">Live GitHub research telemetry for {html.escape(username)}</title>
<desc id="desc">Public repositories, recently active projects, source size, followers, and latest active project</desc>
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#020617"/><stop offset=".55" stop-color="#0f172a"/><stop offset="1" stop-color="#082f49"/>
  </linearGradient>
  <pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">
    <path d="M24 0H0V24" fill="none" stroke="#38bdf8" stroke-opacity=".04"/>
  </pattern>
  <linearGradient id="scan" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#22d3ee" stop-opacity="0"/><stop offset=".5" stop-color="#22d3ee" stop-opacity=".55"/><stop offset="1" stop-color="#22d3ee" stop-opacity="0"/>
  </linearGradient>
</defs>
<rect x="1" y="1" width="998" height="228" rx="20" fill="url(#bg)" stroke="#334155"/>
<rect x="1" y="1" width="998" height="228" rx="20" fill="url(#grid)"/>
<g font-family="Segoe UI, Inter, Arial, sans-serif">
  <circle cx="36" cy="36" r="5" fill="#22c55e"><animate attributeName="opacity" values=".25;1;.25" dur="1.8s" repeatCount="indefinite"/></circle>
  <text x="52" y="41" fill="#e2e8f0" font-size="14" font-weight="700" letter-spacing="2.4">LIVE RESEARCH TELEMETRY</text>
  <text x="964" y="41" text-anchor="end" fill="#64748b" font-size="11">{refreshed}</text>
  {''.join(cards)}
  <text x="34" y="198" fill="#64748b" font-size="11" font-weight="600" letter-spacing="1.5">LATEST PROJECT SIGNAL</text>
  <text x="230" y="198" fill="#cbd5e1" font-size="13" font-weight="600">{latest_name}</text>
  <text x="964" y="198" text-anchor="end" fill="#64748b" font-size="11">UPDATED {latest_date}</text>
</g>
<rect x="18" y="0" width="964" height="2" fill="url(#scan)" opacity=".55">
  <animate attributeName="y" values="8;220;8" dur="7s" repeatCount="indefinite"/>
</rect>
</svg>'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    svg = generate(args.username, os.environ.get("GITHUB_TOKEN"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(svg, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
