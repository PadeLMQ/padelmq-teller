"""De toestandsmachine voor één taak.

Volgorde: baseline → beantwoorden → uitvoeren → verifiëren → beoordelen.
Harde verificatie is de motor; de reviewer komt er nooit voor en kan haar
uitslag niet wijzigen.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .adapters import Executor, ExecutionResult, Reviewer, ReviewResult
from .adapters.claude import assumptions_without_source
from .adapters.reviewer import validate_verdict
from .config import Settings
from .cost import BudgetExceeded, CostGuard, Estimate, InconsistentUsage
from .db import ProjectScope
from .git import GitAdapter, GitError, run_git
from .guards import NoProgressDetector, detect_invented_values
from .models import (
    Question, TaskStatus, Triage, TriageResult, VerificationResult, Verdict,
)
from .notify import Message, Notifier
from .projects import Project
from .redact import redact_diff, redact_text
from .report import pr_body
from .triage import TriageContext, TriageEngine
from .verify import VerifyAdapter


class Paused(RuntimeError):
    pass


@dataclass
class RunOutcome:
    status: TaskStatus
    detail: str = ""
    questions: list[int] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.questions is None:
            self.questions = []


class Runner:
    def __init__(
        self,
        *,
        settings: Settings,
        project: Project,
        scope: ProjectScope,
        executor: Executor,
        reviewer: Reviewer | None,
        verifier: VerifyAdapter,
        git: GitAdapter,
        notifier: Notifier,
        cost: CostGuard,
        github=None,
    ):
        self.settings = settings
        self.project = project
        self.scope = scope
        self.executor = executor
        self.reviewer = reviewer
        self.verifier = verifier
        self.git = git
        self.notifier = notifier
        self.cost = cost
        self.github = github
        self.no_progress = NoProgressDetector()
        self._auto_answers: list[Question] = []

    # -- hulpjes ---------------------------------------------------------
    def _log(self, kind: str, task_id: int | None = None, **payload) -> None:
        self.scope.log(kind, payload, task_id=task_id)

    def _knowledge_context(self) -> str:
        return self.project.knowledge.as_prompt_context()

    def _log_context(self, task_id: int, fase: str, context: str, extra: dict) -> None:
        """Legt vast wat de reviewer precies te zien kreeg.

        Niet de volle tekst — wel welke kennisitems erin zaten, met hun status,
        plus een hash en de omvang. Zo is achteraf exact na te gaan waarop een
        AUTO-antwoord gebaseerd kon zijn, zonder het logboek vol te schrijven.
        """
        items = self.project.knowledge.load()
        self._log(
            "reviewer-context",
            task_id=task_id,
            fase=fase,
            kennisitems=[
                {"id": i.item_id, "status": i.status.value, "bestand": i.file}
                for i in sorted(items.values(), key=lambda x: x.item_id)
            ],
            aantal_items=len(items),
            bevestigd=sum(1 for i in items.values() if i.citable),
            context_tekens=len(context),
            context_sha256=hashlib.sha256(context.encode("utf-8")).hexdigest(),
            **extra,
        )

    def _triage_engine(self, task_id: int, verification: VerificationResult | None) -> TriageEngine:
        return TriageEngine(
            TriageContext(
                knowledge=self.project.knowledge,
                repo_root=self.project.repo_root,
                verification=verification,
                has_independent_work=self.scope.has_independent_work(excluding_task_id=task_id),
            )
        )

    def _park_or_block(self, task_id: int, question: Question, outcome: Triage, reason: str) -> int:
        question_id = self.scope.add_question(
            text=question.text,
            outcome=outcome.value,
            fingerprint=question.fingerprint(),
            why_blocking=question.why_blocking or reason,
            options=question.options,
            proposed=question.proposed_default or question.proposed_answer,
            category=question.category,
            task_id=task_id,
        )
        self.scope.set_task(
            task_id,
            status=(TaskStatus.PARKED if outcome is Triage.PARK else TaskStatus.BLOCKED).value,
            blocked_by_question=question_id,
        )
        self._log(
            "vraag", task_id=task_id, outcome=outcome.value,
            question=question.text, reason=reason, question_id=question_id,
        )
        if outcome is Triage.BLOCK:
            self._notify_block(task_id, question, reason, question_id)
        return question_id

    def _notify_block(self, task_id: int, question: Question, reason: str,
                      question_id: int) -> None:
        """Meldt een BLOCK, precies één keer per vraag.

        Idempotent: heeft deze vraag al een issue, dan wordt er niets nieuws
        aangemaakt. Zonder die controle levert elke herstart of nieuwe poging op
        dezelfde blokkade een extra issue op, en verdrinkt het echte verzoek in
        duplicaten.
        """
        bestaand = self.scope.question(question_id)
        if bestaand is not None and bestaand["issue_number"]:
            self._log("blokmelding-overgeslagen", task_id=task_id,
                      question_id=question_id, issue=int(bestaand["issue_number"]),
                      detail="deze vraag heeft al een issue")
            return

        task = self.scope.task(task_id)
        title = task["title"] if task else f"taak {task_id}"
        others = [t for t in self.scope.tasks(status="queued") if t["id"] != task_id]
        opties = question.options or []
        genummerd = "\n".join(f"{i + 1}. {o}" for i, o in enumerate(opties))

        body = "\n".join([
            "| | |",
            "|---|---|",
            f"| project | `{self.project.slug}` |",
            f"| taak | #{task_id} — {title} |",
            f"| vraag | #{question_id} |",
            "",
            "## De beslissing die nodig is",
            question.text,
            "",
            "## Waarom dit niet automatisch beantwoord kon worden",
            reason,
            "",
            "## Opties",
            genummerd or "_geen opties opgegeven; antwoord in je eigen woorden_",
            "",
            "## Voorstel van de orkestrator",
            (question.proposed_default or question.proposed_answer
             or "_geen. Er is geen bevestigde bron om iets voor te stellen._"),
            "",
            "## Wat ondertussen wel doorgaat",
            ("\n".join(f"- {t['title']}" for t in others)
             or "_niets; dit project wacht volledig op deze beslissing_"),
            "",
            "---",
            "**Antwoord gewoon in dit issue.** Je mag een optienummer noemen, een optie "
            "overnemen, of het in je eigen woorden zeggen. De orkestrator koppelt eerst "
            "terug hoe hij je antwoord gelezen heeft en legt het pas vast als je "
            "bevestigt. Bij twijfel vraagt hij één keer om verduidelijking en raadt "
            "daarna niet alsnog.",
            "",
            "_Generated by [Claude Code](https://claude.ai/code)_",
        ])

        try:
            reference = self.notifier.send(
                Message(
                    subject=f"[{self.project.slug}] Beslissing nodig: {question.text[:60]}",
                    body=redact_text(body, self.project.redact_patterns),
                    project=self.project.slug,
                    urgent=True,
                    labels=["orch:block"],
                )
            )
        except Exception as exc:  # noqa: BLE001 - melden mag de run niet slopen
            self._log("blokmelding-mislukt", task_id=task_id,
                      question_id=question_id, detail=f"{type(exc).__name__}: {exc}")
            return

        if reference and str(reference).isdigit():
            self.scope.set_question(question_id, issue_number=int(reference))
            self._log("blokmelding", task_id=task_id, question_id=question_id,
                      issue=int(reference))

    def _charge(self, result_usage, *, phase: str, role: str, task_id: int, run_id: int) -> None:
        if not result_usage:
            return
        estimate = Estimate(
            model=result_usage.model,
            tokens_in=result_usage.tokens_in,
            tokens_out=result_usage.tokens_out,
            cached_in=result_usage.cached_in,
            reported_cost=getattr(result_usage, "cost_usd", None),
        )
        try:
            self.cost.record(
                self.scope, estimate, phase=phase, role=role, task_id=task_id, run_id=run_id
            )
        except (KeyError, InconsistentUsage) as exc:
            # De aanroep is al gedaan en het geld is al uit. Een probleem met de
            # boekhouding mag de run dan niet alsnog slopen: luid vastleggen en
            # doorgaan, zodat het in het rapport opvalt in plaats van in een
            # traceback.
            self._log(
                "kosten-onbekend", task_id=task_id, detail=str(exc),
                model=estimate.model, tokens_in=estimate.tokens_in,
                tokens_out=estimate.tokens_out, cached_in=estimate.cached_in,
            )

    def _preflight(self, model: str, task_id: int, run_id: int, tokens_in: int, tokens_out: int) -> None:
        """De rem zit vóór de aanroep, niet erna."""
        self.cost.check(
            self.scope,
            Estimate(model=model, tokens_in=tokens_in, tokens_out=tokens_out),
            task_id=task_id,
            run_id=run_id,
        )

    # -- de lus ----------------------------------------------------------
    def run_task(self, task_id: int) -> RunOutcome:
        if self.settings.paused():
            raise Paused(f"noodstop actief ({self.settings.stop_file})")

        task = self.scope.task(task_id)
        if task is None:
            raise ValueError(f"taak {task_id} bestaat niet in project {self.scope.slug}")
        acceptance = json.loads(task["acceptance"] or "[]")
        if not acceptance:
            self.scope.set_task(task_id, status=TaskStatus.BLOCKED.value)
            self._log("geweigerd", task_id=task_id, reason="geen acceptatiecriteria")
            return RunOutcome(TaskStatus.BLOCKED, "taak zonder toetsbare acceptatiecriteria")

        run_id = self.scope.start_run(task_id, "task")
        self._auto_answers = []

        # 0 · baseline
        self.scope.set_task(task_id, status=TaskStatus.BASELINE.value)
        baseline = self.verifier.run(self.project.repo_root, self.project.checks)
        if self.project.checks and not baseline.ok:
            self.scope.set_task(task_id, status=TaskStatus.BLOCKED.value)
            self.scope.end_run(run_id, "baseline_rood")
            detail = "de repository staat al rood vóór er iets gewijzigd is: " + ", ".join(
                c.name for c in baseline.failed
            )
            self._log("baseline-rood", task_id=task_id, detail=detail)
            self.notifier.send(Message(
                subject="Baseline staat rood",
                body=detail + "\n\nEerst dit oplossen; anders is niet vast te stellen"
                     " of een wijziging iets breekt.",
                project=self.project.slug, urgent=True, labels=["orch:block"],
            ))
            return RunOutcome(TaskStatus.BLOCKED, detail)

        worktree = None
        try:
            branch = f"{self.project.branch_prefix}{task_id}"
            GitAdapter.guard_branch(branch, self.project.default_branch)
            worktree = self.git.create_worktree(
                self.project.repo_root, branch, self.project.default_branch
            )

            # 0b · is er nog bruikbaar werk van een eerdere poging?
            hervat = self._resume_phase(task_id, run_id, task, acceptance, worktree)
            if hervat is not None:
                self.scope.end_run(run_id, hervat.status.value)
                return hervat

            pending: list[Question] = []
            for _ in range(self.project.strength.max_implement_iterations):
                # 1 · beantwoorden
                answered, outcome = self._answer_phase(task_id, run_id, pending, baseline)
                if outcome is not None:
                    self.scope.end_run(run_id, outcome.status.value)
                    return outcome

                # 2 · uitvoeren
                self.scope.set_task(task_id, status=TaskStatus.IMPLEMENTING.value)
                prompt = self._build_prompt(task, acceptance, answered)
                if self._herhaalde_betaalde_context(task_id, prompt, worktree):
                    detail = (
                        "dezelfde opdracht is al eens naar de uitvoerder gestuurd bij"
                        " dezelfde toestand van de branch. Nog een keer betalen levert"
                        " hetzelfde antwoord op; er is nieuwe informatie of een"
                        " gewijzigde toestand nodig."
                    )
                    self.scope.set_task(task_id, status=TaskStatus.BLOCKED.value)
                    self._log("herhaalde-opdracht", task_id=task_id, detail=detail)
                    self.notifier.send(Message(
                        subject=f"Herhaalde opdracht tegengehouden: {task['title'][:50]}",
                        body=detail, project=self.project.slug, urgent=True,
                        labels=["orch:block"],
                    ))
                    self.scope.end_run(run_id, "herhaalde_opdracht")
                    return RunOutcome(TaskStatus.BLOCKED, detail)
                self._preflight(self.settings.executor_model, task_id, run_id, 20000, 8000)
                execution = self.executor.execute(
                    prompt=prompt, cwd=worktree.path, session_id=task["claude_session_id"]
                )
                self._charge(execution.usage, phase="implement", role="uitvoerder",
                             task_id=task_id, run_id=run_id)
                if execution.session_id:
                    self.scope.set_task(task_id, claude_session_id=execution.session_id)
                # De feedback is nu verwerkt; hem laten staan zou hem een ronde
                # later opnieuw als openstaand punt presenteren.
                if task["review_feedback"] if "review_feedback" in task.keys() else None:
                    self.scope.set_task(task_id, review_feedback=None)
                    task = self.scope.task(task_id)
                self._log(
                    "uitvoering", task_id=task_id,
                    samenvatting=execution.summary,
                    sessie=execution.session_id,
                    open_vragen=[q.text for q in execution.open_questions],
                    aannames=execution.assumptions_made,
                    alternatief=execution.alternative.proposal or None,
                    aanbeveling=execution.alternative.recommendation,
                    prompt_tekens=len(prompt),
                )

                # 2b · deterministische controles op wat er terugkomt
                blocked = self._guard_phase(task_id, execution, worktree, task, baseline)
                if blocked is not None:
                    self.scope.end_run(run_id, blocked.status.value)
                    return blocked

                if execution.open_questions:
                    pending = execution.open_questions
                    for question in pending:
                        question.task_id = task_id
                    continue

                # 3 · verifiëren
                self.scope.set_task(task_id, status=TaskStatus.VERIFYING.value)
                verification = self._verify(worktree, task_id=task_id)
                self._log(
                    "verificatie", task_id=task_id, ok=verification.ok,
                    checks=[
                        {"naam": c.name, "commando": c.command, "exitcode": c.exit_code,
                         "geslaagd": c.ok}
                        for c in verification.checks
                    ],
                    gefaald=[c.name for c in verification.failed],
                    poging=(task["iterations"] or 0) + 1,
                )
                if self.project.checks and not verification.ok:
                    signature = verification.signature()
                    if self.no_progress.stuck(signature) or self.scope.seen_signature(
                        task_id, signature
                    ):
                        detail = "tweemaal dezelfde falende uitslag; niet nog een poging"
                        self.scope.set_task(task_id, status=TaskStatus.BLOCKED.value)
                        self._log("geen-vooruitgang", task_id=task_id, signature=signature)
                        self.notifier.send(Message(
                            subject=f"Vastgelopen: {task['title'][:60]}",
                            body=detail + "\n\n" + signature,
                            project=self.project.slug, urgent=True, labels=["orch:block"],
                        ))
                        self.scope.end_run(run_id, "geen_vooruitgang")
                        return RunOutcome(TaskStatus.BLOCKED, detail)
                    self.scope.set_task(task_id, iterations=(task["iterations"] or 0) + 1)
                    task = self.scope.task(task_id)
                    pending = []
                    continue

                # 4 · beoordelen
                return self._review_phase(task_id, run_id, task, acceptance, worktree, verification)

            detail = "iteratielimiet bereikt zonder groene verificatie"
            self.scope.set_task(task_id, status=TaskStatus.BLOCKED.value)
            self.scope.end_run(run_id, "iteratielimiet")
            return RunOutcome(TaskStatus.BLOCKED, detail)

        except BudgetExceeded as exc:
            self.scope.set_task(task_id, status=TaskStatus.FAILED.value)
            self.scope.end_run(run_id, "budget")
            self._log("budget", task_id=task_id, detail=str(exc))
            self.notifier.send(Message(
                subject="Budget bereikt", body=str(exc),
                project=self.project.slug, urgent=True,
            ))
            return RunOutcome(TaskStatus.FAILED, str(exc))
        finally:
            if worktree is not None and self.project.checks is not None:
                pass  # worktree blijft staan zodat je de branch kunt bekijken

    # -- fases -----------------------------------------------------------
    def _answer_phase(
        self, task_id: int, run_id: int, pending: list[Question], baseline: VerificationResult
    ) -> tuple[list[Question], RunOutcome | None]:
        if not pending:
            return [], None
        self.scope.set_task(task_id, status=TaskStatus.ANSWERING.value)
        engine = self._triage_engine(task_id, baseline)

        candidates = pending
        if self.reviewer is not None and self.project.reviewer_enabled:
            task = self.scope.task(task_id)
            self._preflight(self.settings.reviewer_model, task_id, run_id, 12000, 3000)
            context = redact_text(self._knowledge_context(), self.project.redact_patterns)
            self._log_context(task_id, "beantwoorden", context, {
                "vragen": [q.text for q in pending],
            })
            result = self.reviewer.answer(
                questions=pending,
                context=context,
                previous_response_id=task["reviewer_response_id"] if task else None,
            )
            self._charge(result.usage, phase="answer", role="beantwoorder",
                         task_id=task_id, run_id=run_id)
            if result.response_id:
                self.scope.set_task(task_id, reviewer_response_id=result.response_id)
            if result.questions:
                candidates = result.questions

        answered: list[Question] = []
        # Eerst de hele batch beoordelen. Vroegtijdig teruggeven zou de vragen
        # die al betaald zijn weggooien; die komen dan een volgende ronde
        # opnieuw langs en kosten opnieuw geld.
        uitgesteld: list[tuple[Question, TriageResult]] = []
        for question in candidates:
            decision = engine.decide(question)
            self._log(
                "triage", task_id=task_id, outcome=decision.outcome.value,
                question=question.text, reason=decision.reason,
                bronnen=decision.resolved_citations,
                aangeboden_bronnen=[c.raw for c in question.citations],
                antwoord=decision.answer,
                categorie=question.category,
            )
            if decision.outcome is Triage.AUTO:
                question.proposed_answer = decision.answer
                answered.append(question)
                self._auto_answers.append(question)
            else:
                uitgesteld.append((question, decision))

        if not uitgesteld:
            return answered, None

        # Alles vastleggen; de zwaarste uitkomst bepaalt de taakstatus.
        for question, decision in uitgesteld:
            self._park_or_block(task_id, question, decision.outcome, decision.reason)
        blokkerend = next(
            ((q, d) for q, d in uitgesteld if d.outcome is Triage.BLOCK), None
        )
        question, decision = blokkerend or uitgesteld[0]
        status = TaskStatus.BLOCKED if blokkerend else TaskStatus.PARKED
        self.scope.set_task(task_id, status=status.value)
        toelichting = decision.reason
        if len(uitgesteld) > 1:
            toelichting += f" (en {len(uitgesteld) - 1} andere vraag/vragen uit dezelfde ronde)"
        return answered, RunOutcome(status, toelichting)

    def _guard_phase(
        self, task_id: int, execution: ExecutionResult, worktree, task, baseline
    ) -> RunOutcome | None:
        engine = self._triage_engine(task_id, baseline)

        for assumption in assumptions_without_source(execution.assumptions_made):
            question = Question(
                text=f"Klopt deze aanname? {assumption}",
                why_blocking="de uitvoerder nam dit aan zonder bron",
                category="aanname",
                task_id=task_id,
            )
            decision = engine.decide(question)
            self._park_or_block(task_id, question, decision.outcome, decision.reason)
            return RunOutcome(
                TaskStatus.PARKED if decision.outcome is Triage.PARK else TaskStatus.BLOCKED,
                f"aanname zonder bron: {assumption}",
            )

        diff = worktree.uncommitted_diff()
        known = "\n".join([
            self._knowledge_context(),
            task["spec"] or "",
            task["acceptance"] or "",
        ])
        for finding in detect_invented_values(diff, known):
            question = Question(
                text=(
                    f"Waar komt de waarde {finding.value} vandaan in "
                    f"{finding.file}:{finding.line_no} ({finding.reason})?"
                ),
                why_blocking="nieuwe harde waarde die nergens op terug te voeren is",
                options=[finding.line],
                category="geld" if finding.reason in ("bedrag", "percentage") else "waarde",
                task_id=task_id,
            )
            decision = engine.decide(question)
            self._park_or_block(task_id, question, decision.outcome, decision.reason)
            return RunOutcome(
                TaskStatus.PARKED if decision.outcome is Triage.PARK else TaskStatus.BLOCKED,
                f"verzonnen waarde {finding.value} in {finding.file}",
            )
        return None

    def _herhaalde_betaalde_context(self, task_id: int, prompt: str, worktree) -> bool:
        """Is deze exacte betaalde opdracht al eens verstuurd?

        Dezelfde prompt bij dezelfde toestand van de werkmap levert hetzelfde
        antwoord op. Nog een keer versturen kost geld en brengt niets: dat is
        precies het rondje dat in B7 $0,30 kostte.

        De handtekening dekt de prompt EN de inhoud van de branch, zodat een
        gewijzigde toestand wel een nieuwe poging rechtvaardigt.
        """
        kop = run_git(worktree.path, "rev-parse", "HEAD", check=False).strip()
        vuil = run_git(worktree.path, "status", "--porcelain", check=False)
        ruw = f"uitvoerder\n{prompt}\n{kop}\n{vuil}"
        handtekening = "impl:" + hashlib.sha256(ruw.encode()).hexdigest()
        return self.scope.seen_signature(task_id, handtekening)

    def _verify(self, worktree, *, task_id: int):
        """Draait de verificatie en ruimt op wat de checks zelf veranderd hebben.

        Een build schrijft gegenereerde bestanden terug in de werkmap. Die
        wijziging hoort niet bij de taak, maar belandt wel in de diff die
        beoordeeld en vastgelegd wordt -- de beoordelaar merkte dat terecht op
        als ongerelateerde wijziging. We noteren dus wat er vooraf al openstond
        en zetten daarna alleen terug wat er tijdens de verificatie bij kwam.
        """
        voor = self._gewijzigde_bestanden(worktree)
        verification = self.verifier.run(worktree.path, self.project.checks)
        erbij = sorted(self._gewijzigde_bestanden(worktree) - voor)
        if not erbij:
            return verification

        # Alleen bekende artefacten terugzetten. Een check die iets anders
        # wijzigt is een verrassing: die melden we, maar we gooien hem niet weg,
        # want dan zou een brede opruiming echt werk kunnen wissen.
        bekend = set(self.project.verification_artifacts)
        opgeruimd = [p for p in erbij if p in bekend]
        onbekend = [p for p in erbij if p not in bekend]
        for pad in opgeruimd:
            run_git(worktree.path, "checkout", "--", pad, check=False)
        self._log("verificatie-rommel", task_id=task_id,
                  opgeruimd=opgeruimd, onbekend=onbekend,
                  detail=("bekende verificatie-artefacten teruggezet; "
                          "onbekende wijzigingen blijven staan en gaan mee in de diff"))
        return verification

    @staticmethod
    def _gewijzigde_bestanden(worktree) -> set[str]:
        """Gevolgde bestanden met een wijziging. Nieuwe bestanden tellen niet mee."""
        uit = run_git(worktree.path, "status", "--porcelain", check=False)
        namen = set()
        for regel in uit.splitlines():
            if len(regel) > 3 and not regel.startswith("??"):
                namen.add(regel[3:].strip())
        return namen

    def _resume_phase(self, task_id: int, run_id: int, task, acceptance: list[str],
                      worktree) -> RunOutcome | None:
        """Kijkt of het werk van een eerdere poging nog voldoet.

        Zonder deze controle roept de lus de uitvoerder onvoorwaardelijk aan en
        betaal je opnieuw voor werk dat er al staat. Dat is niet alleen duur:
        na een beantwoorde BLOCK-vraag is het bestaande werk juist meestal nog
        goed, want de vraag ging over of het klopte, niet over of het bestond.

        De harde verificatie beslist, niet een inschatting. Is de uitslag groen,
        dan gaat het werk door naar de beoordeling. Is ze rood, dan valt de lus
        terug op een gewone implementatieronde.

        Geeft None terug als er niets te hervatten valt.
        """
        base = self.project.default_branch
        aantal = run_git(worktree.path, "rev-list", "--count", f"{base}..HEAD",
                         check=False).strip()
        if not aantal.isdigit() or int(aantal) == 0:
            return None

        self.scope.set_task(task_id, status=TaskStatus.VERIFYING.value)
        verification = self._verify(worktree, task_id=task_id)
        self._log(
            "hervatting", task_id=task_id, commits=int(aantal), ok=verification.ok,
            checks=[
                {"naam": c.name, "commando": c.command, "exitcode": c.exit_code,
                 "geslaagd": c.ok}
                for c in verification.checks
            ],
            gefaald=[c.name for c in verification.failed],
            besluit=("bestaand werk hergebruikt" if verification.ok
                     else "bestaand werk voldoet niet; opnieuw implementeren"),
        )
        # Exitcode 127 is "command not found": de check kon niet draaien. Dat zegt
        # niets over het werk, alleen over de omgeving -- een verse worktree
        # zonder geinstalleerde afhankelijkheden, bijvoorbeeld. Dat verschil
        # bepaalt of er betaald wordt voor een nieuwe implementatieronde, dus het
        # mag niet op een gok berusten: onuitvoerbaar is niet hetzelfde als rood.
        onuitvoerbaar = [c.name for c in verification.checks if c.exit_code == 127]
        if onuitvoerbaar:
            detail = (
                "de verificatie kon niet draaien in de worktree ("
                + ", ".join(onuitvoerbaar)
                + " gaven exitcode 127, commando niet gevonden). Zonder werkende"
                " verificatie is niet vast te stellen of het bestaande werk"
                " voldoet, en dan wordt er niet opnieuw geimplementeerd."
            )
            self.scope.set_task(task_id, status=TaskStatus.BLOCKED.value)
            self._log("verificatie-onuitvoerbaar", task_id=task_id,
                      checks=onuitvoerbaar, detail=detail)
            self.notifier.send(Message(
                subject="Verificatie kon niet draaien",
                body=detail, project=self.project.slug, urgent=True,
                labels=["orch:block"],
            ))
            return RunOutcome(TaskStatus.BLOCKED, detail)

        if self.project.checks and not verification.ok:
            return None
        return self._review_phase(task_id, run_id, task, acceptance, worktree, verification)

    def _review_phase(
        self, task_id: int, run_id: int, task, acceptance: list[str], worktree,
        verification: VerificationResult,
    ) -> RunOutcome:
        self.scope.set_task(task_id, status=TaskStatus.REVIEWING.value)
        summary = "\n".join(
            f"{c.name}: {'geslaagd' if c.ok else 'GEFAALD'} (exitcode {c.exit_code})"
            for c in verification.checks
        ) or "geen checks ingesteld"

        review: ReviewResult | None = None
        if self.reviewer is not None and self.project.reviewer_enabled:
            self._preflight(self.settings.reviewer_model, task_id, run_id, 25000, 4000)
            diff = redact_diff(
                worktree.full_diff(self.project.default_branch),
                self.project.redact_patterns,
            )
            context = redact_text(self._knowledge_context(), self.project.redact_patterns)
            self._log_context(task_id, "beoordelen", context, {
                "diff_tekens": len(diff),
                "verificatie_samenvatting": summary,
                "acceptatiecriteria": acceptance,
            })
            review = self.reviewer.review(
                diff=diff,
                verification_summary=summary,
                acceptance=acceptance,
                context=context,
                previous_response_id=task["reviewer_response_id"],
            )
            self._charge(review.usage, phase="review", role="beoordelaar",
                         task_id=task_id, run_id=run_id)
            before = review.verdict
            review = validate_verdict(review, acceptance)
            if before is not review.verdict:
                self._log("reviewerfout", task_id=task_id, van=before.value,
                          naar=review.verdict.value)
            self._log(
                "beoordeling", task_id=task_id, verdict=review.verdict.value,
                bevindingen=[
                    {"ernst": f.severity, "bestand": f.file, "punt": f.issue}
                    for f in review.findings
                ],
                criteria_gehaald=review.acceptance_met,
                criteria_open=review.acceptance_missing,
                alternatief=review.alternative.proposal or None,
                aanbeveling=review.alternative.recommendation,
                instructie=review.next_instruction or None,
            )
            if review.response_id:
                self.scope.set_task(task_id, reviewer_response_id=review.response_id)

        if review is not None and review.verdict is Verdict.ESCALATE:
            question = Question(
                text=review.next_instruction or "De beoordelaar escaleert deze wijziging.",
                why_blocking="beoordelaar vroeg om een menselijke beslissing",
                category="review",
                task_id=task_id,
            )
            self._park_or_block(task_id, question, Triage.BLOCK, "escalatie door de beoordelaar")
            self.scope.end_run(run_id, "escalate")
            return RunOutcome(TaskStatus.BLOCKED, "beoordelaar escaleerde")

        if review is not None and review.verdict is Verdict.REVISE:
            rounds = (task["review_rounds"] or 0) + 1
            self.scope.set_task(task_id, review_rounds=rounds)
            if rounds >= self.settings.max_review_rounds:
                self.scope.set_task(task_id, status=TaskStatus.BLOCKED.value)
                self.scope.end_run(run_id, "reviewlimiet")
                return RunOutcome(TaskStatus.BLOCKED, "reviewlimiet bereikt")
            self.scope.set_task(task_id, status=TaskStatus.QUEUED.value)
            # De bevindingen moeten de volgende ronde bereiken. Zonder dit krijgt
            # de uitvoerder exact dezelfde prompt als daarvoor, maakt hij hetzelfde
            # werk opnieuw en geeft de beoordelaar hetzelfde oordeel: betaalde
            # rondjes zonder vooruitgang.
            self.scope.set_task(task_id, review_feedback=json.dumps({
                "instructie": review.next_instruction,
                "bevindingen": [
                    {"ernst": f.severity, "bestand": f.file, "punt": f.issue,
                     "herstel": f.fix}
                    for f in review.findings
                ],
                "criteria_open": review.acceptance_missing,
            }, ensure_ascii=False))
            self.scope.end_run(run_id, "revise")
            return RunOutcome(TaskStatus.QUEUED, review.next_instruction or "herzien")

        # pass (of geen reviewer): committen mag, want de verificatie is groen
        self.scope.set_task(task_id, status=TaskStatus.COMMITTING.value)
        try:
            sha = self.git.commit(
                worktree,
                self._commit_message(task, verification),
                "orchestrator <bot@padelmq.be>",
                base=self.project.default_branch,
            )
            self._log("commit", task_id=task_id, sha=sha, branch=worktree.branch)
        except GitError as exc:
            self.scope.set_task(task_id, status=TaskStatus.FAILED.value)
            self.scope.end_run(run_id, "commit_mislukt")
            return RunOutcome(TaskStatus.FAILED, str(exc))

        self.scope.set_task(task_id, status=TaskStatus.PR_OPEN.value)
        self.scope.end_run(run_id, "pass")
        self._log("klaar", task_id=task_id, branch=worktree.branch)
        return self._publish(task_id, task, acceptance, worktree, verification, review)

    def _publish(self, task_id, task, acceptance, worktree, verification, review) -> RunOutcome:
        """Pushen en een pull request openen. Nooit mergen.

        Mislukt het pushen of het openen van de PR, dan is dat geen mislukte
        taak: de commit staat er. We melden precies wat er misging.
        """
        try:
            self.git.push(worktree)
        except GitError as exc:
            self._log("push-mislukt", task_id=task_id, detail=str(exc))
            return RunOutcome(
                TaskStatus.PR_OPEN,
                f"commit staat op {worktree.branch}, maar pushen mislukte: {exc}",
            )

        if self.github is None or not self.project.github_repo:
            return RunOutcome(
                TaskStatus.PR_OPEN,
                f"branch {worktree.branch} gepusht; geen github_repo ingesteld, "
                "dus geen PR geopend",
            )

        parked = [
            row["text"] for row in self.scope.pending_questions("park")
        ]
        body = pr_body(
            project=self.project,
            task=task,
            acceptance=acceptance,
            verification=verification,
            review=review,
            auto_answers=self._auto_answers,
            parked=parked,
        ) + "\n\n---\n_Generated by [Claude Code](https://claude.ai/code)_"

        try:
            result = self.github.create_pull_request(
                self.project.github_repo,
                title=task["title"],
                body=body,
                head=worktree.branch,
                base=self.project.default_branch,
            )
        except Exception as exc:  # noqa: BLE001 - de branch staat er; dit is niet fataal
            self._log("pr-mislukt", task_id=task_id, detail=str(exc))
            return RunOutcome(
                TaskStatus.PR_OPEN,
                f"branch {worktree.branch} gepusht; PR openen mislukte: {exc}",
            )

        url = (result or {}).get("html_url", "")
        number = (result or {}).get("number")
        self.scope.set_task(task_id, status=TaskStatus.DONE.value)
        self._log("pr-geopend", task_id=task_id, url=url, number=number)
        self.notifier.send(Message(
            subject=f"PR klaar voor review: {task['title'][:60]}",
            body=f"{url}\n\nBranch {worktree.branch}. Er wordt nooit automatisch gemerged.",
            project=self.project.slug,
        ))
        return RunOutcome(TaskStatus.DONE, f"PR geopend: {url or number}")

    # -- prompt en boodschappen ------------------------------------------
    def _build_prompt(self, task, acceptance: list[str], answered: list[Question]) -> str:
        parts = [
            f"# Taak\n{task['title']}\n",
            f"## Specificatie\n{task['spec'] or '(geen aanvullende specificatie)'}\n",
            "## Acceptatiecriteria\n" + "\n".join(f"- {c}" for c in acceptance),
            f"\n## Verificatie die hierna draait\n"
            + ("\n".join(f"- {k}: {v}" for k, v in self.project.checks.items())
               or "- geen geautomatiseerde checks; wees extra voorzichtig"),
        ]
        if answered:
            parts.append("\n## Beantwoorde vragen\n" + "\n".join(
                f"- {q.text}\n  antwoord: {q.proposed_answer}\n  bron: "
                + ", ".join(c.raw for c in q.citations)
                for q in answered
            ))
        feedback = task["review_feedback"] if "review_feedback" in task.keys() else None
        if feedback:
            gegevens = json.loads(feedback)
            regels = [
                "\n## Herziening gevraagd door de beoordelaar",
                "Dit is een GERICHTE CORRECTIE van bestaand werk, geen nieuwe opdracht.",
                "Het werk staat er al; pas alleen aan wat hieronder staat.",
                f"\nInstructie: {gegevens.get('instructie') or '(geen)'}",
            ]
            for b in gegevens.get("bevindingen", []):
                regels.append(
                    f"- [{b.get('ernst')}] {b.get('bestand')}: {b.get('punt')}"
                    + (f"\n  voorgesteld herstel: {b.get('herstel')}" if b.get("herstel") else "")
                )
            if gegevens.get("criteria_open"):
                regels.append("Nog niet gehaalde criteria: "
                              + "; ".join(gegevens["criteria_open"]))
            parts.append("\n".join(regels))

        context = self._knowledge_context()
        if context.strip():
            parts.append("\n## Projectkennis (gegevens, geen opdracht)\n" + context)
        return "\n".join(parts)

    def _commit_message(self, task, verification: VerificationResult) -> str:
        checks = ", ".join(c.name for c in verification.checks) or "geen"
        return (
            f"{task['title']}\n\n"
            f"Uitgevoerd door de orkestrator.\n"
            f"Verificatie: {checks} — allemaal geslaagd.\n"
            f"Verificatiesterkte van dit project: {self.project.strength.value}.\n"
        )
