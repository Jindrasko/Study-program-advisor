from rich.prompt import Prompt
from rich.console import Console

console = Console()

def get_user_preferences():
    console.rule("[bold blue]Nastavení preferencí studia[/]")
    
    field = Prompt.ask("[bold green]O jaký obor máte zájem?[/]", default="Informatika")
    
    specialization = Prompt.ask("[bold green]Máte zájem o konkrétní specializaci? (např. AI, Kyberbezpečnost, Web, ...)[/]", default="")

    career_goals = Prompt.ask("[bold green]Jakou kariérní pozici byste chtěl/a po studiu zastávat?[/]", default="")

    focus = Prompt.ask("[bold green]Preferujete spíše teorii nebo praxi?[/]", choices=["Teorie", "Praxe", "Vyvážené"], default="Vyvážené")
    
    location = Prompt.ask("[bold green]Preferované město nebo univerzita?[/]", default="Kdekoliv")
    if location.lower() == "kdekoliv":
        location = None 
        
    level = Prompt.ask("[bold green]Typ studia?[/]", choices=["Bakalářské", "Magisterské", "Doktorské"], default="Bakalářské")
    
    language = Prompt.ask("[bold green]Preferovaný jazyk výuky?[/]", choices=["Čeština", "Angličtina"], default="Čeština")
    
    extra_details = Prompt.ask("[bold green]Další specifické požadavky? (např. možnost výjezdu do zahraničí, bez matematiky, ...)[/]", default="")

    preferences = {
        "field": field,
        "specialization": specialization,
        "career_goals": career_goals,
        "focus": focus,
        "location": location,
        "level": level,
        "language": language,
        "extra_details": extra_details
    }
    
    console.print("\n[i]Děkuji. Vaše preference byly uloženy.[/i]\n")
    return preferences
