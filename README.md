# Agent pro výběr studijního programu

CLI agent využívající umělou inteligenci, který vám pomůže najít ten správný vysokoškolský studijní program v České republice.

---

## Přehled

**Agent pro výběr studijního programu** je inteligentní nástroj pro příkazovou řádku, který automatizuje proces hledání informací pro budoucí vysokoškoláky v ČR. Zpracuje vaše osobní preference (obor, specializace, stupeň studia, preferované město, jazyk výuky atd.) a následně:

1. Vyhledá relevantní české studijní programy na internetu pomocí DuckDuckGo.
2. Stáhne a analyzuje obsah nalezených stránek.
3. Využije **Google Gemini AI** k analýze, ohodnocení a seřazení každého programu podle toho, jak dobře odpovídá vašim požadavkům.
4. Zobrazí přehlednou tabulku v terminálu a uloží detailní **Markdown report**.

---

## Použité technologie

| Kategorie | Technologie |
|---|---|
| **Jazyk** | Python 3.10+ |
| **AI Analýza** | Google Gemini API (`google-generativeai`) |
| **Vyhledávání** | DuckDuckGo Search (`ddgs`) |
| **Parsování HTML** | BeautifulSoup4 (`beautifulsoup4`) |
| **HTTP Požadavky** | Requests |
| **UI v terminálu** | Rich (tabulky, barvy, lišty postupu) |
| **Zpracování dat** | Pandas |
| **Správa konfigurace** | python-dotenv (soubor `.env` pro API klíče) |

---

## Funkce

- **Interaktivní nastavení preferencí** – Obor, specializace, kariérní cíle, zaměření (teorie/praxe), lokace, typ studia, jazyk a další specifika.
- **Strategie více vyhledávacích dotazů** – Sestavuje a spouští několik cílených dotazů pro maximální pokrytí výsledků.
- **Chytré filtrování URL** – Vynechává nerelevantní weby (sociální sítě, pracovní portály, zpravodajství).
- **Strukturovaná extrakce metadat** – Získává typ a délku studia z HTML tabulek, seznamů i textu.
- **Analýza pomocí AI** – Model Gemini vyhodnotí každou stránku a vrátí strukturovaný JSON s názvem programu, univerzitou, fakultou, výhodami/nevýhodami a **skóre shody (0–100)**.
- **Záložní mechanismy** – Pokud dojde kvóta API nebo analýza selže, automaticky převezme práci offline extraktor založený na regulárních výrazech.
- **Filtrování podle lokace a typu** – Dodatečné filtrování výsledků podle měst a titulů pomocí mapování českých vysokých škol.
- **Formátovaný výstup** – Seřazená a barevná tabulka výsledků přímo v terminálu.
- **Markdown report** – Všechny detaily uložené do souboru `report.md`.

---

## Požadavky

- Python 3.10 nebo vyšší
- Google AI Studio API klíč

---

## 👥 Autoři

- **xspacek6**
- **xnazarja**
