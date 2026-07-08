# Split Upload Scripts (Windows)

Each teammate uploads **only their own split** of the project to the graduation
repo, committed under their own GitHub identity, with one double-click.

**Target repo:** https://github.com/Ahmedvip62/Depi-Graduation_project-LLM-for-Data-Analysis

> These are Windows Command Prompt (`.cmd`) scripts. The Linux/bash pieces in the
> project (`scripts/*.sh`, the notebook) are only for running the app on a cloud
> GPU — they are **not** how you upload.

## How to run

**Does ordering matter? No.** You never wait for anyone. Each script uploads only
*your own* files, so all six can run in any order (even at the same time). The
only rule: run `00_setup.cmd` on your own machine once, before your upload script.

1. **Each teammate** runs `00_setup.cmd` once on their own copy. It's safe — it
   does **not** delete your project files. It just connects git to the graduation
   repo and adopts its current history as the base, so your push is a clean
   fast-forward instead of a conflict.
2. **Then** double-click (or run) your own file:

   | Script | Owner | Split |
   |--------|-------|-------|
   | `01_ahmed_frontend.cmd`        | Ahmed (Ahmedvip62)     | Frontend — React UI |
   | `02_amir_backend.cmd`          | Amir (amiressam777)    | Backend Core & API + LLM |
   | `03_shahenda_ai_rag.cmd`       | Shahenda (Shahendawael)| AI — Prompting & RAG |
   | `04_doaa_data.cmd`             | Doaa (doaa186)         | Data Engineering |
   | `05_maimamoon_visualization.cmd` | Maimamoon (maimamoon)| Visualization & Reporting |
   | `06_hesham_ml_devops.cmd`      | Hesham                 | ML Prediction + DevOps + Docs |

   Each script pulls the latest, stages only its own files, commits under the
   right name/email, and pushes. If two people push at nearly the same moment,
   the second just re-runs — the built-in rebase handles it.

> **If a run "does nothing" / the window flashes shut:** you skipped
> `00_setup.cmd`, so your local copy still had an unrelated git history. Run
> `00_setup.cmd` first, then your upload script. The scripts now pause at the end
> so you can read the result.

## Authentication

- If **Git Credential Manager** is set up (it ships with Git for Windows), a
  login window handles GitHub automatically the first time.
- If not, the script asks for your **GitHub username** and a **Personal Access
  Token** (create one at https://github.com/settings/tokens with the `repo`
  scope). The token is used only for that push and is never saved to a file.

## Notes

- Each script sets `git config user.name` / `user.email` so the commit is
  attributed to the right person.
- Secrets and heavy artifacts (`.env`, `node_modules`, `chroma_data`, `uploads`)
  are excluded via `.gitignore` and never uploaded.
- `_common.cmd` is the shared engine; don't run it directly.
