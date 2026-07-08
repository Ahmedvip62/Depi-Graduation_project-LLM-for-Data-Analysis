# Split Upload Scripts (Windows)

Each teammate uploads **only their own split** of the project to the graduation
repo, committed under their own GitHub identity, with one double-click.

**Target repo:** https://github.com/Ahmedvip62/Depi-Graduation_project-LLM-for-Data-Analysis

> These are Windows Command Prompt (`.cmd`) scripts. The Linux/bash pieces in the
> project (`scripts/*.sh`, the notebook) are only for running the app on a cloud
> GPU — they are **not** how you upload.

## How to run

1. **One person** runs `00_setup.cmd` first. It removes the old unrelated git
   history, creates a clean repo on `main`, and points it at the graduation repo.
2. **Each teammate** then double-clicks (or runs from a terminal) their own file:

   | Script | Owner | Split |
   |--------|-------|-------|
   | `01_ahmed_frontend.cmd`        | Ahmed (Ahmedvip62)     | Frontend — React UI |
   | `02_amir_backend.cmd`          | Amir (amiressam777)    | Backend Core & API + LLM |
   | `03_shahenda_ai_rag.cmd`       | Shahenda (Shahendawael)| AI — Prompting & RAG |
   | `04_doaa_data.cmd`             | Doaa (doaa186)         | Data Engineering |
   | `05_maimamoon_visualization.cmd` | Maimamoon (maimamoon)| Visualization & Reporting |
   | `06_hesham_ml_devops.cmd`      | Hesham                 | ML Prediction + DevOps + Docs |

   Run them **one at a time** — each script pulls the latest, stages only its own
   files, commits under the right name/email, and pushes.

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
