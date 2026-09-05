"""Opdrachtregel. Bewust klein: alles wat V1 nodig heeft, niets meer."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from . import __version__
from .answers import answer_locally, process_answers
from .config import Settings
from .cost import CostGuard
from .db import Database
from .notify import ConsoleNotifier, Message, MultiNotifier
from .report import daily_digest
from . import projects as projects_mod


def _settings() -> Settings:
    settings = Settings.from_env()
    settings.ensure_dirs()
    return settings


def _guard_data_dir(settings: Settings) -> bool:
    """De kennisbasis hoort nooit in een repository. Weiger als dat toch zo is."""
    repo = settings.data_dir_inside_git()
    if repo is None:
        return True
    print(
        f"GEWEIGERD: de datamap {settings.data_dir} ligt binnen de git-repository"
        f" {repo}.\n"
        "Daar staan je businessregels en beslissingen in; die horen nooit in git.\n"
        "Zet ORCH_DATA_DIR op een pad buiten elke repository.",
        file=sys.stderr,
    )
    return False


def _db(settings: Settings) -> Database:
    return Database(settings.db_path)


# -- commando's ----------------------------------------------------------
def cmd_project_add(args) -> int:
    settings = _settings()
    checks = {}
    for pair in args.check or []:
        name, _, command = pair.partition("=")
        if not command:
            print(f"check {pair!r} moet de vorm naam=commando hebben", file=sys.stderr)
            return 2
        checks[name.strip()] = command.strip()
    project = projects_mod.add(
        settings, args.slug, args.repo, checks=checks,
        github_repo=args.github_repo or "", default_branch=args.branch,
    )
    _db(settings).ensure_project(args.slug)
    print(f"project {project.slug} toegevoegd in {project.root}")
    print(f"verificatiesterkte: {project.strength.value}"
          f" (max {project.strength.max_implement_iterations} iteraties per taak)")
    if project.strength.value == "zwak":
        print("Let op: geen machinaal bewijs in dit project. De lus bouwt hier niet")
        print("zelfstandig door. Overweeg als eerste taak een minimale testsuite.")
    return 0


def cmd_project_list(args) -> int:
    settings = _settings()
    slugs = projects_mod.list_projects(settings)
    if not slugs:
        print("nog geen projecten; voeg er een toe met 'project add'")
        return 0
    for slug in slugs:
        project = projects_mod.load(settings, slug)
        print(f"{slug:24} {project.strength.value:8} {project.repo}")
    return 0


def cmd_task_add(args) -> int:
    settings = _settings()
    db = _db(settings)
    scope = db.scope(args.project)
    if not args.acceptance:
        print("een taak zonder toetsbare acceptatiecriteria komt de lus niet in;"
              " geef er minstens een met --acceptance", file=sys.stderr)
        return 2
    task_id = scope.add_task(
        args.title, spec=args.spec or "", acceptance=args.acceptance, priority=args.priority
    )
    print(f"taak {task_id} toegevoegd aan {args.project}")
    return 0


def cmd_task_list(args) -> int:
    settings = _settings()
    db = _db(settings)
    slugs = [args.project] if args.project else projects_mod.list_projects(settings)
    for slug in slugs:
        scope = db.scope(slug)
        rows = scope.tasks()
        if not rows:
            continue
        print(f"\n{slug}")
        for row in rows:
            print(f"  {row['id']:>4}  {row['status']:<14} {row['title']}")
    return 0


def cmd_questions(args) -> int:
    settings = _settings()
    db = _db(settings)
    slugs = [args.project] if args.project else projects_mod.list_projects(settings)
    for slug in slugs:
        rows = db.scope(slug).open_questions()
        if not rows:
            continue
        print(f"\n{slug}")
        for row in rows:
            options = json.loads(row["options"] or "[]")
            print(f"  #{row['id']} [{row['outcome']}] {row['text']}")
            if options:
                print("      opties: " + " · ".join(options))
            if row["proposed"]:
                print(f"      voorstel: {row['proposed']}")
    return 0


def cmd_answer(args) -> int:
    settings = _settings()
    db = _db(settings)
    project = projects_mod.load(settings, args.project)
    item_id = answer_locally(
        scope=db.scope(args.project), project=project,
        question_id=args.question_id, answer=args.answer,
    )
    print(f"vastgelegd als {item_id}; wachtende taken staan weer in de rij")
    return 0


def cmd_poll_answers(args) -> int:
    from .notify.github import GitHubClient

    settings = _settings()
    db = _db(settings)
    slugs = [args.project] if args.project else projects_mod.list_projects(settings)
    for slug in slugs:
        project = projects_mod.load(settings, slug)
        if not project.github_repo:
            continue
        actions = process_answers(
            scope=db.scope(slug), project=project, client=GitHubClient(),
        )
        for action in actions:
            print(f"{slug}: {action}")
    return 0


def cmd_digest(args) -> int:
    settings = _settings()
    db = _db(settings)
    slugs = projects_mod.list_projects(settings)
    text = daily_digest(db, slugs, day=args.day)
    if args.send:
        from .notify.email import EmailNotifier

        EmailNotifier().send(Message(subject="Dagrapport", body=text))
        print("dagrapport verstuurd")
    else:
        print(text)
    return 0


def cmd_costs(args) -> int:
    settings = _settings()
    db = _db(settings)
    guard = CostGuard(db, settings)
    rows = guard.report(day=args.day)
    if not rows:
        print("nog geen kosten geregistreerd voor deze dag")
        return 0
    print(f"{'project':20} {'model':22} {'rol':14} {'aanroepen':>9}"
          f" {'kosten (' + settings.currency + ')':>13}")
    total = 0.0
    for row in rows:
        total += row["cost"]
        print(f"{row['project']:20} {row['model']:22} {row['role']:14}"
              f" {row['calls']:>9} {row['cost']:>12.4f}")
    print(f"{'':20} {'':22} {'totaal':14} {'':>9} {total:>12.4f}")
    print(f"\nglobaal dagbudget: {settings.symbol}{settings.budget_global_daily_eur:.2f}")

    maand = (args.day or date.today().isoformat())[:7]
    per_project = []
    for slug in projects_mod.list_projects(settings):
        bedrag = db.scope(slug).spend_month(maand)
        if bedrag:
            per_project.append((slug, bedrag))
    if per_project:
        print(f"\nmaand {maand}:")
        for slug, bedrag in sorted(per_project, key=lambda p: -p[1]):
            print(f"  {slug:24} {settings.symbol}{bedrag:>10.4f}")
        print(f"  {'totaal':24} {settings.symbol}"
              f"{sum(b for _, b in per_project):>10.4f}")
    return 0


def cmd_pause(args) -> int:
    settings = _settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    if args.off:
        if settings.stop_file.exists():
            settings.stop_file.unlink()
        print("noodstop uit; de orkestrator mag weer werken")
    else:
        settings.stop_file.write_text("gepauzeerd via de opdrachtregel\n", encoding="utf-8")
        print(f"noodstop aan: {settings.stop_file}")
    return 0


def cmd_import_chatgpt(args) -> int:
    print(
        "De import is met opzet nog niet geimplementeerd.\n\n"
        "Het ontwerp legt vast dat we de exacte structuur van de ChatGPT-export op\n"
        "een echt bestand verifieren voordat we de parser schrijven. Een parser\n"
        "bouwen op een geraden formaat is precies het soort giswerk dat we hier\n"
        "niet doen.\n\n"
        f"Lever de export aan ({args.export}) en dan schrijf ik de parser op wat er\n"
        "werkelijk in zit."
    )
    return 1


def _sleutel_status(naam: str) -> str:
    """Meldt of een geheim gezet is, zonder ooit de waarde te tonen.

    De vingerafdruk is de eerste acht tekens van de sha256. Daarmee kun je twee
    omgevingen vergelijken ("staat overal dezelfde sleutel?") zonder dat de
    sleutel zelf ergens in beeld of in een logboek komt.
    """
    import hashlib

    waarde = os.environ.get(naam, "")
    if not waarde:
        return "NIET gezet"
    afdruk = hashlib.sha256(waarde.encode()).hexdigest()[:8]
    return f"gezet (vingerafdruk {afdruk})"



def _reviewer_auth_status() -> tuple[bool, str]:
    """Kan de reviewer werkelijk authenticeren?

    De oude controle keek of OPENAI_API_KEY gezet was. Dat bewijst niets: een
    verlopen sleutel haalt die test even goed. En het is onjuist in een omgeving
    waar een credential-proxy de Authorization-header buiten deze runtime
    injecteert; daar hoort de sleutel juist NIET in het procesgeheugen te staan.

    We vragen daarom de modellenlijst op. Dat is een gratis eindpunt: het kost
    geen tokens en verbruikt geen budget, maar het bewijst het hele pad --
    netwerk, egress-policy, authenticatie en SDK -- in een keer.
    """
    try:
        from openai import OpenAI
    except ImportError:
        return False, "pakket 'openai' ontbreekt"

    in_omgeving = bool(os.environ.get("OPENAI_API_KEY"))
    # Zonder sleutel in de omgeving moet de SDK toch een waarde hebben om een
    # client te bouwen. De proxy vervangt de header; deze waarde is geen geheim.
    sleutel = None if in_omgeving else "placeholder-credential-proxy"
    bron = "sleutel uit omgeving" if in_omgeving else "credential-proxy"
    try:
        modellen = OpenAI(api_key=sleutel).models.list()
    except Exception as exc:  # noqa: BLE001 - elke fout is hier een probleem
        return False, f"{bron}: {type(exc).__name__}: {str(exc)[:120]}"
    aantal = len(getattr(modellen, "data", []) or [])
    return True, f"OK via {bron} ({aantal} modellen zichtbaar, gratis eindpunt)"

def cmd_doctor(args) -> int:
    settings = _settings()
    print(f"orchestrator {__version__}")
    print(f"datamap        {settings.data_dir}")
    print(f"database       {settings.db_path}")
    print(f"noodstop       {'AAN' if settings.paused() else 'uit'}")
    print(f"projecten      {', '.join(projects_mod.list_projects(settings)) or 'geen'}")
    print(f"uitvoerder     {settings.executor_model}")
    print(f"beoordelaar    {settings.reviewer_model}")
    print(f"valuta         {settings.currency} (geen omrekening; tarieven moeten in "
          f"deze valuta staan)")
    print(f"budget/dag     globaal {settings.symbol}{settings.budget_global_daily_eur:.2f},"
          f" project {settings.symbol}{settings.budget_project_daily_eur:.2f},"
          f" taak {settings.symbol}{settings.budget_task_eur:.2f}")
    print("geheimen:")
    for naam in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "ORCH_GITHUB_TOKEN",
                 "ORCH_VOICE_TOKEN"):
        print(f"  {naam:20} {_sleutel_status(naam)}")

    problems = []
    ok, detail = _reviewer_auth_status()
    print(f"reviewer-auth   {detail}")
    if not ok:
        problems.append(f"de reviewer kan niet authenticeren: {detail}")
    try:
        import openai  # noqa: F401
    except ImportError:
        problems.append("pakket 'openai' ontbreekt; pip install \"openai>=1.0\"")
    if settings.reviewer_model not in settings.prices:
        problems.append(
            f"geen prijs bekend voor {settings.reviewer_model};"
            " zet ORCH_REVIEWER_PRICE_IN en ORCH_REVIEWER_PRICE_OUT"
        )
    if settings.data_dir_inside_git():
        problems.append(
            f"de datamap ligt binnen de git-repository "
            f"{settings.data_dir_inside_git()}; verplaats hem"
        )
    import shutil
    if shutil.which("claude") is None:
        problems.append("'claude' staat niet in PATH")
    if shutil.which("git") is None:
        problems.append("'git' staat niet in PATH")
    for problem in problems:
        print(f"  ! {problem}")
    return 1 if problems else 0



def _build_runner(settings, db, project):
    from .adapters.claude import ClaudeExecutor
    from .adapters.reviewer import OpenAIReviewer
    from .cost import CostGuard
    from .git import GitAdapter
    from .notify.email import EmailNotifier
    from .notify.github import GitHubClient, GitHubNotifier
    from .runner import Runner
    from .verify import VerifyAdapter

    channels = []
    if "email" in project.notify:
        mailer = EmailNotifier()
        if mailer.configured:
            channels.append(mailer)
    if "github" in project.notify and project.github_repo:
        channels.append(GitHubNotifier(GitHubClient(), project.github_repo))
    channels.append(ConsoleNotifier())

    guard = CostGuard(
        db, settings,
        on_warning=lambda level, pct, spent, limit: print(
            f"waarschuwing: {level} op {pct:.0%} (€{spent:.2f} van €{limit:.2f})"
        ),
    )
    reviewer = None
    if project.reviewer_enabled:
        from .reviewcache import ReviewCache

        scope = db.scope(project.slug)
        reviewer = ReviewCache(
            OpenAIReviewer(settings.reviewer_model),
            scope,
            settings.reviewer_model,
            on_hit=lambda soort, sleutel, usage: scope.log(
                "cache-treffer",
                {"soort": soort, "sleutel": sleutel[:16],
                 "bespaarde_tokens_in": usage.tokens_in,
                 "bespaarde_tokens_uit": usage.tokens_out},
            ),
        )
    github = GitHubClient() if project.github_repo else None
    return Runner(
        settings=settings,
        project=project,
        scope=db.scope(project.slug),
        executor=ClaudeExecutor(settings.executor_model,
                                timeout_seconds=settings.run_timeout_seconds),
        reviewer=reviewer,
        verifier=VerifyAdapter(),
        git=GitAdapter(settings.data_dir / "worktrees"),
        notifier=MultiNotifier(*channels),
        cost=guard,
        github=github,
    )


def cmd_run(args) -> int:
    from .runner import Paused

    settings = _settings()
    if not _guard_data_dir(settings):
        return 2
    db = _db(settings)
    if settings.paused():
        print(f"noodstop actief ({settings.stop_file}); niets gedaan")
        return 1

    slugs = [args.project] if args.project else projects_mod.list_projects(settings)
    if not slugs:
        print("geen projecten om te draaien")
        return 0

    done = 0
    for _ in range(args.max_tasks):
        progressed = False
        for slug in slugs:
            project = projects_mod.load(settings, slug)
            scope = db.scope(slug)
            task = scope.next_queued()
            if task is None:
                continue
            runner = _build_runner(settings, db, project)
            print(f"\n[{slug}] taak {task['id']}: {task['title']}")
            try:
                outcome = runner.run_task(task["id"])
            except Paused as exc:
                print(str(exc))
                return 1
            print(f"[{slug}] -> {outcome.status.value}: {outcome.detail}")
            progressed = True
            done += 1
            break
        if not progressed:
            break
    if done == 0:
        print("niets te doen; alle taken staan klaar, geparkeerd of geblokkeerd")
    return 0



def cmd_inspect(args) -> int:
    from .inspect import format_report, inspect as inspect_repo

    print(format_report(inspect_repo(Path(args.path).expanduser())))
    return 0


def cmd_verify_reviewer(args) -> int:
    from .validate_reviewer import validate_offline, validate_online

    settings = _settings()
    offline = validate_offline()
    print(offline.render())
    if offline.failed:
        return 1
    if args.offline:
        print("\n(alleen de offline trap gedraaid; voeg --online toe voor een echte aanroep)")
        return 0

    model = args.model or settings.reviewer_model
    if not model:
        print("geen model opgegeven; gebruik --model of zet ORCH_REVIEWER_MODEL",
              file=sys.stderr)
        return 2
    print()
    online = validate_online(model)
    print(online.render())
    return 1 if online.failed else 0



def cmd_secret_scan(args) -> int:
    from .secret_scan import format_hits, scan_staged, scan_tree

    root = Path(args.path or ".").expanduser().resolve()
    hits = scan_staged(root) if args.staged else scan_tree(root)
    print(format_hits(hits))
    return 1 if hits else 0



def cmd_question_add(args) -> int:
    """Een openstaande beslissing registreren zonder dat de lus draait.

    Zo kunnen bevindingen uit een codebeoordeling in dezelfde wachtrij komen
    als de vragen die de orkestrator zelf stelt.
    """
    settings = _settings()
    # Het project moet bestaan: een typefout mag geen spookproject aanmaken
    # waarin vragen onvindbaar verdwijnen.
    projects_mod.load(settings, args.project)
    db = _db(settings)
    scope = db.scope(args.project)
    question_id = scope.add_question(
        text=args.text,
        outcome=args.outcome,
        fingerprint=" ".join(args.text.lower().split()),
        why_blocking=args.why or "",
        options=args.option or [],
        proposed=args.proposed,
        category=args.category,
    )
    print(f"vraag #{question_id} geregistreerd in {args.project} als {args.outcome}")
    return 0



def cmd_voice_serve(args) -> int:
    from .voice.api import maak_server
    from .voice.service import VoiceService

    settings = _settings()
    if not _guard_data_dir(settings):
        return 2
    db = _db(settings)
    try:
        server = maak_server(
            VoiceService(settings, db), host=args.host, port=args.port,
            per_minuut=args.per_minuut,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    host, poort = server.server_address[:2]
    print(f"spraakeindpunt luistert op http://{host}:{poort}")
    print("  GET  /voice/next[?project=<slug>]")
    print("  POST /voice/answer")
    if host not in ("127.0.0.1", "::1", "localhost"):
        print("LET OP: dit luistert niet alleen op localhost. Zet er een reverse proxy",
              "met TLS voor; stuur dit token nooit onversleuteld over het internet.",
              file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\ngestopt")
    finally:
        server.server_close()
    return 0



def cmd_report(args) -> int:
    from .runreport import build_report, format_report

    settings = _settings()
    db = _db(settings)
    project = projects_mod.load(settings, args.project)
    rapport = build_report(db.scope(args.project), project, args.task_id)
    print(rapport.as_json() if args.json else format_report(rapport, settings.symbol))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="orchestrator", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    project = sub.add_parser("project", help="projecten beheren").add_subparsers(
        dest="sub", required=True
    )
    add = project.add_parser("add", help="een project toevoegen")
    add.add_argument("slug")
    add.add_argument("--repo", required=True, help="pad naar de git-repository")
    add.add_argument("--github-repo", default="", help="eigenaar/repo voor issues en PR's")
    add.add_argument("--branch", default="main")
    add.add_argument("--check", action="append", metavar="NAAM=COMMANDO")
    add.set_defaults(func=cmd_project_add)
    listing = project.add_parser("list", help="projecten tonen")
    listing.set_defaults(func=cmd_project_list)

    task = sub.add_parser("task", help="taken beheren").add_subparsers(dest="sub", required=True)
    task_add = task.add_parser("add")
    task_add.add_argument("project")
    task_add.add_argument("title")
    task_add.add_argument("--spec", default="")
    task_add.add_argument("--acceptance", action="append", default=[])
    task_add.add_argument("--priority", type=int, default=100)
    task_add.set_defaults(func=cmd_task_add)
    task_list = task.add_parser("list")
    task_list.add_argument("project", nargs="?")
    task_list.set_defaults(func=cmd_task_list)

    qadd = sub.add_parser("question-add", help="een openstaande beslissing registreren")
    qadd.add_argument("project")
    qadd.add_argument("text")
    qadd.add_argument("--outcome", choices=["park", "block"], default="park")
    qadd.add_argument("--why", default="")
    qadd.add_argument("--option", action="append")
    qadd.add_argument("--proposed")
    qadd.add_argument("--category")
    qadd.set_defaults(func=cmd_question_add)

    questions = sub.add_parser("questions", help="openstaande vragen tonen")
    questions.add_argument("project", nargs="?")
    questions.set_defaults(func=cmd_questions)

    answer = sub.add_parser("answer", help="een vraag beantwoorden")
    answer.add_argument("project")
    answer.add_argument("question_id", type=int)
    answer.add_argument("answer")
    answer.set_defaults(func=cmd_answer)

    poll = sub.add_parser("poll-answers", help="antwoorden uit GitHub-issues ophalen")
    poll.add_argument("project", nargs="?")
    poll.set_defaults(func=cmd_poll_answers)

    digest = sub.add_parser("digest", help="dagrapport")
    digest.add_argument("--day")
    digest.add_argument("--send", action="store_true")
    digest.set_defaults(func=cmd_digest)

    costs = sub.add_parser("costs", help="kostenoverzicht")
    costs.add_argument("--day")
    costs.set_defaults(func=cmd_costs)

    pause = sub.add_parser("pause", help="noodstop aan of uit")
    pause.add_argument("--off", action="store_true")
    pause.set_defaults(func=cmd_pause)

    imp = sub.add_parser("import", help="kennisbasis vullen").add_subparsers(
        dest="sub", required=True
    )
    chatgpt = imp.add_parser("chatgpt")
    chatgpt.add_argument("export")
    chatgpt.set_defaults(func=cmd_import_chatgpt)

    run = sub.add_parser("run", help="werk de wachtrij af")
    run.add_argument("project", nargs="?", help="beperk tot één project")
    run.add_argument("--max-tasks", type=int, default=1,
                     help="hoeveel taken maximaal in deze aanroep (standaard 1)")
    run.set_defaults(func=cmd_run)

    inspect_p = sub.add_parser("inspect", help="welke verificatie heeft een repository echt")
    inspect_p.add_argument("path")
    inspect_p.set_defaults(func=cmd_inspect)

    verify = sub.add_parser("verify-reviewer",
                            help="controleer de reviewer-aanroep tegen de echte SDK/API")
    verify.add_argument("--model", help="goedkoopste geschikte model voor de validatie")
    verify.add_argument("--offline", action="store_true",
                        help="alleen de SDK-handtekening controleren; geen netwerk, geen kosten")
    verify.set_defaults(func=cmd_verify_reviewer)

    scan = sub.add_parser("secret-scan", help="controleer op geheimen voor ze in git belanden")
    scan.add_argument("path", nargs="?", default=".")
    scan.add_argument("--staged", action="store_true",
                      help="alleen wat klaarstaat om gecommit te worden")
    scan.set_defaults(func=cmd_secret_scan)

    voice = sub.add_parser("voice-serve", help="het spraakeindpunt draaien")
    voice.add_argument("--host", default=None, help="standaard 127.0.0.1")
    voice.add_argument("--port", type=int, default=None, help="standaard 8765")
    voice.add_argument("--per-minuut", type=int, default=60, dest="per_minuut")
    voice.set_defaults(func=cmd_voice_serve)

    report = sub.add_parser("report", help="het eindrapport van een taak")
    report.add_argument("project")
    report.add_argument("task_id", type=int)
    report.add_argument("--json", action="store_true")
    report.set_defaults(func=cmd_report)

    doctor = sub.add_parser("doctor", help="omgeving controleren")
    doctor.set_defaults(func=cmd_doctor)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
