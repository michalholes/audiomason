# 🧭 AudioMason – AUTHORITATIVE HANDOFF / AI CONTRACT (v3)

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
- ❌ Ziadne manualne edit kroky typu "otvor subor a zmen X".
- ❌ Ziadne partial fixes.
- Minimalny zasah, ktory splni acceptance criteria.

---

## 3) Authoritative files (FAIL FAST)

- Ak pouzivatel vlozi alebo uploadne subor/snippet, je AUTHORITATIVE (ma prednost pred repo stavom).
- Ak spravne riesenie zavisi od suboru, ktory nebol poskytnuty:
  - **FAIL FAST** a vyziadat si ho
  - nehadat / nevymyslat kod

---

## 4) Patchovanie (NEVYJEDNAVATELNE)

### 4.1 Povolený format

- ❌ NO diff patches
- ❌ NO heredoc pre patch kod
- ❌ NO inline manualne edit pokyny
- ✅ IBA deterministicky Python patch skript:

`tools/patches/issue_<N>.py`

### 4.2 Patch skript MUST

- anchor checks (overit kontext pred editom)
- idempotency (bezpecne opakovane spustenie)
- fail-fast s jasnou chybou
- post-edit assertions (overit, ze zmena existuje)

### 4.3 Jeden issue = jeden patch skript

- Presne 1 skript: `tools/patches/issue_<N>.py`

### 4.4 Distribucia patchov (preferencia)

- Patch skripty sa maju dodavat ako DOWNLOAD.
- Ak download nie je dostupny v danom prostredi:
  - patch sa poskytne v chate iba na vyslovnu ziadost pouzivatela.

### 4.5 Po uspechu

- Po uspesnom patchnuti a uspesnych testoch sa patch skript MUSI zmazat:

```sh
rm tools/patches/issue_<N>.py
```

---

## 5) Testy a git bezpecnost (INVARIANT)

### 5.1 Invariant

- Ziadny `git add`, `git commit` ani `git push` NESMIE prebehnut, pokial nepresli testy.
- Pred KAZDYM `git push` MUSI byt `python -m pytest -q &&` v tej istej retazi.

### 5.2 Kanonicka sekvencia (POVINNA)

Vsetko vzdy v jednom code blocku:

```sh
python tools/patches/issue_<N>.py rm tools/patches/issue_<N>.py  python -m pytest -q && git add -A && git commit -m "<message>" && python -m pytest -q && git push
```

---

## 6) GitHub issues (STRICT)

### 6.1 Opening issues

- Otvaranie issue vyhradne cez `gh`.
- Pre dlhe bodies preferuj:
  - `gh issue create/edit -F - <<'EOF' ... EOF`
  - (Vynimka: heredoc je zakazany pre PATCH kod, nie pre `gh` body.)

### 6.2 Closing issues

- ❌ Nikdy nezatvarat issue automaticky.
- ❌ Nikdy nezatvarat issue v patch skripte.
- Po push: ZASTAVIT a cakat na explicitne schvalenie pouzivatela.
- Closing comment MUSI obsahovat commit SHA(cka) + subject(y).

### 6.3 Povinny helper na closing (template)

```sh
cd /home/pi/apps/audiomason && . .venv/bin/activate && git log --oneline -10 && echo && echo "Skopiruj sem SHA(cka) z hore uvedeneho logu, ktore patria k #<ISSUE>, potom spusti tento prikaz:" && echo && echo "gh issue close <ISSUE> -R michalholes/audiomason -c "Resolved: <short summary>.

Commits:
- <SHA1> <subject>
- <SHA2> <subject>"" && deactivate
```

---

## 7) Release / version bump safety

Ak sa meni verzia alebo `pyproject.toml`, po zmene vzdy spravit dev reinstall:

```sh
. .venv/bin/activate
pip uninstall -y audiomason
pip install -e .
deactivate
```

---

## 8) Notices (ak sa pisu)

Ak pouzivatel ziada "published notices":
- pisat po anglicky
- pouzivat straight apostrophes
- davat do code blocku

---

## 9) Ocakavany postup v chate

1. Potvrdit handoff/contract (slovensky).
2. Zoznam potrebnych authoritative suborov; ak chybaju -> FAIL FAST.
3. Dodat patch ako download (ak mozne).
4. Dodat jeden code block s kanonickou sekvenciou.
5. Po push STOP (issue nezatvarat).
