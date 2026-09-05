"""De gereedschapskist van de uitvoerder.

D-16 liet zien dat een tool verbieden niet betekent dat zijn beschrijving niet
wordt meegestuurd en betaald. --allowedTools regelt wat mag, --tools regelt wat
er geladen wordt. Deze tests bewaken beide, en het verschil ertussen.
"""

import inspect
import unittest

from orchestrator.adapters.claude import (
    BENODIGDE_TOOLS,
    ClaudeExecutor,
    ToolsetError,
    tool_names,
)


def _cmd(**kw) -> list[str]:
    return ClaudeExecutor("claude-opus-5", **kw)._command("PROMPT", None)


def _waarde(cmd: list[str], vlag: str) -> str:
    return cmd[cmd.index(vlag) + 1]


class G1_GeenMcp(unittest.TestCase):
    def test_mcp_configuratie_wordt_genegeerd(self):
        cmd = _cmd()
        self.assertIn("--strict-mcp-config", cmd)
        self.assertNotIn("--mcp-config", cmd)


class G2_AlleenNoodzakelijkeTools(unittest.TestCase):
    def test_tools_bevat_precies_de_benodigde_set(self):
        geladen = _waarde(_cmd(), "--tools").split(",")
        self.assertEqual(sorted(geladen), sorted(BENODIGDE_TOOLS))

    def test_geen_ongebruikt_gereedschap(self):
        """De 35 tools die de uitvoerder niet mag gebruiken, worden niet geladen."""
        geladen = _waarde(_cmd(), "--tools")
        for ongewenst in ("Agent", "Artifact", "Workflow", "CronCreate", "DesignSync",
                          "Monitor", "SendUserFile", "ShowOnboardingRolePicker",
                          "WebFetch", "WebSearch", "NotebookEdit", "Skill"):
            self.assertNotIn(ongewenst, geladen, f"{ongewenst} wordt onnodig geladen")

    def test_niet_leeg(self):
        """Een lege set zou de uitvoerder blind en stuur loos maken."""
        self.assertTrue(_waarde(_cmd(), "--tools").strip())


class G3_TweeVlaggenTweeFuncties(unittest.TestCase):
    """--allowedTools is de poort, --tools is de laadlijst. Allebei nodig."""

    def test_beide_vlaggen_staan_er(self):
        cmd = _cmd()
        self.assertIn("--allowedTools", cmd)
        self.assertIn("--tools", cmd)

    def test_ze_komen_uit_dezelfde_opgave(self):
        cmd = _cmd()
        self.assertEqual(
            sorted(tool_names(_waarde(cmd, "--allowedTools"))),
            sorted(_waarde(cmd, "--tools").split(",")),
            "de poort en de laadlijst lopen uiteen",
        )

    def test_patronen_blijven_in_de_poort_maar_niet_in_de_laadlijst(self):
        """'Bash(git *)' is een toegestaan patroon; --tools wil alleen 'Bash'."""
        spec = "Read,Edit,Write,Glob,Grep,Bash(git *)"
        cmd = _cmd(allowed_tools=spec)
        self.assertIn("git *", _waarde(cmd, "--allowedTools"))
        self.assertNotIn("(", _waarde(cmd, "--tools"))
        self.assertIn("Bash", _waarde(cmd, "--tools").split(","))


class G4_GeenStilleUitbreiding(unittest.TestCase):
    def test_een_ruimere_poort_verandert_de_laadlijst_mee(self):
        """Wie later een tool toevoegt, ziet dat hier terug in plaats van in de rekening."""
        cmd = _cmd(allowed_tools="Read,Edit,Write,Glob,Grep,Bash,WebFetch")
        self.assertIn("WebFetch", _waarde(cmd, "--tools").split(","))

    def test_de_standaard_blijft_de_kleine_set(self):
        self.assertEqual(len(_waarde(_cmd(), "--tools").split(",")), len(BENODIGDE_TOOLS))

    def test_default_wordt_niet_gebruikt(self):
        """'default' zou alle ingebouwde tools terugzetten."""
        self.assertNotEqual(_waarde(_cmd(), "--tools").strip().lower(), "default")


class G5_UitvoerderKanNogWerken(unittest.TestCase):
    def test_lezen_schrijven_zoeken_en_uitvoeren_blijven_beschikbaar(self):
        geladen = _waarde(_cmd(), "--tools").split(",")
        for nodig in ("Read", "Write", "Edit", "Glob", "Grep", "Bash"):
            self.assertIn(nodig, geladen, f"{nodig} ontbreekt; de uitvoerder is verlamd")


class G6_VerbodenActiesBlijvenGeblokkeerd(unittest.TestCase):
    def test_de_verificatiepoort_staat_los_van_de_toolset(self):
        """Het verbod op live acties zit in de uitvoerder zelf, niet in een vlag."""
        from orchestrator.verify import assert_safe_checks

        for cmd in ("npm run deploy", "npm run sync", "ENABLE_STOCK_WRITE=true npm run daily",
                    "curl https://x.myshopify.com/admin"):
            with self.subTest(cmd=cmd):
                with self.assertRaises(Exception):
                    assert_safe_checks({"check": cmd})

    def test_permissies_blijven_dichtstaan(self):
        cmd = _cmd()
        self.assertIn("--permission-prompts", cmd)
        self.assertEqual(_waarde(cmd, "--permission-prompts"), "none")
        self.assertNotIn("bypassPermissions", cmd)


class G7_GeenFallbackNaarDeVolledigeSet(unittest.TestCase):
    def test_de_uitvoerder_probeert_niet_opnieuw(self):
        """Een retry met ruimere tools zou het probleem oplossen door het duur te maken."""
        bron = inspect.getsource(ClaudeExecutor)
        for verdacht in ("retry", "opnieuw proberen", '"default"', "'default'"):
            self.assertNotIn(verdacht, bron, f"mogelijke terugval gevonden: {verdacht}")

    def test_execute_doet_precies_een_aanroep(self):
        bron = inspect.getsource(ClaudeExecutor.execute)
        self.assertEqual(bron.count("subprocess.run"), 1,
                         "er wordt meer dan één subproces gestart")


class G8_OntbrekendGereedschapFaaltDicht(unittest.TestCase):
    def test_te_kleine_set_wordt_geweigerd(self):
        with self.assertRaises(ToolsetError):
            ClaudeExecutor("m", allowed_tools="Read,Write")

    def test_de_melding_noemt_wat_ontbreekt(self):
        with self.assertRaises(ToolsetError) as ctx:
            ClaudeExecutor("m", allowed_tools="Read")
        tekst = str(ctx.exception)
        self.assertIn("Bash", tekst)
        self.assertIn("niet teruggevallen", tekst)

    def test_lege_set_wordt_geweigerd(self):
        with self.assertRaises(ToolsetError):
            ClaudeExecutor("m", allowed_tools="")


if __name__ == "__main__":
    unittest.main()
