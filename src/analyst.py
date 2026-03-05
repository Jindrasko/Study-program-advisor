import os
import json
import re
import google.generativeai as genai
from rich.console import Console

console = Console()

def configure_genai():
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        console.print("[bold red]CHYBA: Nenalezen API klíč. Ujistěte se, že máte nastavenou proměnnou GOOGLE_API_KEY v souboru .env[/]")
        return False
    
    try:
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        console.print(f"[bold red]CHYBA při konfiguraci Gemini API: {e}[/]")
        return False


def extract_json_from_text(text):
    if not text:
        return None
    
    cleaned = text.strip()
    
    # Remove markdown code blocks
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    
    cleaned = cleaned.strip()
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    
    # Regex fallback for JSON extraction
    json_patterns = [
        r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # Nested braces
        r'\{.*?\}',  # Simple braces (non-greedy)
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, cleaned, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
    
    # Common JSON fixes
    try:
        # Replace single quotes with double quotes
        fixed = cleaned.replace("'", '"')
        # Fix trailing commas
        fixed = re.sub(r',\s*([}\]])', r'\1', fixed)
        return json.loads(fixed)
    except:
        pass
    
    return None


def build_preferences_string(user_preferences):
    if not user_preferences:
        return "Žádné specifické preference nebyly zadány."
    
    parts = []
    
    field_map = {
        "field": "Obor",
        "specialization": "Specializace", 
        "career_goals": "Kariérní cíle",
        "focus": "Zaměření (teorie/praxe)",
        "location": "Lokace",
        "level": "Typ studia",
        "language": "Jazyk",
        "extra_details": "Další požadavky"
    }
    
    for key, label in field_map.items():
        value = user_preferences.get(key)
        if value and str(value).strip() and str(value).lower() not in ["", "none", "kdekoliv"]:
            parts.append(f"{label}: {value}")
    
    if not parts:
        return "Obecný zájem o vysokoškolské studium."
    
    return ", ".join(parts)


def analyze_content(search_results_with_content, user_preferences):
    if not configure_genai():
        return []
    
    if not search_results_with_content:
        console.print("[yellow]Žádný obsah k analýze.[/]")
        return []
    
    model = None
    model_names = [
        'gemini-2.5-flash-lite',
        'gemini-2.5-flash',
        'gemini-2.0-flash',
        'gemini-2.0-flash-lite',
    ]
    
    for model_name in model_names:
        try:
            model = genai.GenerativeModel(model_name)
            console.print(f"[dim]Používám model: {model_name}[/dim]")
            break
        except Exception:
            continue
            
    if not model:
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
        except:
             console.print("[bold red]Nelze inicializovat žádný Gemini model.[/]")
             return []
    
    analyzed_programs = []
    prefs_str = build_preferences_string(user_preferences)
    
    console.print("[cyan]Spouštím AI analýzu stránek...[/]")
    
    total_pages = len(search_results_with_content)
    analyzed_count = 0
    error_count = 0
    offline_mode = False

    for idx, item in enumerate(search_results_with_content, 1):
        url = item.get('href', '')
        text = item.get('content', '')
        title = item.get('title', 'Neznámá stránka')
        body_snippet = item.get('body', '')
        metadata = item.get('metadata', {})
        
        # If in offline mode, just use fallback
        if offline_mode:
            fallback = create_fallback_result(item)
            if fallback:
                fallback['match_score'] = fallback.get('match_score', 0)
                # Slightly lower score for offline results to prioritize AI ones if mixed
                analyzed_programs.append(fallback)
                console.print(f"[dim yellow]  (Offline) Extrahováno: {fallback['program_name'][:40]}...[/dim yellow]")
            analyzed_count += 1
            continue

        # Be more lenient with content length - even short pages might be relevant
        if not text:
            text = body_snippet  # Use search snippet as fallback
        
        if not text or len(text.strip()) < 50:
            console.print(f"[dim]({idx}/{total_pages}) Přeskakuji - příliš krátký obsah: {title[:50]}...[/dim]")
            continue
        
        text_for_analysis = text[:12000]
        
        meta_context = ""
        if metadata:
            meta_context = f"""
NALEZENÁ METADATA ZE STRUKTURY STRÁNKY:
Typ: {metadata.get('degree', 'N/A')}
Délka: {metadata.get('duration', 'N/A')}
"""

        prompt = f"""Jsi expert na vysokoškolské vzdělávání v České republice. Analyzuj text z webové stránky a extrahuj informace o studijním programu.

PREFERENCE UŽIVATELE:
{prefs_str}

STRÁNKA: {title}
URL: {url}
{meta_context}

TEXT STRÁNKY:
---
{text_for_analysis}
---

ÚKOL:
1. Urči, zda stránka obsahuje informace o konkrétním studijním programu.
2. I pokud je to jen částečná informace nebo seznam programů, pokus se extrahovat co nejvíce.
3. Pokud metadata obsahují Typ nebo Délku, POUŽIJ JE, pokud v textu nenajdeš opak.
4. Buď velkorysý s hodnocením - pokud program MŮŽE odpovídat preferencím, dej mu šanci.

DŮLEŽITÉ: Vrať POUZE validní JSON bez jakéhokoliv dalšího textu:
{{
    "is_relevant": true,
    "university": "Název univerzity (pokud zjištěn, jinak 'Neznámá')",
    "faculty": "Název fakulty (pokud zjištěn, jinak '')",
    "program_name": "Název programu (pokud zjištěn, jinak shrň hlavní téma)",
    "degree": "Bc./Mgr./Ph.D./NMgr. (pokud zjištěn, jinak 'N/A')",
    "duration": "Délka studia (pokud zjištěna, jinak 'N/A')",
    "description": "2-3 věty popisující program nebo obsah stránky",
    "pros": ["Klad 1", "Klad 2", "Klad 3"],
    "cons": ["Možná nevýhoda 1"],
    "match_score": 50,
    "match_reason": "Vysvětlení proč program odpovídá nebo neodpovídá preferencím"
}}

Pokud stránka vůbec nesouvisí se studiem, nastav is_relevant na false a match_score na 0."""

        console.print(f"[dim]({idx}/{total_pages}) Analyzuji: {title[:60]}...[/dim]")
        
        try:
            for attempt in range(2):
                try:
                    response = model.generate_content(
                        prompt,
                        generation_config={
                            "temperature": 0.3,
                            "max_output_tokens": 1024,
                        }
                    )
                    break # Success
                except Exception as e:
                    if "429" in str(e) or "ResourceExhausted" in str(e) or "Quota" in str(e):
                        if attempt == 0:
                            import time
                            time.sleep(2)
                            continue
                    raise e
            
            if not response or not response.text:
                error_count += 1
                continue
            
            data = extract_json_from_text(response.text)
            
            if data is None:
                console.print(f"[dim yellow]Nepodařilo se parsovat JSON odpověď pro: {title[:40]}[/dim yellow]")
                error_count += 1
                continue
            
            analyzed_count += 1
            
            # Be more lenient - include anything with is_relevant=true OR score > 20
            is_relevant = data.get("is_relevant", False)
            match_score = data.get("match_score", 0)
            
            # Convert string score to int if needed
            if isinstance(match_score, str):
                try:
                    match_score = int(match_score)
                except:
                    match_score = 50  # Default if can't parse
            
            # Lower threshold - include more results and let user decide
            if is_relevant or match_score > 20:
                data['url'] = url
                data['source_title'] = title
                data['match_score'] = match_score
                if data.get('degree') == 'N/A' and metadata.get('degree'):
                    data['degree'] = metadata.get('degree')
                if data.get('duration') == 'N/A' and metadata.get('duration'):
                    data['duration'] = metadata.get('duration')
                    
                analyzed_programs.append(data)
                console.print(f"[green]  ✓ Nalezen relevantní program (skóre: {match_score})[/green]")
                
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "ResourceExhausted" in error_msg or "Quota" in error_msg:
                console.print(f"[bold yellow]! Vyčerpána API kvóta Gemini. Přepínám na offline režim pro zbytek stránek.[/bold yellow]")
                offline_mode = True
                # Process current item again in offline mode
                fallback = create_fallback_result(item)
                if fallback:
                    analyzed_programs.append(fallback)
                analyzed_count += 1
                continue
            
            error_count += 1
            # Log error but continue with other pages
            console.print(f"[dim red]Chyba při analýze {title[:40]}: {str(e)[:50]}[/dim red]")
            continue

    final_results = filter_results_by_preferences(analyzed_programs, user_preferences)
    
    console.print(f"\n[cyan]Shrnutí analýzy: {analyzed_count}/{total_pages} stránek zpracováno.[/cyan]")
    console.print(f"[cyan]Nalezeno {len(analyzed_programs)} programů před filtrací, {len(final_results)} relevantních po filtraci.[/cyan]")
    
    if error_count > 0:
        console.print(f"[dim yellow]({error_count} stránek se nepodařilo analyzovat)[/dim yellow]")
    
    # If nothing found, add a fallback message
    if not final_results and analyzed_count > 0:
        console.print("[yellow]Žádné programy nebyly označeny jako relevantní po filtraci. Zkuste upravit preference nebo rozšířit hledání.[/yellow]")
    
    return final_results


def filter_results_by_preferences(results, preferences):
    if not results:
        return []
        
    filtered = []
    
    # Normalize preferences
    pref_location = (preferences.get("location") or "").lower().strip()
    pref_level = (preferences.get("level") or "").lower().strip()
    
    # University city mapping - include full names and abbreviations
    uni_cities = {
        "masarykova univerzita": "brno",
        "muni": "brno",
        "vut": "brno",
        "vysoké učení technické": "brno",
        "mendelova univerzita": "brno",
        "mendelu": "brno",
        "univerzita obrany": "brno",
        "jamu": "brno",
        "janáčkova akademie": "brno",
        
        "univerzita karlova": "praha",
        "čvut": "praha",
        "české vysoké učení technické": "praha",
        "vše": "praha",
        "vysoká škola ekonomická": "praha",
        "čzu": "praha",
        "česká zemědělská univerzita": "praha",
        "všcht": "praha",
        "vysoká škola chemicko-technologická": "praha",
        "policejní akademie": "praha",
        
        "všb": "ostrava",
        "technická univerzita ostrava": "ostrava",
        "ostravská univerzita": "ostrava",
        
        "univerzita palackého": "olomouc",
        "upol": "olomouc",
        
        "západočeská univerzita": "plzeň",
        "zčul": "plzeň",
        
        "technická univerzita v liberci": "liberec",
        "tul": "liberec",
        
        "univerzita pardubice": "pardubice",
        
        "univerzita hradec králové": "hradec králové",
        "uhk": "hradec králové",
        
        "univerzita tomáše bati": "zlín",
        "utb": "zlín",
        
        "jihočeská univerzita": "české budějovice",
        "jču": "české budějovice",
        "všte": "české budějovice",
        
        "slezská univerzita": "opava", 
        "ujep": "ústí nad labem",
        "univerzita jana evangelisty purkyně": "ústí nad labem"
    }

    ignored_locations = ["kdekoliv", "none", "", "čr", "česká republika", "Kdekoliv", "Česká republika", "Česká Republika", "ČR"]

    for res in results:
        keep = True
        reason_drop = ""
        
        # 0. Fill missing Duration if Degree is known (Heuristic)
        deg = res.get("degree", "").lower()
        dur = res.get("duration", "").lower()
        if (not dur or dur in ["n/a", "nezjištěno"]) and deg and deg not in ["n/a", "nezjištěno"]:
            if "bc" in deg:
                res["duration"] = "3 roky (standard)"
            elif "mgr" in deg or "ing" in deg:
                res["duration"] = "2 roky (standard)"
            elif "ph" in deg:
                res["duration"] = "4 roky (standard)"

        # 1. Location Filtering
        if pref_location and pref_location not in ignored_locations:
            uni_name = res.get("university", "").lower()
            
            # Check explicit city in university name (often not there) or map from known unis
            city_match = False
            
            # Direct check if city is in uni name (e.g. "Univerzita Pardubice")
            if pref_location in uni_name:
                city_match = True
            
            if not city_match:
                for key, city in uni_cities.items():
                    if key in uni_name:
                        if city == pref_location:
                            city_match = True
                        else:
                            pass 
                        break
            
            detected_city = None
            for key, city in uni_cities.items():
                if key in uni_name:
                    detected_city = city
                    break
            
            if detected_city and detected_city != pref_location:
                keep = False
                reason_drop = f"Lokace ({detected_city} != {pref_location})"
        
        if not keep:
            # console.print(f"[dim red]Filtr: Vyřazuji {res['program_name']} - {reason_drop}[/]")
            continue

        # 2. Degree Filtering
        if pref_level and pref_level not in ignored_locations:
            prog_degree = res.get("degree", "").lower()
            
            # Map user pref to standardized
            target_deg = None
            if "bakalář" in pref_level: target_deg = "bc."
            elif "magister" in pref_level or "magistr" in pref_level: target_deg = "mgr." # Could be Mgr. or NMgr.
            elif "doktor" in pref_level: target_deg = "ph.d."
            
            # Map program degree
            # Accepted variants
            is_match = False
            if target_deg == "bc.":
                if "bc" in prog_degree or "bakalář" in prog_degree or "bachelor" in prog_degree: is_match = True
            elif target_deg == "mgr.":
                if "mgr" in prog_degree or "magist" in prog_degree or "master" in prog_degree or "inženýr" in prog_degree or "ing." in prog_degree: is_match = True
            elif target_deg == "ph.d.":
                if "phd" in prog_degree or "ph.d" in prog_degree or "doktor" in prog_degree: is_match = True
                
            if target_deg and not is_match and prog_degree != "nezjištěno" and prog_degree != "n/a":
                keep = False
                reason_drop = f"Typ studia ({prog_degree} != {pref_level})"
        
        if keep:
            filtered.append(res)
            
    return filtered


def create_fallback_result(item):
    import re
    
    title = item.get('title', 'Neznámý program')
    content = item.get('content', '') or item.get('body', '') or ''
    url = item.get('href', '')
    metadata = item.get('metadata', {})
    
    # Extract university name from URL or title
    university = "Neznámá"
    uni_patterns = {
        r'muni\.cz|masaryk': 'Masarykova univerzita',
        r'cvut\.cz|čvut': 'ČVUT v Praze',
        r'cuni\.cz|karlov': 'Univerzita Karlova',
        r'vutbr\.cz|vut\.cz': 'VUT v Brně',
        r'vsb\.cz|technická univerzita ostrava|báňsk': 'VŠB-TU Ostrava',
        r'upol\.cz|palack': 'Univerzita Palackého',
        r'zcu\.cz|západočesk': 'Západočeská univerzita',
        r'ujep\.cz|ústí nad labem': 'UJEP Ústí nad Labem',
        r'mendelu\.cz|mendel': 'Mendelova univerzita',
        r'vse\.cz|ekonomick': 'VŠE Praha',
        r'utb\.cz|tomáš': 'UTB Zlín',
        r'tul\.cz|liberec': 'TU Liberec',
        r'uhk\.cz|hradec': 'UHK Hradec Králové',
        r'osu\.cz|ostravská univerzita': 'Ostravská univerzita',
        r'unob\.cz|obrany': 'Univerzita obrany',
        r'slu\.cz|slezsk': 'Slezská univerzita',
        r'jcu\.cz|jihočesk': 'Jihočeská univerzita',
    }
    
    combined = (url + ' ' + title).lower()
    for pattern, name in uni_patterns.items():
        if re.search(pattern, combined, re.IGNORECASE):
            university = name
            break
    
    # Use pre-extracted metadata first
    degree = metadata.get('degree')
    duration = metadata.get('duration')
    
    # If not in metadata, try regex on content
    search_text = (url + ' ' + title + ' ' + content[:3000]).lower()
    
    if not degree:
        # Prioritize PhD detection first (often mentions Mgr as requirement)
        if re.search(r'doktor|ph\.?d|doctor|\bd-[a-z]{2,4}\b', title, re.IGNORECASE):
            degree = "Ph.D."
        elif re.search(r'navazuj|magist|master|mgr\.|nmgr', title, re.IGNORECASE):
            degree = "Mgr." 
        elif re.search(r'bakalá|bachelor|bc\.', title, re.IGNORECASE):
            degree = "Bc."
        # If not in title, check content with stricter context
        elif re.search(r'doktorsk[ýé]|ph\.?d\.', search_text, re.IGNORECASE):
            degree = "Ph.D."
        elif re.search(r'navazujíc|magistersk', search_text, re.IGNORECASE):
            degree = "Mgr."
        elif re.search(r'bakalářsk', search_text, re.IGNORECASE):
            degree = "Bc."
            
    if not duration:
        # Look for duration patterns
        duration_patterns = [
            (r'délka\s*(?:studia)?\s*[:\-–]\s*(\d+)\s*(rok|let|semestr)', 1, 2),
            (r'standardní\s*doba\s*[:\-]?\s*(\d+)', 1, None),
            (r'(\d+)\s*rok[yů]?(?:\s*studia)?', 1, None),
            (r'(\d)\s*leté', 1, None),
        ]
        
        for pattern_tuple in duration_patterns:
            if len(pattern_tuple) == 3:
                pattern, num_group, unit_group = pattern_tuple
                match = re.search(pattern, search_text, re.IGNORECASE)
                if match:
                    years = match.group(num_group)
                    if unit_group and 'semestr' in match.group(unit_group):
                        years = str(int(years) // 2)
                    duration = f"{years} roky" if years in ['2', '3', '4'] else f"{years} let"
                    break
            else:
                 match = re.search(pattern_tuple[0], search_text, re.IGNORECASE)
                 if match:
                    years = match.group(1)
                    duration = f"{years} roky" if years in ['2', '3', '4'] else f"{years} let"
                    break
    
    if not degree:
        if university != "Neznámá":
            degree = "Bc."
        else:
            degree = "Nezjištěno"
            
    if not duration or duration == "Nezjištěno":
        if degree == "Bc.":
            duration = "3 roky (standard)"
        elif degree == "Mgr.":
            duration = "2 roky (standard)"
        elif degree == "Ph.D.":
            duration = "4 roky (standard)"
        else:
            duration = "Nezjištěno"
    
    # Extract faculty
    faculty = ""
    faculty_patterns = [
        (r'fakulta\s+informatiky', 'Fakulta informatiky'),
        (r'fakulta\s+elektrotechniky', 'Fakulta elektrotechniky'),
        (r'fakulta\s+informačních\s+technologií', 'Fakulta informačních technologií'),
        (r'fakulta\s+aplikovaných\s+věd', 'Fakulta aplikovaných věd'),
        (r'\bfi\b', 'FI'),
        (r'\bfit\b', 'FIT'),
        (r'\bfel\b', 'FEL'),
        (r'\bfav\b', 'FAV'),
        (r'\bfsi\b', 'FSI'),
        (r'\bfekt\b', 'FEKT'),
        (r'fakulta\s+\w+', None),
    ]
    
    for pattern_tuple in faculty_patterns:
        pattern = pattern_tuple[0]
        fixed_name = pattern_tuple[1] if len(pattern_tuple) > 1 else None
        match = re.search(pattern, combined, re.IGNORECASE)
        if match:
            faculty = fixed_name if fixed_name else match.group(0).title()
            break
    
    if faculty:
        university = f"{university} {faculty}"

    # Generate pros based on content analysis
    pros = []
    
    if re.search(r'prax[eií]|praktick|stáž|firma', content, re.IGNORECASE):
        pros.append("Důraz na praxi")
    if re.search(r'zahrani|erasmus|výměn|mobility', content, re.IGNORECASE):
        pros.append("Možnost zahraničního studia")
    if re.search(r'laboratoř|vybaven|modern', content, re.IGNORECASE):
        pros.append("Moderní vybavení")
    if re.search(r'projekt|týmov|skupin', content, re.IGNORECASE):
        pros.append("Projektová výuka")
    if re.search(r'výzkum|věd[ea]|research', content, re.IGNORECASE):
        pros.append("Zapojení do výzkumu")
    if re.search(r'ai|umělá inteligence|machine learning|strojov', content, re.IGNORECASE):
        pros.append("Zaměření na AI/ML")
    if re.search(r'program|software|vývoj|develop', content, re.IGNORECASE):
        pros.append("Programování a vývoj SW")
    if re.search(r'kyberbezpečnost|security|bezpečn', content, re.IGNORECASE):
        pros.append("Kybernetická bezpečnost")
    
    if not pros:
        pros = ["Akreditovaný studijní program"]
    
    # Clean up program name from title
    program_name = title
    # Remove common suffixes
    program_name = re.sub(r'\s*[-|–]\s*(vysoké školy|fakulta|univerzita).*$', '', program_name, flags=re.IGNORECASE)
    program_name = re.sub(r'\s*\[\d{4}/\d{4}\].*$', '', program_name)
    
    # Calculate score based on content quality
    score = 40
    if university != "Neznámá":
        score += 15
    if degree != "Nezjištěno":
        score += 10
    if duration != "Nezjištěno":
        score += 10
    if len(pros) > 2:
        score += 10
    if len(content) > 500:
        score += 10
    
    # Extract description from content
    description = ""
    if content:
        # Get first meaningful paragraph
        sentences = re.split(r'[.!?]\s+', content[:1000])
        for sent in sentences[:3]:
            if len(sent) > 30 and not re.search(r'cookie|přihlásit|registr', sent, re.IGNORECASE):
                description = sent[:200]
                if not description.endswith('.'):
                    description += '...'
                break
    
    if not description:
        description = f"Studijní program na {university}. Klikněte na odkaz pro více informací."
    
    return {
        "is_relevant": True,
        "university": university,
        "faculty": faculty,
        "program_name": program_name[:80],
        "degree": degree,
        "duration": duration,
        "description": description,
        "pros": pros[:4],
        "cons": ["Detaily ověřte na webu školy"],
        "match_score": min(score, 85),
        "match_reason": f"Extrahováno z obsahu stránky ({university})",
        "url": url,
        "source_title": title
    }

