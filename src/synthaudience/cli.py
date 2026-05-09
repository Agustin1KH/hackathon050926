"""CLI entrypoint for synthaudience."""

import json
import uuid
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from synthaudience.config import get_settings
from synthaudience.db import init_db

app = typer.Typer(name="synthaudience", help="Synthetic Audience Agent Network")
console = Console()


@app.command()
def init():
    """Create database, chroma directory, and copy example files."""
    settings = get_settings()

    # Create data directories
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)

    # Initialize database
    init_db()
    console.print("[green]Database initialized.[/green]")

    # Copy example files if they don't exist
    examples_dir = Path("examples")
    examples_dir.mkdir(exist_ok=True)

    spec_path = examples_dir / "audience_spec.json"
    if not spec_path.exists():
        console.print(f"[yellow]Example audience spec not found at {spec_path}[/yellow]")
    else:
        console.print(f"[dim]Example audience spec already at {spec_path}[/dim]")

    content_path = examples_dir / "content_to_test.json"
    if not content_path.exists():
        console.print(f"[yellow]Example content not found at {content_path}[/yellow]")
    else:
        console.print(f"[dim]Example content already at {content_path}[/dim]")

    console.print("[green]Initialization complete.[/green]")


@app.command()
def generate_personas(spec_path: str = typer.Argument(..., help="Path to audience spec JSON")):
    """Generate personas from an audience spec."""
    import asyncio

    from synthaudience.models import AudienceSpec
    from synthaudience.personas.generator import generate_personas

    spec_data = json.loads(Path(spec_path).read_text())
    spec = AudienceSpec(**spec_data)

    personas = asyncio.run(generate_personas(spec))
    console.print(f"[green]Generated {len(personas)} personas:[/green]")

    table = Table(title="Personas")
    table.add_column("Segment")
    table.add_column("Name")
    table.add_column("Age")
    table.add_column("Country")
    table.add_column("Occupation")

    for p in personas:
        table.add_row(p.segment_id, p.display_name, str(p.age), p.country, p.occupation)

    console.print(table)


@app.command()
def browse_once():
    """Run one discovery pass for all agents."""
    import asyncio

    from synthaudience.discovery.scheduler import run_browse_once
    from synthaudience.memory import MemoryStore

    memory = MemoryStore()
    result = asyncio.run(run_browse_once(memory_factory=lambda _p: memory))
    console.print(
        f"[green]Browsed {result['agents_browsed']} agents, "
        f"added {result['memories_added']} memories.[/green]"
    )


@app.command()
def evaluate(
    content_path: str = typer.Argument(..., help="Path to content payload JSON"),
    out: str | None = typer.Option(None, help="Output file path for report JSON"),
):
    """Evaluate content with all agents."""
    import asyncio

    from synthaudience.evaluation.runner import run_evaluation
    from synthaudience.memory import MemoryStore
    from synthaudience.models import ContentPayload

    content_data = json.loads(Path(content_path).read_text())
    content = ContentPayload(**content_data)
    run_id = uuid.uuid4()

    memory = MemoryStore()
    report = asyncio.run(run_evaluation(content, run_id, memory_factory=lambda _p: memory))

    if out:
        Path(out).write_text(report.model_dump_json(indent=2))
        console.print(f"[green]Report written to {out}[/green]")

    console.print(f"[green]Run ID: {run_id}[/green]")
    _print_report(report)


@app.command()
def report(run_id: str = typer.Argument(..., help="Run ID to display")):
    """Pretty-print an evaluation report."""
    from synthaudience.db import get_session_factory, RunRow

    session_factory = get_session_factory()
    with session_factory() as session:
        row = session.query(RunRow).filter_by(id=run_id).first()
        if not row or not row.report_json:
            console.print(f"[red]No report found for run {run_id}[/red]")
            raise typer.Exit(1)

        from synthaudience.models import EvaluationReport

        rpt = EvaluationReport(**json.loads(row.report_json))
        _print_report(rpt)


def _print_report(rpt):
    """Render an EvaluationReport with Rich."""
    from rich.panel import Panel

    console.print(Panel(f"Run: {rpt.run_id}\nContent: {rpt.content_id}", title="Evaluation Report"))

    # Overall
    table = Table(title="Overall Metrics")
    for key, val in rpt.overall.items():
        table.add_row(key, f"{val:.2f}" if isinstance(val, float) else str(val))
    console.print(table)

    # Per segment
    for seg_id, metrics in rpt.by_segment.items():
        table = Table(title=f"Segment: {seg_id}")
        for key, val in metrics.items():
            table.add_row(key, f"{val:.2f}" if isinstance(val, float) else str(val))
        console.print(table)

    # Themes
    if rpt.top_themes_positive:
        console.print("\n[green]Positive themes:[/green]")
        for t in rpt.top_themes_positive:
            console.print(f"  + {t}")

    if rpt.top_themes_negative:
        console.print("\n[red]Negative themes:[/red]")
        for t in rpt.top_themes_negative:
            console.print(f"  - {t}")

    # Representative comments
    if rpt.representative_comments:
        console.print("\n[bold]Representative comments:[/bold]")
        for c in rpt.representative_comments:
            console.print(f"  [{c.get('segment_id', '?')}] {c.get('comment', '')}")


if __name__ == "__main__":
    app()
