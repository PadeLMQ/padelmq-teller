"""Opdrachten aannemen via GitHub, zodat er geen mens meer tussen hoeft."""

import unittest

from orchestrator.intake import (
    AANGENOMENLABEL,
    TAAKLABEL,
    acceptatiecriteria,
    intake,
    spec_uit_body,
)

try:
    from tests.base import TempCase
except ImportError:  # pragma: no cover
    from base import TempCase


class FakeGitHub:
    def __init__(self, issues=None):
        self.issues = issues or []
        self.posted = []
        self.labels = []

    def issues_with_label(self, repo, label):
        return [i for i in self.issues
                if label in {l["name"] for l in i.get("labels", [])}]

    def add_labels(self, repo, number, labels):
        self.labels.append((number, labels))
        for i in self.issues:
            if i["number"] == number:
                i.setdefault("labels", []).extend({"name": l} for l in labels)

    def comment(self, repo, number, body):
        self.posted.append((number, body))

    def issue_author_is_owner(self, repo, issue):
        owner = repo.split("/", 1)[0].lower()
        auteur = ((issue.get("user") or {}).get("login") or "").lower()
        return auteur == owner or (issue.get("author_association") or "").upper() == "OWNER"


def _issue(nummer=1, titel="Doe iets", body="", auteur="eigenaar", labels=(TAAKLABEL,)):
    return {"number": nummer, "title": titel, "body": body,
            "user": {"login": auteur}, "author_association": "OWNER",
            "labels": [{"name": l} for l in labels]}


class Criteria(unittest.TestCase):
    def test_checklist(self):
        body = "Wat dan ook.\n\n- [ ] eerste eis\n- [x] tweede eis\n"
        self.assertEqual(acceptatiecriteria(body), ["eerste eis", "tweede eis"])

    def test_kop_zonder_checklist(self):
        body = "Uitleg.\n\n## Acceptatie\n- npm run test geeft exit 0\n- niets live\n"
        self.assertEqual(acceptatiecriteria(body),
                         ["npm run test geeft exit 0", "niets live"])

    def test_geen_criteria_is_leeg_en_niet_verzonnen(self):
        self.assertEqual(acceptatiecriteria("Gewoon even fixen graag."), [])
        self.assertEqual(acceptatiecriteria(""), [])

    def test_spec_bevat_de_criteria_niet(self):
        body = "De opdracht.\n\n- [ ] eerste eis\n"
        self.assertIn("De opdracht", spec_uit_body(body))
        self.assertNotIn("eerste eis", spec_uit_body(body))


class Aannemen(TempCase):
    def setUp(self):
        super().setUp()
        self.project = self.make_project("intake")
        self.project.github_repo = "eigenaar/intake"
        self.scope = self.db.scope("intake")

    def test_issue_wordt_een_taak(self):
        client = FakeGitHub([_issue(body="Doe dit.\n\n- [ ] het werkt\n")])
        acties = intake(scope=self.scope, project=self.project, client=client)

        taken = self.scope.tasks()
        self.assertEqual(len(taken), 1)
        self.assertEqual(taken[0]["title"], "Doe iets")
        self.assertIn("aangenomen", acties[0])
        self.assertEqual(client.labels, [(1, [AANGENOMENLABEL])])

    def test_zonder_criteria_wordt_geweigerd(self):
        """Anders zou de orkestrator zelf moeten bedenken wanneer het klaar is."""
        client = FakeGitHub([_issue(body="Gewoon even fixen.")])
        intake(scope=self.scope, project=self.project, client=client)

        self.assertEqual(self.scope.tasks(), [])
        self.assertIn("geen acceptatiecriteria", client.posted[0][1])
        self.assertEqual(client.labels, [], "een geweigerd issue is toch gemarkeerd")

    def test_alleen_de_eigenaar_mag_werk_opdragen(self):
        issue = _issue(auteur="iemandanders")
        issue["author_association"] = "NONE"
        issue["body"] = "- [ ] doe iets duurs\n"
        client = FakeGitHub([issue])
        acties = intake(scope=self.scope, project=self.project, client=client)

        self.assertEqual(self.scope.tasks(), [])
        self.assertIn("niet van de eigenaar", acties[0])

    def test_idempotent_bij_herstart(self):
        client = FakeGitHub([_issue(body="- [ ] het werkt\n")])
        intake(scope=self.scope, project=self.project, client=client)
        intake(scope=self.scope, project=self.project, client=client)

        self.assertEqual(len(self.scope.tasks()), 1,
                         "dezelfde opdracht is twee keer aangenomen")

    def test_issue_zonder_taaklabel_blijft_liggen(self):
        client = FakeGitHub([_issue(labels=("bug",), body="- [ ] iets\n")])
        intake(scope=self.scope, project=self.project, client=client)
        self.assertEqual(self.scope.tasks(), [])

    def test_zonder_github_repo_gebeurt_er_niets(self):
        self.project.github_repo = ""
        self.assertEqual(
            intake(scope=self.scope, project=self.project, client=FakeGitHub()), [])


if __name__ == "__main__":
    unittest.main()
