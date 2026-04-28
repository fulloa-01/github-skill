# 🔧 GitHub & Git Manager — Claude Skill

> Manage your Git repositories through natural conversation with Claude. *Administra tus repositorios de Git conversando con Claude.*

[![Skill Version](https://img.shields.io/badge/version-2.1.0-blue.svg)](./SKILL.md)
[![Language](https://img.shields.io/badge/language-EN%20%7C%20ES-green.svg)](#)
[![Python](https://img.shields.io/badge/python-3.7%2B-yellow.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)](./LICENSE)

**Choose language / Elige idioma:** [🇨🇱 Español](#-español) · [🇬🇧 English](#-english)


---

## 🇨🇱 Español

### Qué es

Un Claude Skill que te permite operar repositorios de Git conversando con Claude. Entiende español e inglés, diagnostica errores comunes, y **siempre pide confirmación antes de hacer algo destructivo**.

```
Tú:     Muéstrame mis proyectos y la rama de cada uno
Claude: ✅ Encontré 3 repositorios:
         📁 web-app     → main           (2 archivos modificados)
         📁 api-server  → develop        (limpio)
         📁 mobile-app  → feature/login  (1 archivo modificado)

Tú:     Resetea todos mis cambios en web-app
Claude: ⚠️  OPERACIÓN DESTRUCTIVA
         Comando: git reset --hard HEAD
         Efecto:  Descarta permanentemente todos los cambios sin confirmar
         Afecta:  src/auth/login.js, src/routes/index.js
         Repo:    /home/tu/projects/web-app

         Escribe SÍ (o YES) para confirmar. Cualquier otra cosa cancela.
```

### Características

- **Lenguaje natural** — funciona en español e inglés, sin necesidad de sintaxis de comandos.
- **Confirmación estricta** — las operaciones destructivas exigen `SÍ` o `YES` literales. "ok" / "claro" / "dale" *no* son aceptados.
- **Lista de subcomandos permitidos** — el script rechaza `git config --global`, `filter-branch` y otros que modifican el estado global.
- **Sin exposición de credenciales** — los tokens embebidos en URLs remotas se eliminan antes de mostrarlos.
- **Descubrimiento automático** — busca repositorios en `~/projects`, `~/repos`, `~/code`, `~/Documents/GitHub`.
- **Diagnóstico de errores** — explica los fallos y propone soluciones concretas.
- **Commits convencionales** — sugiere mensajes estructurados cuando no proporcionas uno.

### Requisitos

- Cuenta de Claude con Skills habilitado
- Git 2.0+
- Python 3.7+ (para los scripts auxiliares)
- Repositorios clonados localmente

### Instalación

**Opción A — Interfaz de Claude Skills**

1. Abre Claude → **Settings → Skills → Add Skill**
2. Sube o apunta al archivo `SKILL.md`
3. Claude confirma que el skill está activo

**Opción B — Manual (self-hosted / API)**

```bash
git clone https://github.com/tu-usuario/github-git-manager-skill.git
cp -r github-git-manager-skill ~/.claude/skills/github-git-manager
python3 ~/.claude/skills/github-git-manager/scripts/validate_setup.py
```

### Configuración inicial

```bash
python3 scripts/validate_setup.py
```

Salida esperada en un sistema correcto:
```
✅ Git           git version 2.43.0
✅ Python        3.11.4
✅ Git Identity  name: Tu Nombre / email: tu@ejemplo.com
✅ Ssh Keys      id_ed25519.pub
✅ Repositories  3 repositorios encontrados

✅ Todo está en orden. Prueba: "Muéstrame mis repositorios"
```

### Ejemplos de uso

**Inspeccionar**
- "Muéstrame mis repositorios"
- "¿En qué rama estoy en my-app?"
- "¿Qué archivos he modificado?"
- "Muéstrame los últimos 10 commits"

**Ramas**
- "Crea una rama llamada feature/dark-mode"
- "Cambia a main"
- "Elimina la rama feature/old-login"

**Guardar trabajo**
- "Haz commit de mis cambios con el mensaje 'feat: add dark mode'"
- "Prepara solo los archivos CSS y haz commit"
- "¿Cómo quedaría el mensaje de commit?" *(Claude propone uno)*
- "Guarda en stash lo que tengo en progreso"

**Sincronizar**
- "Trae los últimos cambios"
- "Sube mis commits"
- "¿Qué commits tengo que no están en GitHub todavía?"

**Deshacer**
- "Deshaz el último commit (pero conserva los cambios)"
- "Descarta mis cambios en login.js"
- "Resetea todo" *(pide confirmación)*

**Resolver problemas**
- "Me aparece Permission denied (publickey)"
- "Tengo un conflicto de fusión, ayúdame a resolverlo"
- "Me rechazó el push"

### Modelo de seguridad

| Nivel | Ejemplos | Comportamiento |
|-------|----------|----------------|
| Seguro | status, log, diff, fetch, listar ramas | Se ejecuta de inmediato |
| Moderado | switch, pull, crear rama | Avisa si hay cambios sin confirmar |
| Destructivo | reset --hard, force push, clean -fd, branch -D, rm | Requiere `SÍ` / `YES` literal |
| Restringido | push a `main` / `master` | Pide confirmación aunque no sea destructivo localmente |

Bloque de confirmación:
```
⚠️  OPERACIÓN DESTRUCTIVA
    Comando: git <comando exacto>
    Efecto:  <qué cambia / qué se pierde>
    Afecta:  <archivos / commits / ramas en riesgo>
    Repo:    <ruta absoluta>

    Escribe SÍ (o YES) para confirmar. Cualquier otra cosa cancela.
```

### CLI del script auxiliar

`git_manager.py` también se puede usar directamente desde la terminal:

```bash
# Buscar repositorios (carpetas predeterminadas)
python3 scripts/git_manager.py find

# Buscar con carpetas personalizadas
python3 scripts/git_manager.py find --base-dir /trabajo/clientes ~/personal

# Estado
python3 scripts/git_manager.py status ~/projects/my-app

# Ejecutar un comando seguro
python3 scripts/git_manager.py run ~/projects/my-app -- log --oneline -10

# Ejecutar un comando destructivo (requiere --confirmed)
python3 scripts/git_manager.py run ~/projects/my-app --confirmed -- reset --hard HEAD~1

# Salida en JSON (útil para tuberías)
python3 scripts/git_manager.py --json find | jq '.[].name'

# Validar el entorno
python3 scripts/git_manager.py validate
```

El script aplica:
- Una **lista de subcomandos permitidos** (rechaza `config --global`, `filter-branch`, etc.).
- Un **control de operaciones destructivas** (el flag `--confirmed` es obligatorio para `reset --hard`, `clean -f`, force push, `branch -D`, etc.).
- **Tiempos de espera por llamada** (10 s para operaciones rápidas, 60 s para operaciones de red).
- **Eliminación de credenciales** en URLs remotas antes de mostrarlas.

### Estructura de archivos

```
github-git-manager/
├── SKILL.md                    ← Claude lee este archivo
├── README.md                   ← Estás aquí
├── LICENSE
├── scripts/
│   ├── git_manager.py          ← Helper CLI (lista permitida + control de seguridad)
│   └── validate_setup.py       ← Verificador de entorno
├── references/
│   ├── operations.md           ← Referencia completa de comandos (carga bajo demanda)
│   └── errors.md               ← Diagnóstico de errores (carga bajo demanda)
└── evals/
    └── evals.json              ← Casos de prueba
```

### Notas de seguridad

- El skill **nunca** muestra claves SSH privadas, tokens ni el contenido de `.git-credentials`.
- Las URLs con credenciales incorporadas (`https://usuario:token@host/...`) se sanitizan antes de mostrarse.
- El comando `run` del helper rechaza `git config --global` / `--system` para proteger la configuración global.
- En la guía de errores se advierte sobre el uso de `safe.directory '*'` y `credential.helper store` (que almacena tokens en texto plano).
- Cada operación destructiva requiere `SÍ`/`YES` literal — los sinónimos informales ("ok", "claro", "dale") son rechazados.
- Las confirmaciones son de un solo uso — la siguiente operación destructiva requiere una nueva confirmación.
- No se realizan llamadas de red más allá de las que hace el propio `git`.

### Resolución de problemas

- **El skill no se activa** → menciona algo relacionado con Git: "git", "github", "commit", "rama", "push", "pull", "repositorio".
- **No encuentra repositorios** → revisa `ls ~/projects/` o indica una ruta explícita: *"En /ruta/a/mi/repo, muéstrame el estado"*.
- **Problemas de SSH** → ejecuta `ssh -T git@github.com`, luego `ssh-add ~/.ssh/id_ed25519`.
- **Python no encontrado** → el skill principal funciona sin Python (Claude llama a `git` directamente por bash). Los scripts son solo una herramienta de conveniencia.

### Contribuir

1. Haz un fork del repositorio
2. `git switch -c feature/tu-mejora`
3. Agrega un caso en `evals/evals.json` por cada comportamiento nuevo
4. Abre un Pull Request

Para agregar una operación nueva:
1. Agrégala a `references/operations.md`.
2. Si es destructiva, actualiza `_is_destructive()` en `git_manager.py`.
3. Si tiene modos de fallo comunes, agrégalos a `references/errors.md`.
4. Agrega un caso de evaluación en `evals/evals.json`.
5. Actualiza la tabla de operaciones en `SKILL.md`.

### Licencia

MIT — ver [LICENSE](./LICENSE).

---

## 🇬🇧 English

### What it is

A Claude Skill that lets you operate Git repositories through natural conversation. It understands English and Spanish, diagnoses common errors, and **always asks before doing anything destructive**.

```
You:    Show me all my projects and what branch they're on
Claude: ✅ Found 3 repositories:
         📁 web-app     → main           (2 changed files)
         📁 api-server  → develop        (clean)
         📁 mobile-app  → feature/login  (1 changed file)

You:    Reset all my changes in web-app
Claude: ⚠️  DESTRUCTIVE OPERATION
         Command: git reset --hard HEAD
         Effect:  Permanently discards all uncommitted changes
         Affects: src/auth/login.js, src/routes/index.js
         Repo:    /home/you/projects/web-app

         Type YES (or SÍ) to confirm. Anything else cancels.
```

### Features

- **Natural language** — works in English and Spanish, no command syntax required.
- **Strict confirmation** — destructive ops require literal `YES` or `SÍ`. "ok" / "sure" / "dale" are *not* accepted.
- **Subcommand allowlist** — the helper script refuses `git config --global`, `filter-branch`, and other state-altering commands.
- **Credential-safe** — tokens embedded in remote URLs are stripped before display.
- **Smart discovery** — auto-finds repos in common directories (`~/projects`, `~/repos`, `~/code`, `~/Documents/GitHub`).
- **Error diagnosis** — explains failures and offers concrete fixes.
- **Conventional commits** — proposes structured messages when you don't provide one.

### Requirements

- A Claude account with Skills enabled
- Git 2.0+
- Python 3.7+ (for the helper scripts)
- Repositories cloned locally

### Installation

**Option A — Claude Skills UI**

1. Open Claude → **Settings → Skills → Add Skill**
2. Upload or point to the `SKILL.md` file
3. Claude confirms the skill is active

**Option B — Manual (self-hosted / API)**

```bash
git clone https://github.com/your-username/github-git-manager-skill.git
cp -r github-git-manager-skill ~/.claude/skills/github-git-manager
python3 ~/.claude/skills/github-git-manager/scripts/validate_setup.py
```

### First-time setup

```bash
python3 scripts/validate_setup.py
```

Expected on a healthy system:
```
✅ Git           git version 2.43.0
✅ Python        3.11.4
✅ Git Identity  name: Your Name / email: you@example.com
✅ Ssh Keys      id_ed25519.pub
✅ Repositories  3 repos found

✅ Everything looks good. Try: "Show me my repositories"
```

### Usage examples

**Inspect**
- "Show me my repositories"
- "What branch am I on in my-app?"
- "What files have I changed?"
- "Show me the last 10 commits"

**Branches**
- "Create a branch called feature/dark-mode"
- "Switch to main"
- "Delete the feature/old-login branch"

**Save work**
- "Commit my changes with message 'feat: add dark mode'"
- "Stage only the CSS files and commit"
- "What would my commit message look like?" *(Claude proposes one)*
- "Stash my work in progress"

**Sync**
- "Pull the latest changes"
- "Push my commits"
- "What commits do I have that aren't on GitHub yet?"

**Undo**
- "Undo my last commit (keep the changes)"
- "Discard my changes to login.js"
- "Reset everything" *(asks for confirmation)*

**Troubleshoot**
- "I'm getting Permission denied (publickey)"
- "There's a merge conflict, help me fix it"
- "My push was rejected"

### Safety model

| Tier | Examples | Behavior |
|------|----------|----------|
| Safe | status, log, diff, fetch, branch list | Run immediately |
| Moderate | switch, pull, create branch | Warn if working tree is dirty |
| Destructive | reset --hard, force push, clean -fd, branch -D, rm | Require literal `YES` / `SÍ` |
| Gated | push to `main` / `master` | Require confirmation even if not local-destructive |

Confirmation block:
```
⚠️  DESTRUCTIVE OPERATION
    Command: git <exact command>
    Effect:  <what changes / what is lost>
    Affects: <files / commits / branches at risk>
    Repo:    <absolute path>

    Type YES (or SÍ) to confirm. Anything else cancels.
```

### Helper script CLI

`git_manager.py` is also usable directly from the terminal:

```bash
# Find repos (default dirs)
python3 scripts/git_manager.py find

# Find with custom dirs
python3 scripts/git_manager.py find --base-dir /work/clients ~/personal

# Status
python3 scripts/git_manager.py status ~/projects/my-app

# Run a safe command
python3 scripts/git_manager.py run ~/projects/my-app -- log --oneline -10

# Run a destructive command (requires --confirmed)
python3 scripts/git_manager.py run ~/projects/my-app --confirmed -- reset --hard HEAD~1

# JSON output (good for piping)
python3 scripts/git_manager.py --json find | jq '.[].name'

# Validate environment
python3 scripts/git_manager.py validate
```

The script enforces:
- An **allowlist of subcommands** (rejects `config --global`, `filter-branch`, etc.).
- A **destructive-op gate** (`--confirmed` flag required for `reset --hard`, `clean -f`, force push, `branch -D`, etc.).
- **Per-call timeouts** (10 s for fast ops, 60 s for network ops).
- **URL credential stripping** before any remote URL is displayed.

### File structure

```
github-git-manager/
├── SKILL.md                    ← Claude reads this
├── README.md                   ← You are here
├── LICENSE
├── scripts/
│   ├── git_manager.py          ← CLI helper (allowlist + safety gate)
│   └── validate_setup.py       ← Environment checker
├── references/
│   ├── operations.md           ← Full command reference (loaded on demand)
│   └── errors.md               ← Error diagnosis (loaded on demand)
└── evals/
    └── evals.json              ← Test cases
```

### Security notes

- The skill **never** displays SSH private keys, tokens, or `.git-credentials` contents.
- Remote URLs with embedded credentials (`https://user:token@host/...`) are sanitized before display.
- The helper's `run` command refuses `git config --global` / `--system` to protect user-wide state.
- The skill warns against `safe.directory '*'` and `credential.helper store` (plaintext token storage) in its error guidance.
- Every destructive op requires a literal `YES`/`SÍ`; soft synonyms ("ok", "sure", "dale") are rejected.
- Confirmations are single-use — the next destructive op needs a fresh confirmation.
- No network calls except via `git` itself.

### Troubleshooting

- **Skill not activating** → mention something Git-related: "git", "github", "commit", "branch", "push", "pull", "repo".
- **Repos not found** → check `ls ~/projects/`, or pass an explicit path: *"In /path/to/repo, show status"*.
- **SSH issues** → `ssh -T git@github.com`, then `ssh-add ~/.ssh/id_ed25519`.
- **Python missing** → core skill works without it (Claude calls `git` directly via bash). Scripts are convenience-only.

### Contributing

1. Fork the repo
2. `git switch -c feature/your-improvement`
3. Add an eval case to `evals/evals.json` for any new behavior
4. Open a PR

When adding a new operation:
1. Add the command to `references/operations.md`.
2. If destructive, update `_is_destructive()` in `git_manager.py`.
3. If it has common failure modes, add them to `references/errors.md`.
4. Add an eval to `evals/evals.json`.
5. Update the operation table in `SKILL.md`.

### License

MIT — see [LICENSE](./LICENSE).

---
