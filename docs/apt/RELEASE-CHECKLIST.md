# AudioMason – APT Release Checklist (Maintainer)

This checklist defines the **only supported procedure** for publishing a new AudioMason version to the signed APT repository.

---

## 0. Preconditions

- clean git worktree
- branch: main
- correct GPG signing key available
- public key published as: docs/apt/audiomason.gpg.asc
- GitHub Pages enabled for this repository

---

## 1. Build the package

    cd ~/apps/audiomason || exit 1
    dpkg-buildpackage -us -uc

Expected artifacts:
- audiomason_*_all.deb
- .changes
- .buildinfo

---

## 2. Place package into pool/

    mkdir -p docs/apt/pool/main/a/audiomason
    mv ../audiomason_*_all.deb docs/apt/pool/main/a/audiomason/

---

## 3. Regenerate APT metadata

    cd docs/apt || exit 1

    apt-ftparchive packages pool > dists/stable/main/binary-all/Packages
    gzip -kf dists/stable/main/binary-all/Packages

    apt-ftparchive release dists/stable > dists/stable/Release
    gpg --clearsign -o dists/stable/InRelease dists/stable/Release
    gpg -abs -o dists/stable/Release.gpg dists/stable/Release

---

## 4. Local validation (mandatory)

    grep -n '^Version:' dists/stable/main/binary-all/Packages

Verify:
- new version is present
- InRelease, Release, Release.gpg exist

---

## 5. Commit and push

    cd ~/apps/audiomason || exit 1
    git add docs/apt
    git commit -m "APT: publish new package version"
    git push

---

## 6. GitHub Pages verification (mandatory)

On a clean system:

    sudo apt update
    sudo apt install audiomason

Expected:
- no GPG warnings
- no 404 errors
- package installs or upgrades correctly

---

## 7. Post-release sanity check

    audiomason --help

---

## Failure policy

If any step fails:
- stop
- fix the issue
- restart from step 3

Do not partially publish.
