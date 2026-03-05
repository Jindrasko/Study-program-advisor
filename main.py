import os
import sys
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.preferences import get_user_preferences
from src.researcher import search_programs, fetch_page_content
from src.analyst import analyze_content, create_fallback_result
from src.reporter import display_results, save_report

load_dotenv()
console = Console()


def main():
    try:
        console.print("\n[bold magenta]=== Agent pro rešerši studijních programů ===[/]\n")
        
        prefs = get_user_preferences()
        
        console.print("\n[cyan]Fáze 1: Vyhledávání na internetu...[/cyan]")
        search_results = search_programs(prefs, max_results=8)
        
        if not search_results:
            console.print("[red]Nebyly nalezeny žádné výsledky. Zkuste změnit kritéria.[/]")
            console.print("[dim]Tip: Zkuste zadat obecnější obor nebo vynechat lokaci.[/dim]")
            return
            
        console.print(f"[green]✓ Nalezeno {len(search_results)} potenciálních stránek.[/green]")
        
        console.print("\n[cyan]Fáze 2: Stahování obsahu stránek...[/cyan]")
        results_with_content = []
        failed_downloads = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task("[cyan]Stahuji...", total=len(search_results))
            
            for res in search_results:
                result = fetch_page_content(res['href'])
                if isinstance(result, dict):
                    content = result.get('text', '')
                    metadata = result.get('metadata', {})
                else:
                    content = result
                    metadata = {}
                
                if content and len(content) > 100:
                    res['content'] = content
                    res['metadata'] = metadata
                    results_with_content.append(res)
                else:
                    failed_downloads += 1
                progress.advance(task)
        
        if not results_with_content:
            console.print("[yellow]Nepodařilo se stáhnout žádný obsah.[/]")
            console.print("[dim]Používám výsledky vyhledávání jako zálohu...[/dim]")
            results_with_content = search_results
        else:
            console.print(f"[green]✓ Staženo {len(results_with_content)} stránek.[/green]")
            if failed_downloads > 0:
                console.print(f"[dim]({failed_downloads} stránek se nepodařilo stáhnout)[/dim]")
        
        console.print("\n[cyan]Fáze 3: AI analýza obsahu...[/cyan]")
        analyzed_data = analyze_content(results_with_content, prefs)
        
        if not analyzed_data:
            console.print("\n[yellow]AI analýza nedostupná. Extrahuji data přímo z obsahu stránek...[/yellow]")
            for item in results_with_content:
                fallback = create_fallback_result(item)
                analyzed_data.append(fallback)
            analyzed_data.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        
        console.print("\n[cyan]Fáze 4: Generování reportu...[/cyan]")
        display_results(analyzed_data)
        save_report(analyzed_data)
        
        console.print("\n[bold green]✓ Hotovo![/bold green]")
        console.print("[dim]Tip: Otevřete soubor report.md pro detailní report.[/dim]\n")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Přerušeno uživatelem.[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]Neočekávaná chyba: {e}[/bold red]")
        console.print("[dim]Zkontrolujte připojení k internetu a API klíč.[/dim]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    main()
