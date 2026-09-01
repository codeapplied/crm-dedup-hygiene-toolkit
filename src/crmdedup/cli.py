import typer
from rich.console import Console
from rich.table import Table

from .config import load_rules, settings
from .storage.db import get_engine, get_session_factory, init_db
from .storage.models import MergeLog

app = typer.Typer(help="CRM Dedup/Hygiene Toolkit — ops CLI")
console = Console()


@app.command()
def init() -> None:
    """Initialize the database."""
    engine = get_engine(settings.db_path)
    init_db(engine)
    console.print(f"[green]Database initialized at {settings.db_path}[/green]")


@app.command()
def status() -> None:
    """Show merge history: recent duplicate groups processed."""
    engine = get_engine(settings.db_path)
    session_factory = get_session_factory(engine)
    with session_factory() as session:
        logs = session.query(MergeLog).order_by(MergeLog.started_at.desc()).limit(20).all()

    if not logs:
        console.print("[yellow]No merge runs recorded yet. Run 'crmdedup discover' first.[/yellow]")
        raise typer.Exit()

    table = Table(title="Recent Merge Runs")
    for column in ("Entity", "Group Key", "Primary", "Absorbed", "Dry Run", "Status", "Started"):
        table.add_column(column)
    for log in logs:
        absorbed_count = len([x for x in log.absorbed_record_ids.split(",") if x])
        table.add_row(
            log.entity_type,
            log.group_key,
            str(log.primary_record_id),
            str(absorbed_count),
            str(log.dry_run),
            log.status,
            str(log.started_at),
        )
    console.print(table)


@app.command()
def rules() -> None:
    """Show the loaded scoring weights and known-false-positive skip list."""
    r = load_rules()
    if not r.score_weights and not r.skip_pairs:
        console.print("[yellow]No rules configured. Copy config/rules.example.yaml to config/rules.yaml.[/yellow]")
        raise typer.Exit()
    console.print(f"Score weights: {r.score_weights or '-'}")
    console.print(f"Skip pairs: {len(r.skip_pairs)}")


@app.command()
def discover() -> None:
    """Find duplicate groups (organizations by domain, contacts by email)."""
    console.print("[red]Pipeline not implemented yet — see upcoming phases.[/red]")
    raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
