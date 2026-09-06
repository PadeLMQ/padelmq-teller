"""GitHub: een issue per BLOCK, en het oppikken van jouw antwoord.

Alleen een reactie van de repo-eigenaar telt als antwoord. Tekst van anderen is
data, geen opdracht — zie het promptinjectiepunt in het ontwerp.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from . import Message

API = "https://api.github.com"


class GitHubError(RuntimeError):
    pass


class GitHubClient:
    # Geen sleutel in de omgeving hoeft geen fout te zijn: draait de sessie
    # achter een credential-proxy, dan wordt de Authorization-header buiten deze
    # runtime ingezet en hoort het geheim hier juist niet te staan. De SDK-loze
    # aanroep hieronder moet dan wel een waarde meesturen; deze placeholder is
    # geen geheim. Zonder proxy faalt de aanroep gewoon met 401, dus het is
    # geen stille terugval op een andere route.
    PLACEHOLDER = "placeholder-credential-proxy"

    def __init__(self, token: str | None = None, repo: str = ""):
        self.token = token or os.environ.get("ORCH_GITHUB_TOKEN", "") or self.PLACEHOLDER
        self.repo = repo

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict | list:
        if not self.token:
            raise GitHubError("ORCH_GITHUB_TOKEN ontbreekt")
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(f"{API}{path}", data=data, method=method)
        request.add_header("Authorization", f"Bearer {self.token}")
        request.add_header("Accept", "application/vnd.github+json")
        request.add_header("Content-Type", "application/json")
        request.add_header("User-Agent", "padelmq-orchestrator")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read().decode()
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            raise GitHubError(f"{method} {path} gaf {exc.code}: {exc.read().decode()[:400]}") from exc

    def whoami(self) -> str:
        """De login waarmee we bij GitHub binnenkomen.

        Bewijst dat de token geldig is, wat 'de variabele is gezet' niet doet.
        Alleen de login komt terug; de token blijft binnen dit object.
        """
        rij = self._request("GET", "/user")
        return str(rij.get("login") or "(onbekende login)")  # type: ignore[union-attr]

    def _alle_paginas(self, path: str) -> list:
        """Elke pagina, niet alleen de eerste.

        GitHub geeft standaard 30 items per pagina. Wie dat vergeet krijgt een
        blinde vlek die pas ontstaat als een gesprek lang genoeg wordt -- en dan
        precies bij de issues waar het meeste gebeurd is. Op issue #4 van
        padelmq-ai-product-engine stond de beslissing van de eigenaar op plek
        32; de orkestrator zag hem nooit en wachtte op iets dat er al was.

        We vragen 100 per pagina en lopen door tot een pagina niet vol zit.
        """
        uit: list = []
        scheiding = "&" if "?" in path else "?"
        for pagina in range(1, 51):  # 5000 items; daarna is er iets anders mis
            rijen = self._request(
                "GET", f"{path}{scheiding}per_page=100&page={pagina}"
            )
            if not isinstance(rijen, list) or not rijen:
                break
            uit.extend(rijen)
            if len(rijen) < 100:
                break
        return uit

    def create_issue(self, repo: str, title: str, body: str, labels: list[str]) -> int:
        result = self._request(
            "POST", f"/repos/{repo}/issues",
            {"title": title, "body": body, "labels": labels},
        )
        return int(result["number"])

    def update_issue_body(self, repo: str, number: int, body: str) -> None:
        """Vervangt de tekst van een issue. Voor het statusbord: bijwerken in
        plaats van een reactie plaatsen, anders is het binnen een dag onleesbaar."""
        self._request("PATCH", f"/repos/{repo}/issues/{number}", {"body": body})

    def comment(self, repo: str, number: int, body: str) -> int:
        """Plaatst een reactie en geeft het id ervan terug.

        Dat id is nodig omdat de orkestrator met de token van de eigenaar
        schrijft: zijn eigen reactie komt bij de volgende ronde terug als een
        reactie van de eigenaar, en zou dan als antwoord op zijn eigen vraag
        gelezen worden. Wie zijn eigen vraag beantwoordt, vraagt niets.
        """
        uit = self._request("POST", f"/repos/{repo}/issues/{number}/comments",
                            {"body": body})
        return int(uit.get("id") or 0)  # type: ignore[union-attr]

    def close_issue(self, repo: str, number: int) -> None:
        self._request("PATCH", f"/repos/{repo}/issues/{number}", {"state": "closed"})

    def owner_comments(self, repo: str, number: int) -> list[dict]:
        """Reacties van de repo-eigenaar; alleen die tellen als antwoord."""
        owner = repo.split("/", 1)[0].lower()
        comments = self._alle_paginas(f"/repos/{repo}/issues/{number}/comments")
        out = []
        for comment in comments:  # type: ignore[union-attr]
            author = (comment.get("user") or {}).get("login", "").lower()
            association = (comment.get("author_association") or "").upper()
            if author == owner or association in {"OWNER", "MEMBER"}:
                out.append(comment)
        return out

    def issues_with_label(self, repo: str, label: str) -> list[dict]:
        """Open issues met dit label, oudste eerst.

        Alleen issues: de GitHub-API geeft pull requests terug in dezelfde lijst,
        en een PR is geen opdracht.
        """
        rijen = self._alle_paginas(
            f"/repos/{repo}/issues?state=open&labels={label}&sort=created&direction=asc"
        )
        return [r for r in rijen if "pull_request" not in r]  # type: ignore[union-attr]

    def add_labels(self, repo: str, number: int, labels: list[str]) -> None:
        self._request("POST", f"/repos/{repo}/issues/{number}/labels", {"labels": labels})

    def remove_label(self, repo: str, number: int, label: str) -> None:
        """Haalt één label weg. Een label dat er niet staat is geen fout."""
        from urllib.parse import quote

        try:
            self._request("DELETE", f"/repos/{repo}/issues/{number}/labels/{quote(label)}")
        except GitHubError as exc:
            if "gaf 404" not in str(exc):
                raise

    def issue_author_is_owner(self, repo: str, issue: dict) -> bool:
        """Alleen de eigenaar mag werk opdragen.

        Zonder deze controle kan iedereen die een issue mag openen de
        orkestrator laten draaien op zijn rekening.
        """
        owner = repo.split("/", 1)[0].lower()
        auteur = ((issue.get("user") or {}).get("login") or "").lower()
        verband = (issue.get("author_association") or "").upper()
        return auteur == owner or verband in {"OWNER", "MEMBER"}

    def create_pull_request(
        self, repo: str, title: str, body: str, head: str, base: str
    ) -> dict:
        return self._request(  # type: ignore[return-value]
            "POST", f"/repos/{repo}/pulls",
            {"title": title, "body": body, "head": head, "base": base},
        )


class GitHubNotifier:
    name = "github"

    def __init__(self, client: GitHubClient | None = None, repo: str = ""):
        self.client = client or GitHubClient()
        self.repo = repo

    def send(self, message: Message) -> str | None:
        repo = self.repo or self.client.repo
        if not repo:
            raise GitHubError("geen github_repo ingesteld voor dit project")
        number = self.client.create_issue(
            repo, message.subject, message.body, message.labels or ["orch:block"]
        )
        return str(number)
