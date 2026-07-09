Feature: Ctrl+G one-step undo in import preflight

- During interactive PREPARE prompts, pressing Ctrl+G and Enter performs a one-step undo.
- Works for both text and yes/no questions:
  - cover -> goes back to the book title
  - title -> goes back to author (then to publish/wipe if needed)
  - clean_stage -> goes back to publish/wipe
- Non-interactive runs (`--yes`) and disabled prompts are unchanged.

Implementation notes:
- Ctrl+G (BEL, \x07) detection added to `util.prompt` and `util.prompt_yes_no`.
- Minimal local loops added in `import_flow.py` to handle step-back without growing PROCESS logic.
