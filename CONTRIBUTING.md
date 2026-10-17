# Contributing

## Daily flow

```bash
git checkout main && git pull          # start from the latest main
git checkout -b feature/short-name     # one branch per task
# ...work...
git add <files>                        # prefer naming files over `git add .`
git commit -m "backend: add login endpoint"
git push -u origin feature/short-name
```

Then open a Pull Request into `main` on GitHub. One teammate reviews, then merge.

## Rules

1. **Never push directly to `main`.** Turn on branch protection (Settings → Branches → require a pull request).
2. **Pull before you start working** and before you push, so conflicts stay small.
3. **Keep commits small** and use a prefix: `backend:`, `ai:`, `unity:`, `dashboard:`, `docs:`.
4. **Never commit secrets.** API keys, passwords and `.env` files stay local. Put placeholders in `.env.example`. If a key is ever committed, rotate it immediately; deleting it from the next commit is not enough.
5. **Big files go through Git LFS** (models, audio, video, textures). The patterns are already set in `.gitattributes`.

## Unity specifics (avatar-unity/)

- In Unity: Edit → Project Settings → Editor → set **Asset Serialization** to *Force Text* and **Version Control** to *Visible Meta Files*.
- Always commit `.meta` files together with their assets.
- Avoid two people editing the same scene or prefab at once. Split work into separate prefabs and tell the team before touching a shared scene.
- Never commit `Library/`, `Temp/`, `Obj/` or `Builds/` (already ignored).

## If you hit a merge conflict

```bash
git pull origin main        # on your branch
# fix the conflict markers in the files, then:
git add <fixed-files>
git commit
```

Ask in the team chat before resolving conflicts in Unity scene or prefab files.
