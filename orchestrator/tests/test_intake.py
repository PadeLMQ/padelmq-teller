"""Opdrachten aannemen via GitHub, zodat er geen mens meer tussen hoeft."""

import unittest

from orchestrator.intake import (
    AANGENOMENLABEL,
    CRITERIALABEL,
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
        self.verwijderd = []

    def issues_with_label(self, repo, label):
        return [i for i in self.issues
                if label in {l["name"] for l in i.get("labels", [])}]

    def add_labels(self, repo, number, labels):
        self.labels.append((number, labels))
        for i in self.issues:
            if i["number"] == number:
                i.setdefault("labels", []).extend({"name": l} for l in labels)

    def remove_label(self, repo, number, label):
        self.verwijderd.append((number, label))
        for i in self.issues:
            if i["number"] == number:
                i["labels"] = [l for l in i.get("labels", []) if l["name"] != label]

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
        # Het krijgt wel een merkteken 'geen criteria', anders zou dezelfde
        # melding elke ronde terugkomen. Maar aangenomen is het niet.
        gezet = {l for _, labels in client.labels for l in labels}
        self.assertNotIn(AANGENOMENLABEL, gezet,
                         "een geweigerd issue is toch als aangenomen gemarkeerd")
        self.assertEqual(gezet, {CRITERIALABEL})

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


class GeenCriteriaBlijftNietDoorzeuren(TempCase):
    """Een lus die 24/7 draait maakt van een kleine onvolkomenheid vanzelf een
    grote: zonder merkteken kwam hetzelfde commentaar elke ronde terug."""

    def _scope(self):
        self.db.ensure_project("p")
        return self.db.scope("p")

    def _project(self):
        import types
        return types.SimpleNamespace(slug="p", github_repo="eigenaar/repo")

    def test_er_wordt_maar_een_keer_gemeld(self):
        issue = _issue(body="Geen enkel criterium hier.")
        client = FakeGitHub([issue])
        scope, project = self._scope(), self._project()

        intake(scope=scope, project=project, client=client)
        self.assertEqual(len(client.posted), 1)
        self.assertIn(CRITERIALABEL, {l["name"] for l in issue["labels"]})

        for _ in range(5):
            acties = intake(scope=scope, project=project, client=client)
            self.assertEqual(acties, [], "een al gemelde opdracht hoort stil te blijven")
        self.assertEqual(len(client.posted), 1,
                         "vijf extra rondes hebben opnieuw commentaar geplaatst")

    def test_criteria_erbij_zetten_haalt_het_merkteken_weg_en_neemt_aan(self):
        """Het issue moet zichzelf kunnen herstellen zonder tussenkomst."""
        issue = _issue(body="Nog niets.")
        client = FakeGitHub([issue])
        scope, project = self._scope(), self._project()
        intake(scope=scope, project=project, client=client)

        issue["body"] = "Nu wel.\n\n- [ ] npm run test geeft exit 0\n"
        acties = intake(scope=scope, project=project, client=client)

        self.assertTrue(any("aangenomen" in a for a in acties), acties)
        self.assertIn((1, CRITERIALABEL), client.verwijderd)
        self.assertIn(AANGENOMENLABEL, {l["name"] for l in issue["labels"]})
        self.assertNotIn(CRITERIALABEL, {l["name"] for l in issue["labels"]})

    def test_geweigerde_opdracht_maakt_geen_taak_aan(self):
        """Belangrijk voor de kosten: weigeren mag nooit werk starten."""
        client = FakeGitHub([_issue(body="niets")])
        scope = self._scope()
        intake(scope=scope, project=self._project(), client=client)
        self.assertEqual(scope.tasks(), [])
