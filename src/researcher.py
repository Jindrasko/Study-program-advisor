from ddgs import DDGS
import requests
from bs4 import BeautifulSoup
from rich.console import Console
import time

console = Console()


def build_search_query(preferences):
    parts = []
    
    # Core terms
    field = preferences.get("field", "").strip()
    if field and field.lower() not in ["", "none", "kdekoliv"]:
        parts.append(field)
    
    specialization = preferences.get("specialization", "").strip()
    if specialization and specialization.lower() not in ["", "none"]:
        parts.append(specialization)
    
    level = preferences.get("level", "").strip()
    if level and level.lower() not in ["", "none", "kdekoliv"]:
        level_map = {
            "bakalářské": "bakalářské studium",
            "magisterské": "magisterské navazující studium",
            "doktorské": "doktorské PhD studium"
        }
        parts.append(level_map.get(level.lower(), level))
    
    language = preferences.get("language", "").strip()
    if language and language.lower() not in ["", "none", "čeština"]:
        parts.append(f"výuka v {language}")
    
    location = preferences.get("location")
    if location and str(location).strip().lower() not in ["", "none", "kdekoliv"]:
        parts.append(str(location))
    
    # Default context
    if not parts:
        parts = ["vysokoškolské studium", "informatika"]
    
    query = " ".join(parts) + " univerzita fakulta ČR"
    
    return query


def build_alternative_queries(preferences):
    queries = []
    
    field = (preferences.get("field") or "Informatika").strip()
    level = (preferences.get("level") or "bakalářské").strip()
    location = (preferences.get("location") or "").strip()
    
    # Query 1: Direct university search
    q1 = f"{field} studijní program {level} univerzita"
    if location and location.lower() != "kdekoliv":
        q1 += f" {location}"
    queries.append(q1)
    
    # Query 2: Faculty search
    q2 = f"fakulta {field.lower()} {level} studium přijímací řízení"
    queries.append(q2)
    
    # Query 3: Specific Czech universities - targeted
    if location.lower() == "brno":
        q3 = f"{field} studium fakulta VUT MUNI MENDELU UNOB"
    elif location.lower() == "praha":
        q3 = f"{field} studium fakulta ČVUT UK VŠE ČZU"
    elif location.lower() == "ostrava":
        q3 = f"{field} studium fakulta VŠB OSU"
    else:
        q3 = f"{field} ČVUT MFF UK VUT MUNI fakulta"
    
    queries.append(q3)
    
    # Query 4: Broad site search if specific city
    if location and location.lower() not in ["", "kdekoliv"]:
        q4 = f"{field} {level} studium {location}"
        queries.append(q4)
    
    return queries


def search_programs(preferences, max_results=15):
    all_results = []
    seen_urls = set()
    
    queries = build_alternative_queries(preferences)
    ddgs = DDGS()
    
    max_results = 15
    
    for query_idx, query in enumerate(queries):
        if len(all_results) >= max_results:
            break
            
        console.print(f"[dim]Vyhledávací dotaz {query_idx + 1}: {query}[/dim]")
        
        try:
            remaining = max_results - len(all_results)
            
            # DDGS API
            search_results = ddgs.text(
                query, 
                region='cs-cz',
                max_results=min(remaining + 5, 20)
            )
            
            for r in search_results:
                url = r.get("href", "") or r.get("link", "")
                
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                
                if should_skip_url(url):
                    continue
                
                if ".cz" in url.lower():
                    all_results.insert(0, {
                        "title": r.get("title", "Neznámý titulek"),
                        "href": url,
                        "body": r.get("body", "") or r.get("snippet", "")
                    })
                else:
                    all_results.append({
                        "title": r.get("title", "Neznámý titulek"),
                        "href": url,
                        "body": r.get("body", "") or r.get("snippet", "")
                    })
                
                if len(all_results) >= max_results:
                    break
                    
        except Exception as e:
            console.print(f"[yellow]Vyhledávání '{query[:50]}...' selhalo: {e}[/]")
            continue
        
        # Small delay between queries
        if query_idx < len(queries) - 1:
            time.sleep(0.5)
    
    if not all_results:
        console.print("[yellow]Žádné výsledky z primárního vyhledávání. Zkouším záložní dotaz...[/]")
        try:
            fallback_query = "informatika studium fakulta site:cuni.cz OR site:cvut.cz OR site:muni.cz OR site:vutbr.cz"
            search_results = ddgs.text(fallback_query, region='cs-cz', max_results=max_results)
            for r in search_results:
                url = r.get("href", "") or r.get("link", "")
                if url:
                    all_results.append({
                        "title": r.get("title", "Neznámý titulek"),
                        "href": url,
                        "body": r.get("body", "") or r.get("snippet", "")
                    })
        except Exception as e:
            console.print(f"[red]Záložní vyhledávání také selhalo: {e}[/]")
    
    return all_results[:max_results]


def should_skip_url(url):
    if not url:
        return True
    
    skip_domains = [
        "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
        "youtube.com", "wikipedia.org", "wikipedie.org",
        "novinky.cz", "idnes.cz", "seznam.cz", "aktualne.cz",
        "jobs.cz", "prace.cz", "profesia.cz"
    ]
    
    url_lower = url.lower()
    for domain in skip_domains:
        if domain in url_lower:
            return True
    
    return False


def fetch_page_content(url):
    if not url:
        return {"text": "", "metadata": {}}
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'cs,en-US;q=0.7,en;q=0.3',
        }
        
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        
        if response.encoding is None:
            response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        metadata = extract_program_metadata(soup)
        
        for element in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "iframe"]):
            element.decompose()
        
        main_content = None
        for selector in ['main', 'article', '.content', '#content', '.main-content', '.program-detail', '.study-program']:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        if main_content:
            text = main_content.get_text(separator=' ', strip=True)
        else:
            text = soup.get_text(separator=' ', strip=True)
        
        text = ' '.join(text.split())
        
        return {
            "text": text[:15000] if text else "",
            "metadata": metadata
        }
        
    except requests.exceptions.Timeout:
        console.print(f"[dim yellow]Timeout při stahování: {url[:60]}...[/dim yellow]")
        return {"text": "", "metadata": {}}
    except requests.exceptions.RequestException as e:
        console.print(f"[dim red]Nepodařilo se stáhnout {url[:50]}...: {str(e)[:30]}[/dim red]")
        return {"text": "", "metadata": {}}
    except Exception as e:
        console.print(f"[dim red]Neočekávaná chyba: {str(e)[:50]}[/dim red]")
        return {"text": "", "metadata": {}}


def extract_program_metadata(soup):
    import re
    metadata = {}
    
    degree_keywords = ['typ studia', 'typ programu', 'stupeň', 'titul', 'forma studia', 'druh studia', 'studijní program']
    duration_keywords = ['délka studia', 'délka', 'doba studia', 'standardní doba', 'trvání', 'počet semestrů', 'roky']
    # Search in tables
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True).lower()
                value = cells[1].get_text(strip=True)
                
                for kw in degree_keywords:
                    if kw in label:
                        metadata['degree_raw'] = value
                        break
                        
                for kw in duration_keywords:
                    if kw in label:
                        metadata['duration_raw'] = value
                        break
    
    # Search in definition lists (dl/dt/dd)
    for dl in soup.find_all('dl'):
        dts = dl.find_all('dt')
        dds = dl.find_all('dd')
        for dt, dd in zip(dts, dds):
            label = dt.get_text(strip=True).lower()
            value = dd.get_text(strip=True)
            
            for kw in degree_keywords:
                if kw in label:
                    metadata['degree_raw'] = value
                    break
                    
            for kw in duration_keywords:
                if kw in label:
                    metadata['duration_raw'] = value
                    break
    # Search in labeled elements
    for elem in soup.find_all(['div', 'span', 'p', 'li']):
        text = elem.get_text(strip=True).lower()
        
        degree_match = re.search(r'(typ\s*(studia|programu)?|stupeň|titul)\s*[:\-–]\s*([^\n\r,]{3,30})', text, re.IGNORECASE)
        if degree_match and 'degree_raw' not in metadata:
            metadata['degree_raw'] = degree_match.group(3).strip()
        
        duration_match = re.search(r'(délka|doba|trvání)\s*(studia)?\s*[:\-–]\s*(\d+\s*(rok|let|semestr)[^\n\r,]{0,20})', text, re.IGNORECASE)
        if duration_match and 'duration_raw' not in metadata:
            metadata['duration_raw'] = duration_match.group(3).strip()
        
        if 'duration_raw' not in metadata:
            dur_standalone = re.search(r'(\d)\s*(roky?|let[áý]?|semestr)', text)
            if dur_standalone:
                num = dur_standalone.group(1)
                unit = dur_standalone.group(2)
                if 'semestr' in unit:
                    num = str(int(num) // 2) if int(num) > 1 else num
                metadata['duration_raw'] = f"{num} roky" if num in ['2', '3', '4'] else f"{num} let"
    
    if 'degree_raw' in metadata:
        raw = metadata['degree_raw'].lower()
        if 'bakalá' in raw or 'bachelor' in raw or 'bc' in raw:
            metadata['degree'] = 'Bc.'
        elif 'magist' in raw or 'master' in raw or 'mgr' in raw or 'navazuj' in raw or 'inženýr' in raw:
            metadata['degree'] = 'Mgr.'
        elif 'doktor' in raw or 'phd' in raw or 'ph.d' in raw:
            metadata['degree'] = 'Ph.D.'
    
    if 'duration_raw' in metadata:
        raw = metadata['duration_raw']
        dur_match = re.search(r'(\d+)', raw)
        if dur_match:
            years = dur_match.group(1)
            if 'semestr' in raw.lower():
                years = str(int(years) // 2)
            metadata['duration'] = f"{years} roky" if years in ['2', '3', '4'] else f"{years} let"
    
    return metadata

