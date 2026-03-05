from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
import pandas as pd

console = Console()

def display_results(analyzed_programs):
    if not analyzed_programs:
        console.print("[yellow]Nebyly nalezeny žádné relevantní programy odpovídající analýze.[/]")
        return

    table = Table(title="Doporučené studijní programy", box=box.ROUNDED)

    table.add_column("Skóre", justify="center", style="cyan", no_wrap=True)
    table.add_column("Univerzita", style="magenta")
    table.add_column("Program", style="green")
    table.add_column("Typ", justify="center")
    table.add_column("Délka", justify="center")
    table.add_column("Klíčové výhody")

    sorted_programs = sorted(analyzed_programs, key=lambda x: x.get('match_score', 0), reverse=True)

    for prog in sorted_programs:
        score = str(prog.get('match_score', 0))
        uni = f"{prog.get('university', 'N/A')}\n[dim]{prog.get('faculty', '')}[/dim]"
        name = prog.get('program_name', 'N/A')
        degree = prog.get('degree', 'N/A')
        duration = prog.get('duration', 'N/A')
        
        pros = ", ".join(prog.get('pros', [])[:3])
        
        table.add_row(score, uni, name, degree, duration, pros)

    console.print(table)
    console.print("\n")

def save_report(analyzed_programs, filename="report.md"):
    if not analyzed_programs:
        return

    sorted_programs = sorted(analyzed_programs, key=lambda x: x.get('match_score', 0), reverse=True)
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write("# Analýza studijních programů\n\n")
        
        for prog in sorted_programs:
            f.write(f"## {prog.get('program_name')} - {prog.get('university')}\n")
            f.write(f"**Shoda:** {prog.get('match_score')}%\n\n")
            f.write(f"**Důvod shody:** {prog.get('match_reason', '')}\n\n")
            f.write(f"**Fakulta:** {prog.get('faculty')}\n")
            f.write(f"**Typ:** {prog.get('degree')}, **Délka:** {prog.get('duration')}\n\n")
            f.write(f"**Popis:** {prog.get('description')}\n\n")
            
            f.write("### Výhody\n")
            for p in prog.get('pros', []):
                f.write(f"- {p}\n")
                
            f.write("\n### Nevýhody/Poznámky\n")
            for c in prog.get('cons', []):
                f.write(f"- {c}\n")
                
            f.write(f"\n[Odkaz na stránky]({prog.get('url')})\n")
            f.write("\n---\n\n")
            
    console.print(f"[green]Detailní report uložen do souboru: {filename}[/]")
