"""Waarom deze test bestaat.

Railway meldde "Online / Active" terwijl er geen enkele orkestratorregel in de
log stond. De oorzaak was niet de code maar de plaats van de configuratie:
Railway leest railway.json uitsluitend in de wortel van de repository. Die van
ons stond in deploy/railway/ en werd genegeerd. Nixpacks zag vervolgens de
GitHub Pages-site in dezelfde repository (index.html + CNAME), concludeerde
"statische site" en startte Caddy. Groen lampje, geen orkestrator.

Zo'n fout is niet met de hand te bewaken: hij is onzichtbaar tot je hem nodig
hebt. Daarom staat hij hier vast.
"""

import json
import re
import unittest
from pathlib import Path

WORTEL = Path(__file__).resolve().parents[2]


class RailwayConfiguratie(unittest.TestCase):
    def setUp(self) -> None:
        self.pad = WORTEL / "railway.json"

    def test_config_staat_in_de_wortel(self):
        """Railway kijkt alleen in de wortel; elders is het bestand decoratie."""
        self.assertTrue(
            self.pad.exists(),
            "railway.json ontbreekt in de wortel van de repository; Railway "
            "valt dan terug op Nixpacks en start de statische site in plaats "
            "van de orkestrator",
        )

    def test_bouwt_met_de_dockerfile_die_bestaat(self):
        config = json.loads(self.pad.read_text())
        bouw = config.get("build", {})
        self.assertEqual(
            bouw.get("builder"), "DOCKERFILE",
            "zonder DOCKERFILE-builder raadt Nixpacks het projecttype, en in "
            "deze repository raadt het 'statische site'",
        )
        dockerfile = WORTEL / bouw.get("dockerfilePath", "")
        self.assertTrue(dockerfile.is_file(),
                        f"dockerfilePath wijst naar {dockerfile}, die bestaat niet")

    def test_startcommando_bestaat_en_wordt_gekopieerd(self):
        """Het startcommando moet in het image staan, niet alleen in de repo."""
        config = json.loads(self.pad.read_text())
        start = config["deploy"]["startCommand"]
        self.assertTrue(start.endswith("start.sh"), start)
        dockerfile = (WORTEL / config["build"]["dockerfilePath"]).read_text()
        self.assertIn("start.sh", dockerfile,
                      "de Dockerfile kopieert start.sh niet; het startcommando "
                      "zou dan in de container ontbreken")

    def test_dockerignore_sluit_niets_uit_dat_gekopieerd_wordt(self):
        """Een te ijverige .dockerignore levert een build die pas in de lucht faalt."""
        dockerfile = (WORTEL / "deploy" / "railway" / "Dockerfile").read_text()
        genegeerd = {
            regel.strip().lstrip("/")
            for regel in (WORTEL / ".dockerignore").read_text().splitlines()
            if regel.strip() and not regel.startswith("#")
        }
        gekopieerd = []
        for regel in dockerfile.splitlines():
            gevonden = re.match(r"\s*COPY\s+(.*)$", regel, re.I)
            if not gevonden:
                continue
            velden = [v for v in gevonden.group(1).split() if not v.startswith("--")]
            gekopieerd.extend(velden[:-1])  # laatste veld is het doel
        self.assertTrue(gekopieerd, "de Dockerfile kopieert niets; dat klopt niet")
        for bron in gekopieerd:
            top = bron.strip().split("/")[0]
            self.assertNotIn(
                top, genegeerd,
                f"de Dockerfile kopieert {bron}, maar .dockerignore sluit {top} uit",
            )
            self.assertTrue((WORTEL / bron).exists(),
                            f"de Dockerfile kopieert {bron}, die niet bestaat")

    def test_start_script_draait_de_opstartcontrole_en_serve(self):
        """De volgorde is het punt: eerst bewijzen dat het kan, dan pas draaien."""
        script = (WORTEL / "deploy" / "railway" / "start.sh").read_text()
        self.assertLess(script.index("cli startup"), script.index("cli serve"),
                        "de opstartcontrole hoort vóór serve te draaien")
        self.assertIn("exec python3 -m orchestrator.cli serve", script,
                      "serve hoort het procesbeeld over te nemen, anders krijgt "
                      "het proces geen signalen van Railway")

    def test_geen_geheimen_in_de_deploybestanden(self):
        """Wat in de repo staat is publiek; een sleutel hoort daar dus nooit.

        Verwijzen naar een geheim moet juist wel: "$ORCH_GITHUB_TOKEN" is de
        manier waarop de waarde buiten de repo blijft. We zoeken daarom naar
        ingetypte waarden in bekende sleutelvormen, niet naar het woord token.
        """
        vormen = re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}|\bgh[pousr]_[A-Za-z0-9]{16,}"
                            r"|\bshpat_[A-Za-z0-9]+|BEGIN [A-Z ]*PRIVATE KEY")
        for pad in self._deploybestanden():
            gevonden = vormen.search(pad.read_text(errors="ignore"))
            self.assertIsNone(gevonden, f"{pad.name} bevat een echte sleutelwaarde")

    def test_token_belandt_nooit_in_een_url_of_in_de_log(self):
        """Een token in een remote-URL lekt: die URL staat in .git/config en in
        elke foutmelding die git afdrukt. Vandaar het credential-bestand."""
        script = (WORTEL / "deploy" / "railway" / "start.sh").read_text()
        # Alleen regels die de waarde uitvouwen tellen; de naam noemen mag.
        uitvouw = re.compile(r"\$\{?ORCH_GITHUB_TOKEN")
        for regel in script.splitlines():
            kaal = regel.strip()
            if kaal.startswith("#") or not uitvouw.search(kaal):
                continue
            self.assertFalse(
                kaal.startswith("echo") or kaal.startswith("git remote"),
                f"deze regel zou de token kunnen tonen of in een URL zetten: {kaal}",
            )
        self.assertIn("chmod 600 /root/.git-credentials", script,
                      "het credential-bestand hoort alleen voor de eigenaar leesbaar te zijn")

    def _deploybestanden(self):
        paden = [p for p in sorted((WORTEL / "deploy" / "railway").glob("*")) if p.is_file()]
        return paden + [self.pad, WORTEL / ".dockerignore"]


if __name__ == "__main__":
    unittest.main()
