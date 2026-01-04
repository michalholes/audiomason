# 🧭 AudioMason – AUTHORITATIVE HANDOFF / AI CONTRACT (v4)

TENTO DOKUMENT JE AUTHORITATIVE PRE PRACU NA PROJEKTE AudioMason.
PLATI PRE VSETKY IMPLEMENTACNE CHATY, AK ISSUE HANDOFF NEPOVIE INAK.
AK JE ROZPOR: EXPLICITNY ISSUE HANDOFF MA PREDNOST, INAK PLATI TENTO CONTRACT.

Komunikacia: slovensky (ak nepovies inak).
Kod/prikazy: vzdy v code blockoch.

---

## 1) Runtime a prostredie

AudioMason vzdy bezi vo venv `.venv`. Ked sa uvadza venv, MUSI sa uviest aktivacia aj deaktivacia:

```sh
. .venv/bin/activate
deactivate
```

---

## 2) Scope a styl prace

- Implementovat iba to, co je explicitne pozadovane v handoffe.
- ❌ Ziadne refaktory mimo nutneho zasahu.
- ❌ Ziadne "bonus" zmeny.
- ❌ Ziadne manualne edit kroky.
- ❌ Ziadne partial fixes.

---

## 3) Authoritative files (FAIL FAST)

- Vlozeny / uploadnuty subor je AUTHORITATIVE.
- Ak chyba potrebny subor → FAIL FAST a vyziadat ho.
- Nehadat, nevymyslat kod.

---

## 4) Patchovanie (NEVYJEDNAVATELNE)

### 4.1 Povolený format

- ❌ NO diff patches
- ❌ NO heredoc pre patch kod
- ❌ NO inline manualne edit pokyny
- ✅ IBA deterministicky Python patch skript:

```
/home/pi/apps/patches/issue_<N>.py
```

### 4.2 Patch skript MUST

- anchor checks
- idempotency
- fail-fast
- post-edit assertions

### 4.3 Jeden issue = jeden patch skript

- Presne 1 skript: `/home/pi/apps/patches/issue_<N>.py`

### 4.4 Miesto a spustanie patchov (MANDATORY)

- Patch skripty sa **UKLADAJU** do:
  `/home/pi/apps/patches`
- Patch skripty sa **SPUSTAJU VZDY ODTIAL**.
- Nevykonavat patch z inej cesty.

### 4.5 Distribucia patchov

- Patch skripty sa dodavaju ako DOWNLOAD.
- Inline patch iba na vyslovnu ziadost pouzivatela.

### 4.6 Po uspechu

- Patch skript sa po uspechu MUSI zmazat:
  `rm /home/pi/apps/patches/issue_<N>.py`

---

## 5) Testy a git bezpecnost (INVARIANT)

### 5.1 Invariant

- Ziadny git add/commit/push pred uspesnymi testami.
- Pred KAZDYM push MUSI byt `python -m pytest -q &&`.

### 5.2 Kanonicka sekvencia (POVINNA)

```sh
python /home/pi/apps/patches/issue_<N>.py rm /home/pi/apps/patches/issue_<N>.py python -m pytest -q && git add -A && git commit -m "<message>" && python -m pytest -q && git push
```

---

## 6) GitHub issues

- Issue sa NIKDY nezatvara automaticky.
- Zatvaranie vyhradne po schvaleni pouzivatela.
- Closing comment MUSI obsahovat commit SHA(cka).

Helper:

```sh
cd /home/pi/apps/audiomason && . .venv/bin/activate && git log --oneline -10 && echo && echo "Skopiruj sem SHA(cka) z hore uvedeneho logu, ktore patria k #<ISSUE>, potom spusti tento prikaz:" && echo && echo "gh issue close <ISSUE> -R michalholes/audiomason -c \"Resolved: <summary>.\n\nCommits:\n- <SHA1> <subject>\n- <SHA2> <subject>\"" && deactivate
```

---

## 7) Release safety

Pri zmene verzie / pyproject.toml vzdy:

```sh
. .venv/bin/activate
pip uninstall -y audiomason
pip install -e .
deactivate
```

---

## 8) Postup v chate

1. Potvrdit handoff.
2. Vyziadat authoritative subory.
3. FAIL FAST, ak nieco chyba.
4. Dodat patch ako download.
5. Dodat jeden code block s workflow.
6. STOP (issue nezatvarat).
