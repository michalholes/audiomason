# 🧭 AudioMason – AUTHORITATIVE HANDOFF / AI CONTRACT (v21)
## 🔒 AUTHORITATIVE SCOPE

TENTO DOKUMENT JE AUTHORITATIVE PRE PRACU NA PROJEKTE AudioMason
A PLATI PRE VSETKY IMPLEMENTACNE CHATY BEZ VYNIMKY.

ISSUE HANDOFF NESMIE BYT V ROZPORE S TYMTO CONTRACTOM.
ISSUE HANDOFF MOZE CONTRACT IBA SPRESNIT (DOPLNIT DETAILY),
NIKDY HO NESMIE OSLABIT ANI OBIST.

AK EXISTUJE ROZPOR:
- PLATI TENTO CONTRACT,
- ISSUE HANDOFF SA POVAZUJE ZA CHYBNY.
VYNIMKU MOZE POVOLIT IBA POUZIVATEL EXPLICITNE.

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
AUTHORITATIVE FILES: Vsetky subory uploadnute v tomto chate su AUTHORITATIVE; ak existuje viac verzii, plati POSLEDNA uploadnuta verzia.
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

### 2.1 Pravidla pre nove funkcie a opravy existujucich (POVINNE)

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

- ZIP / ARCHIV je AUTHORITATIVE vstup, ale chat NESMIE predstierat analyzu.
  Ak je dodany ZIP, chat MUSI spravit jedno z tychto:
  A) vypisat konkretne subory (cesty v repo) z toho archivu, ktore budu editovane/pouzite,
     a nasledne dodat patch alebo konkretnu analyzu tychto suborov,
  B) alebo fail-fast a vyziadat si konkretne subory ako uploady.
- Ak chat nevie alebo nemoze realne precitat/analyzovat ZIP,
  MUSI fail-fast (nesmie slubovat "rozbalim a zanalyzujem").

- Ak pouzivatel v akomkolvek chate uploadne subor
  (alebo ho explicitne oznaci ako aktualny),
  je tento subor AUTOMATICKY AUTHORITATIVE.

- Ak existuje viac verzii toho isteho suboru,
  **AUTHORITATIVE je VZDY POSLEDNA uploadnuta verzia.**
  Starsie verzie su AUTOMATICKY NEPLATNE a NESMU byt pouzite.

- Chat sa NESMIE pytat, ktora verzia je authoritative,
  ani ziadat potvrdenie.

- V pripade rozporu ma posledna uploadnuta verzia
  ABSOLUTNU PREDNOST pred pamatou, repo stavom
  aj predoslymi odpovedami chatu.

- Ak potrebny subor nebol uploadnuty,
  chat MUSI fail-fast a vyziadat si ho.


## 4) Patchovanie (KRITICKE, NEVYJEDNAVATELNE)

### 4.1 Povolený sposob zmien

- ❌ Ziadne diff patches
- ❌ Ziadne heredoc pre patch kod (<<EOF, <<PY)
- ❌ Ziadne manualne edit pokyny
- ❌ Ziadne shell hacky
- ✅ JEDINY povoleny sposob: deterministicky Python patch skript

### 4.2 Vlastnosti patch skriptu (MUST)

- Patch skript NESMIE hardcodovat repo root na `/home/pi/src` ani na ziadnu inu pevnu cestu.
- Repo root sa MUSI urcit deterministicky takto (v tomto poradi):
  1) najdi najblizsi rodicovsky adresar (od `cwd`) obsahujuci `pyproject.toml`.
     Tento adresar je repo root.
  2) ak sa `pyproject.toml` nenasiel, fail-fast.
- Patch skript MUSI pracovat s cestami relativne k repo root (napr. `repo_root / "src/..."`).

- anchor checks
- idempotentny
- fail-fast
- post-edit assertions

### 4.3 Umiestnenie patchov (POVINNE)

- Vsetky subory **dodane chatom**
  (patch skripty, kontrakty na stiahnutie,
  pomocne alebo docasne subory)
  MUSIA byt ulozene v adresari: `/home/pi/apps/patches`.
- Chat NESMIE navrhovat pracu so subormi
  v inych adresaroch.

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

## 4.5 Patch runner (POVINNE)

- Ak ma issue viac patch-runov, kazdy run MUSI byt jasne oznaceny v odpovedi:
  - "RUN 1: code", "RUN 2: docs" (alebo ekvivalent),
  - a commit message MUSI mat zodpovedajuci prefix (napr. `Feat:` vs `Docs:`/`Chore:`).
- Patch pre dokumentaciu NESMIE byt dodany, kym nie je potvrdene,
  ze code-run bol uspesne commitnuty a pushnuty.

- Jeden issue moze mat viac commitov a viac patch-runov.
- Kazdy samostatny patch-run MUSI byt stale dodany/spusteny kanonicky ako: `/home/pi/apps/patches/issue_<N>.py` (runner ho po dobehnuti zmaze).
- Ak chat doda patch pod inym menom (napr. `issue_<N>_docs.py`), MUSI uviest rename + run v jednom code blocku (podla tohto bodu).

- Ak je potrebny rename krok (napr. kvoli sandbox kolizii nazvu), chat MUSI dodat rename + spustenie runnera **v jednom code blocku**, aby pouzivatel mohol vykonat jeden copy-paste.
- Canonicky tvar v takom pripade je:
  ```sh
  mv /home/pi/apps/patches/<DOWNLOADED_FILENAME>.py /home/pi/apps/patches/issue_<N>.py && \
  /home/pi/apps/patches/am_patch.sh <N> "<COMMIT_MESSAGE>"
  ```

- Runner MUSI fail-fast, ak patch nevyprodukuje ziadne zmeny na commit ("nothing to commit" / working tree clean). V takom pripade MUSI vypisat jasnu hlasku "patch produced no changes" a skoncit s nenulovym rc.
- Pri zlyhani patchu alebo testov MUSI byt dovod zlyhania viditelny okamzite (error/traceback alebo jasna chybova hlaska). Chat MUSI po zlyhani hned poziadat o konkretny diagnosticky vystup (napr. relevantny traceback, sed -n rozsah, git diff, pytest output).

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

### 6.0 Jazyk issues (POVINNE)

- Vsetky GitHub issues (title aj body) MUSIA byt napisane po anglicky.


### 6.1 Otvaranie / uprava issues

- Vyhradne cez `gh`.
- Dlhe texty: vyhradne cez `-F <file>` (ziadne heredoc).
  - Priklad: `gh issue create -R michalholes/audiomason -F /path/to/body.md`
  - Priklad: `gh issue edit <N> -R michalholes/audiomason -F /path/to/body.md`

### 6.2 UZATVARANIE ISSUES (EXTRÉMNE STRIKTNE)

- Ak pouzivatel uz explicitne poskytol commit SHA(a) pre issue, chat NESMIE vyzadovat opakovane `git log` kroky len "pre audit". Moze pokracovat rovno na `gh issue close` prikaz s dodanym SHA(a) a subjectom.
- Pred uzavretim issue MUSI byt dokumentacia aktualizovana, ak issue pridava alebo meni spravanie (nova funkcia / oprava funkcie / zmena UX).
  - Minimalne: doplnit zmenu do `docs/FUNCTIONS.md` (single place pre funkcie).
  - Ak sa meni prompt (pridany/odstraneny/upraveny), MUSI byt po testoch a code commite     aktualizovany aj `docs/prompts/catalog.md` podla pravidiel pre prompt katalog.
  - Dokumentacny update moze byt samostatny commit po code commite.

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

## 9) Komunikacia (TVRDE PRAVIDLA)

- STATUS ODPOVEDE SU ZAKAZANE.
  Priklady zakazanych odpovedi: "pokracujem", "idem na to", "patch sa generuje",
  "dalsia sprava bude", "uz to robim", opakovane "OK" bez vysledku.
- Po potvrdeni pouzivatela (napr. "OK", "pokracuj") MUSI byt kazda dalsia odpoved
  IBA jedna z tychto moznosti:
  A) realny vysledok (download patch / konkretna analyza s citaciou suborov / prikazy),
  B) TECHNICKY FAIL-FAST: presny dovod + konkretne subory, ktore chybaju alebo blokator.
- Chat NESMIE slubovat buduce vysledky bez toho, aby ich dodal v tej istej odpovedi.
- Chat NESMIE opakovane vyzyvat pouzivatela na "OK"; ak pouzivatel napise "OK", chat kona.

- Scope chatu urcuje pouzivatel explicitne v prvej sprave (napr. "Tento chat je implementacny.").
- Chat NESMIE spochybnovat scope ani navrhovat presun do ineho chatu, pokial pouzivatel vyslovene nepoziada o presun.
- Ak existuje konflikt medzi implicitnymi pravidlami/pamatou a explicitnym scope pouzivatela, plati explicitny scope pouzivatela.
- Ak pouzivatel da explicitne "OK", "pokracuj" alebo ekvivalent, chat NESMIE ziadat dalsie potvrdenie planu a MUSI prejst rovno na dalsi vykonavaci krok.
- Chat NESMIE klast overovacie otazky, ak odpoved vyplyva z contractu alebo issue zadania.

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

## 11) Dokumentacia (POVINNE)

- Text v issue handoffe typu "bez docs zmien" znamena iba:
  "nerobit docs pocas implementacie kodu".
  NEZNAMENA to vynimku z povinnosti aktualizovat dokumentaciu pred uzavretim issue.
  Vynimku moze povolit iba pouzivatel explicitne.

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

## 12) Prompt catalog update rules (POVINNE)

### 🔒 Zavazne pravidlo pre `docs/prompts/catalog.md`

- Katalog promptov (`docs/prompts/catalog.md`) MUSI ostat konzistentny s aktualnym stavom vetvy `main`.

- Katalog promptov MUSI byt aktualizovany IBA PO:
  1. uspesnom otestovani zmien (`python -m pytest -q`),
  2. commitnuti zmeny, ktora prompt meni / pridava / odstraňuje.

- Aktualizacia katalogu je sucastou uzatvarania issue, nie jeho priebehu.

### Prakticky dosledok

- Implementacne chaty MUSIA postupovat v poradi:
  1. kod + testy + commit,
  2. aktualizacia `docs/prompts/catalog.md`,
  3. dokumentacny commit (samostatny, alebo v tom istom, ak to issue vyslovne povoľuje).

- Katalog promptov NESMIE byt aktualizovany pred tym, nez je zmena realne pritomna v `main`.
