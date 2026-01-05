# 🧭 AudioMason – AUTHORITATIVE HANDOFF / AI CONTRACT (v13)
TENTO DOKUMENT JE AUTHORITATIVE PRE PRACU NA PROJEKTE AudioMason.
PLATI PRE VSETKY IMPLEMENTACNE CHATY, AK ISSUE HANDOFF NEPOVIE INAK.
AK JE ROZPOR: EXPLICITNY ISSUE HANDOFF MA PREDNOST, INAK PLATI TENTO CONTRACT.

Komunikacia: slovensky (ak nepovies inak).
Kod/prikazy: vzdy v code blockoch.

---

## 0) Povinny zaciatok KAZDEHO handoffu (DOSLOVNE)

KAZDY novy issue chat MUSI zacat tymto blokom (doslovne):

```text
AUTHORITATIVE: Tento handoff sa riadi pravidlami v HANDOFF_CONTRACT.md ulozenom v Project Files.
V pripade konfliktu ma HANDOFF_CONTRACT.md absolutnu prednost.
```

- Ziadny handoff bez tohto bloku.
- Ziadna parafraza.
- Ziadne vynimky.

---

## 1) Runtime a prostredie

AudioMason vzdy bezi vo venv `.venv`. Ked sa uvadza venv, MUSI sa uviest aktivacia aj deaktivacia:

```sh
. .venv/bin/activate
deactivate
```

---

## 2) Scope a styl prace (STRICT)

### 2.1 Pravidla pre nove funkcie a opravy existujucich (MANDATORY)

**Ovládanie**

- Kazda nova funkcia alebo oprava MUSI byt ovladatelna:
  - cez CLI (zapnut/vypnut + volitelne urcit cielovy adresar/subor)
  - cez config (zapnut/vypnut + volitelne urcit cielovy adresar/subor)
- **CLI ma vzdy prednost pred configom.**

**Prompt-control kompatibilita**

- Ak k funkcii existuje alebo vznikne interaktivna otazka:
  - MUSI byt vypinatelna cez config,
  - pri vypnuti sa MUSI pouzit deterministicky default,
  - spravanie MUSI byt konzistentne s globalnym prompt-control mechanizmom.

- Implementovat iba to, co je explicitne pozadovane v handoffe.
- ❌ Ziadne refaktory mimo nutneho zasahu.
- ❌ Ziadne "bonus" zmeny.
- ❌ Ziadne manualne edit pokyny.
- ❌ Ziadne partial fixes.
- ❌ Ziadne shell hacky (sed/awk inline prepisy, one-off piped transforms, fragile in-place edits).
- Minimalny zasah, ktory splni acceptance criteria.

---

## 3) Authoritative files (FAIL FAST)

- **Vsetky subory projektu (vratane patch skriptov a suborov poskytovanych chatom)** sa ukladju do adresara: `/home/pi/apps/patches`.
- Tento adresar je kanonicke ulozisko pre vsetky dodane subory.

- Ak pouzivatel vlozi / uploadne subor alebo snippet, je to AUTHORITATIVE pravda.
- Repo stav / pamat / odhady su irelevantne, ak je k dispozicii AUTHORITATIVE subor.
- Ak chyba potrebny subor → FAIL FAST a vyziadat ho.
- Nehadat, nevymyslat kod.

---

## 4) Patchovanie (KRITICKE, NEVYJEDNAVATELNE)

### 4.1 Povolený sposob zmien

- ❌ Ziadne diff patches
- ❌ Ziadne heredoc pre patch kod (<<EOF, <<PY)
- ❌ Ziadne manualne edit pokyny
- ❌ Ziadne shell hacky
- ✅ JEDINY povoleny sposob: deterministicky Python patch skript

### 4.2 Vlastnosti patch skriptu (MUST)

- anchor checks
- idempotentny
- fail-fast
- post-edit assertions

### 4.3 Umiestnenie patchov (MANDATORY)

- Patch skripty sa ukladaju do: `/home/pi/apps/patches`
- **Kazdy patch skript MUSI byt dodany presne pod nazvom a cestou:** `/home/pi/apps/patches/issue_<N>.py` (bez verznych suffixov ako `_v1`, `_v2`, ...).
- Ak chat **nemoze technicky dodat subor** pod kanonickym nazvom (napr. kolizia v sandboxe), **MUSI pred RUN krokom uviest explicitny rename prikaz**, napr.:
  ```sh
  mv issue_60_blabla.py /home/pi/apps/patches/issue_60.py
  ```
- Ak chat doda subor s inym nazvom alebo cestou **bez uvedenia rename kroku**, je to PORUSENIE contractu.
- Jeden issue = jeden skript.

### 4.4 Distribucia patchov

- Patch skripty sa dodavaju ako DOWNLOAD.
- Inline patch iba na vyslovnu ziadost pouzivatela.


---

## 4.5 Patch runner (MANDATORY)

**All patches MUST be executed via the patch runner.  
No inline shell blocks, no ad-hoc commands.**

### Canonical runner command
```sh
/home/pi/apps/patches/am_patch.sh <ISSUE_NUMBER> "<COMMIT_MESSAGE>"
```

### Example
```sh
/home/pi/apps/patches/am_patch.sh 70 "Fix: Opts defaults (make all Opts fields defaulted)"
```

### Runner guarantees
- activates `.venv`
- runs deterministic Python patch script `issue_<N>.py`
- **always deletes the patch script** (success or failure)
- fails fast on patch or test errors
- runs `python -m pytest -q` **before commit**
- runs `python -m pytest -q` **before push**
- commits with the **exact message provided by the chat**
- pushes to the current branch
- prints **commit SHA (short + full)** after successful commit
- **does NOT use `pipefail`** (never kills the parent shell)

### Hard rules
- Patch scripts are **single-use** (never re-run).
- Commit message is **mandatory** and is **always authored by the chat**.
- The user executes the runner command **verbatim**, without modifications.

---

## 5) Git workflow (STRICT)

### 5.1 Zakladne pravidla

- Commit message je povinna a musi byt explicitna.
- Commit message MUSI mat prefix: `Feat:`, `Fix:` alebo `Chore:`.

### 5.2 Test gate (NEPRESTRELITELNE)

- Ziadny `git add`, `git commit` ani `git push` NESMIE prebehnut, pokial nepresli testy.
- Pred KAZDYM `git push` MUSI byt `python -m pytest -q &&` (push nikdy bez testov).


---

## 6) Issue management (GH CLI ONLY)

### 6.0 Jazyk issues (MANDATORY)

- Vsetky GitHub issues (title aj body) MUSIA byt napisane po anglicky.


### 6.1 Otvaranie / uprava issues

- Vyhradne cez `gh`.
- Dlhe texty: vyhradne cez `-F <file>` (ziadne heredoc).
  - Priklad: `gh issue create -R michalholes/audiomason -F /path/to/body.md`
  - Priklad: `gh issue edit <N> -R michalholes/audiomason -F /path/to/body.md`

### 6.2 UZATVARANIE ISSUES (EXTRÉMNE STRIKTNE)

- ❌ ziadne auto-close
- ❌ ziadne uzatvorenie bez schvalenia pouzivatela
- ❌ ziadne "myslim, ze toto su commity"
- SHA vybera VYHRADNE pouzivatel na zaklade `git log --oneline`.

Povinny vzor uzatvarania:

```sh
cd /home/pi/apps/audiomason && . .venv/bin/activate && git log --oneline -10 && echo && echo "Skopiruj sem SHA(cka) z hore uvedeneho logu, ktore patria k #<ISSUE>, potom spusti tento prikaz:" && echo && echo "gh issue close <ISSUE> -R michalholes/audiomason -c \"Resolved: <short summary>.\n\nCommits:\n- <SHA1> <subject>\n- <SHA2> <subject>\"" && deactivate
```

---

## 7) Verzie & pyproject.toml (POVINNE)

Po KAZDOM bumpnuti verzie alebo zasahu do `pyproject.toml` je POVINNE v dev prostredi:

```sh
. .venv/bin/activate
pip uninstall -y audiomason
pip install -e .
deactivate
```

Dovod: `importlib.metadata.version("audiomason")` musi reflektovat realitu.

---

## 8) Beta / release pravidla (STRICT)

- Beta cislo (betaX) sa NEZVYSUJE automaticky.
- Zvysenie verzie je len po rozhodnuti pouzivatela.
- Release workflow je striktne oddeleny od feature prace (nespajat do jedneho "nahodneho" patchu).

---

## 9) Komunikacia (HARD RULES)

- Slovencina (ak pouzivatel vyslovne nepoziada inak).
- Tento projekt = implementacny.
- Ziadna teoria, ziadne eseje.
- Kratke, chirurgicke odpovede.
- Vsetko deterministicke.

---

## 10) Notices (ak sa pisu)

Ak pouzivatel ziada "published notices":
- pisat po anglicky
- pouzivat straight apostrophes
- davat do code blocku

## 11) Dokumentacia (MANDATORY)

- **Kanonicky zoznam vsetkych funkcii projektu AudioMason MUSI byt vedeny v jednom subore:** `docs/FUNCTIONS.md`.
- Tento subor je **single source of truth** pre popis funkcii.
- Popis, vlastnosti a spravanie **vsetkych funkcii** (novych aj upravenych) MUSIA byt zaznamenane v `docs/FUNCTIONS.md`.
- Ak zmena ovplyvnuje:
  - CLI rozhranie,
  - konfiguračne volby,
  - interaktivne otazky / prompt-control,
  - defaultne spravanie,
  → zodpovedajuca cast `docs/FUNCTIONS.md` MUSI byt aktualizovana.
- README, manpage alebo ine dokumenty mozu obsahovat vyber alebo zhrnutie, ale **pravda je vzdy `docs/FUNCTIONS.md`.**
