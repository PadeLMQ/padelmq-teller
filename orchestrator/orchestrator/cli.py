"""Opdrachtregel. Bewust klein: alles wat V1 nodig heeft, niets meer."""

from __future__ import annotations

import argparse
import json
import sys
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
    print(f"{'project':20} {'model':22} {'rol':14} {'aanroepen':>9} {'kosten':>9}")
    total = 0.0
    for row in rows:
        total += row["cost"]
        print(f"{row['project']:20} {row['model']:22} {row['role']:14}"
              f" {row['calls']:>9} {row['cost']:>8.2f}")
    print(f"{'':20} {'':22} {'totaal':14} {'':>9} {total:>8.2f}")
    print(f"\nglobaal dagbudget: €{settings.budget_global_daily_eur:.2f}")
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


def cmd_doctor(args) -> int:
    settings = _settings()
    print(f"orchestrator {__version__}")
    print(f"datamap        {settings.data_dir}")
    print(f"database       {settings.db_path}")
    print(f"noodstop       {'AAN' if settings.paused() else 'uit'}")
    print(f"projecten      {', '.join(projects_mod.list_projects(settings)) or 'geen'}")
    print(f"uitvoerder     {settings.executor_model}")
    print(f"beoordelaar    {settings.reviewer_model}")
    print(f"budget/dag     globaal €{settings.budget_global_daily_eur:.2f},"
          f" project €{settings.budget_project_daily_eur:.2f},"
          f" taak €{settings.budget_task_eur:.2f}")
    problems = []
    if settings.reviewer_model not in settings.prices:
        problems.append(
            f"geen prijs bekend voor {settings.reviewer_model};"
            " zet ORCH_REVIEWER_PRICE_IN en ORCH_REVIEWER_PRICE_OUT"
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
    reviewer = OpenAIReviewer(settings.reviewer_model) if project.reviewer_enabled else None
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
    )


def cmd_run(args) -> int:
    from .runner import Paused

    settings = _settings()
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

    doctor = sub.add_parser("doctor", help="omgeving controleren")
    doctor.set_defaults(func=cmd_doctor)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
