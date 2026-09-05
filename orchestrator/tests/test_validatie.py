"""De reviewer-validatie stopt bij afwijkingen in plaats van stil terug te vallen."""

import unittest

from orchestrator.validate_reviewer import validate_online


class _Usage:
    input_tokens = 12
    output_tokens = 4


class GoedeClient:
    class responses:
        @staticmethod
        def create(**kwargs):
            GoedeClient.laatste = kwargs
            obj = type("R", (), {})()
            obj.output_text = '{"ok": true}'
            obj.id = "resp_1"
            obj.usage = _Usage()
            return obj


class WeigertParameter:
    class responses:
        @staticmethod
        def create(**kwargs):
            raise TypeError("create() got an unexpected keyword argument 'text'")


class GeenTokentelling:
    class responses:
        @staticmethod
        def create(**kwargs):
            obj = type("R", (), {})()
            obj.output_text = '{"ok": true}'
            obj.id = "resp_1"
            obj.usage = None
            return obj


class OngeldigeJson:
    class responses:
        @staticmethod
        def create(**kwargs):
            obj = type("R", (), {})()
            obj.output_text = "sorry, geen json"
            obj.id = "resp_1"
            obj.usage = _Usage()
            return obj


class Validatie(unittest.TestCase):
    def test_goede_vorm_wordt_goedgekeurd(self):
        report = validate_online("goedkoop-model", client=GoedeClient())
        self.assertFalse(report.failed, report.render())
        self.assertIn("tokentelling", report.render())

    def test_de_aanroep_gebruikt_hetzelfde_codepad_als_productie(self):
        validate_online("goedkoop-model", client=GoedeClient())
        verstuurd = GoedeClient.laatste
        for parameter in ("model", "input", "previous_response_id", "text"):
            self.assertIn(parameter, verstuurd)
        self.assertEqual(verstuurd["text"]["format"]["type"], "json_schema")
        self.assertTrue(verstuurd["text"]["format"]["strict"])

    def test_geweigerde_parameter_leidt_tot_stoppen(self):
        report = validate_online("goedkoop-model", client=WeigertParameter())
        self.assertTrue(report.failed)
        self.assertIn("corrigeer adapters/reviewer.py", report.render().lower())
        self.assertIn("val niet terug", report.render().lower())

    def test_ontbrekende_tokentelling_is_een_fout(self):
        report = validate_online("goedkoop-model", client=GeenTokentelling())
        self.assertTrue(report.failed)
        self.assertIn("kostenbewaking", report.render())

    def test_ongeldige_json_is_een_fout(self):
        report = validate_online("goedkoop-model", client=OngeldigeJson())
        self.assertTrue(report.failed)
