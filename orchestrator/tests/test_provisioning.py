"""Waarom deze test bestaat.

Na de eerste Railway-fix bouwde en startte de container wel, maar meldde
Railway de service als "Completed" in plaats van "Online". Oorzaak: het volume
was vers, dus stonden er nul projecten, dus sloot serve netjes af met code 0.
Een afsluitcode 0 leest als succes. Dat is dezelfde soort fout als de eerste:
een groen ogende eindtoestand waarin niets draait.

Twee dingen liggen hier vast: nul projecten is luidruchtig fout, en projecten
kunnen zonder shell op een vers volume komen.
"""

import json
import unittest

from tests.base import TempCase

from orchestrator import projects as projects_mod
from orchestrator.opstart import controleer_projecten
from orchestrator.provision import VARIABELE, ProvisionError, provision


class GeenProjecten(unittest.TestCase):
    def test_nul_projecten_is_fout_geen_rust(self):
        c = controleer_projecten([], "/data/orchestrator/projects")
        self.assertFalse(c.ok)
        self.assertIn("geen enkel project", c.detail)
        self.assertIn("ORCH_PROJECTS", c.detail)

    def test_met_projecten_is_het_goed_en_noemt_ze(self):
        c = controleer_projecten(["a", "b"], "/x")
        self.assertTrue(c.ok)
        self.assertIn("a, b", c.detail)

    def test_serve_sluit_niet_stil_af_zonder_projecten(self):
        """De kern van de fout: exit 0 laat Railway 'Completed' tonen."""
        import inspect

        from orchestrator import cli

        bron = inspect.getsource(cli.cmd_serve)
        kop = bron[:bron.index("def herstel")]
        self.assertIn("return 1", kop,
                      "serve hoort met een foutcode te stoppen als er geen "
                      "projecten zijn; met 0 lijkt het geslaagd")


class Provisioning(TempCase):
    def _ruw(self, *projecten):
        return json.dumps(list(projecten))

    def test_maakt_een_ontbrekend_project_aan(self):
        uitkomst = provision(
            self.settings,
            self._ruw({"slug": "teller", "github_repo": "PadeLMQ/padelmq-teller"}),
            repos_dir="/data/repos",
        )
        self.assertEqual(uitkomst.aangemaakt, ["teller"])
        project = projects_mod.load(self.settings, "teller")
        self.assertEqual(project.github_repo, "PadeLMQ/padelmq-teller")
        self.assertEqual(project.repo, "/data/repos/teller",
                         "zonder expliciet pad hoort de kloon op het volume")

    def test_bestaand_project_wordt_nooit_overschreven(self):
        """Anders draait een oude variabele later stilletjes wijzigingen terug."""
        projects_mod.add(self.settings, "teller", "/eigen/pad",
                         checks={"tests": "pytest"}, github_repo="PadeLMQ/oud")
        uitkomst = provision(
            self.settings,
            self._ruw({"slug": "teller", "github_repo": "PadeLMQ/nieuw",
                       "checks": {"tests": "iets anders"}}),
            repos_dir="/data/repos",
        )
        self.assertEqual(uitkomst.aangemaakt, [])
        self.assertEqual(uitkomst.bestond, ["teller"])
        project = projects_mod.load(self.settings, "teller")
        self.assertEqual(project.github_repo, "PadeLMQ/oud")
        self.assertEqual(project.checks, {"tests": "pytest"})

    def test_checks_komen_mee(self):
        provision(self.settings,
                  self._ruw({"slug": "p", "checks": {"tests": "npm test"}}),
                  repos_dir="/r")
        self.assertEqual(projects_mod.load(self.settings, "p").checks,
                         {"tests": "npm test"})

    def test_leeg_is_geen_fout_maar_levert_niets_op(self):
        self.assertEqual(provision(self.settings, "", repos_dir="/r").aangemaakt, [])
        self.assertEqual(provision(self.settings, "   ", repos_dir="/r").aangemaakt, [])

    def test_een_enkel_object_mag_ook(self):
        provision(self.settings, json.dumps({"slug": "p"}), repos_dir="/r")
        self.assertIn("p", projects_mod.list_projects(self.settings))

    def test_kapotte_json_zegt_waar_het_misgaat(self):
        """Een typefout in een Railway-variabele moet leesbaar falen, niet
        met een stacktrace waar niemand iets aan heeft."""
        with self.assertRaises(ProvisionError) as ctx:
            provision(self.settings, '[{"slug": "p",}]', repos_dir="/r")
        self.assertIn(VARIABELE, str(ctx.exception))

    def test_project_zonder_slug_wordt_niet_geraden(self):
        with self.assertRaises(ProvisionError) as ctx:
            provision(self.settings, self._ruw({"github_repo": "a/b"}), repos_dir="/r")
        self.assertIn("zonder 'slug'", str(ctx.exception))

    def test_zonder_pad_en_zonder_repos_map_wordt_niets_verzonnen(self):
        with self.assertRaises(ProvisionError) as ctx:
            provision(self.settings, self._ruw({"slug": "p"}), repos_dir="")
        self.assertIn("ORCH_REPOS", str(ctx.exception))

    def test_gevaarlijke_check_wordt_geweigerd(self):
        """De veiligheidspoort van 'project add' geldt ook hier; een
        omgevingsvariabele is geen achterdeur."""
        with self.assertRaises(Exception) as ctx:
            provision(self.settings,
                      self._ruw({"slug": "p", "checks": {"x": "rm -rf /"}}),
                      repos_dir="/r")
        self.assertNotIsInstance(ctx.exception, AssertionError)

    def test_start_script_zet_projecten_klaar_voor_de_controle(self):
        """Volgorde: eerst projecten aanmaken, dan pas controleren en draaien."""
        from pathlib import Path

        wortel = Path(__file__).resolve().parents[2]
        script = (wortel / "deploy" / "railway" / "start.sh").read_text()
        self.assertLess(script.index("project ensure"), script.index("cli startup"))
        self.assertLess(script.index("cli startup"), script.index("cli serve"))


if __name__ == "__main__":
    unittest.main()
