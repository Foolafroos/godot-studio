# godot-studio — Hermes plugin for the agent game studio

Réponse au besoin exprimé par Teknium (thread « DIY game dev studio », oct. 2026) :
il manque un chemin **Godot** officiel dans l'écosystème Hermes.

## État de l'écosystème (vérifié le 19/10/2026)

| Projet | Stars | Licence | Activité | Rôle |
|---|---|---|---|---|
| `hi-godot/godot-ai` | 1.9k | MIT | très active (commits août 2026) | **46 outils MCP, cite Hermes Agent comme client supporté** (`godot-ai attach` stdio). Nécessite Godot 4.7+ et `uv`. |
| `Coding-Solo/godot-mcp` | 5.4k | MIT | quiet depuis avril 2026 | le plus étoilé, mais dormeur |
| `yurineko73/Godot-MCP-Native` | 722 | MIT | active | 155 outils, pur GDScript, **zéro dépendance Node/Python**, CLI `gdmcp` à découverte progressive |
| `youichi-uda/godot-mcp-pro` | 575 | commerciale | active | 175 outils, Asset Library |

## Positionnement de ce plugin

godot-ai fait déjà le pont éditeur↔agent. Le plugin n'emballe pas ce pont — il ajoute ce qui manque :

1. **Mode headless** : `godot --headless --quit` (validation de scripts sans éditeur),
   export CI (`--export-release`). godot-ai exige un éditeur vivant ; le studio
   agentique a besoin de vérifications reproductibles sans GUI.
2. **Skill `godot-studio`** : le workflow complet — enregistrement godot-ai,
   scaffold, édition via MCP, check headless, export web, playtest.
3. **Accroche playtester** : le lien avec REA (observation native du build joué)
   est documenté dans le skill ; l'outillage complet est un chantier séparé.

## Structure

```
plugin.yaml          manifeste Hermes (name/version/description)
__init__.py          couche tools atomiques (headless check, export, setup)
skills/godot-studio/ couche intelligence (workflow, enchaînements)
vendor/              clones d'étude (godot-ai, Godot-MCP-Native) — ne pas packager
```

## Installation (dev)

```bash
cp -r . ~/.hermes/plugins/godot-studio   # ou symlink
# puis : hermes mcp add godot-ai ... (le tool godot_setup donne la commande exacte)
```

## Prérequis

- Godot 4.x (cask `godot-4`), `uv` pour godot-ai.
- Le tool `godot_setup` détecte l'état et génère les commandes manquantes.

## Prochaines étapes

- [ ] Tester les tools contre un projet de démo (scaffold minimal).
- [ ] Valider le format de manifeste contre la doc plugin officielle / un plugin officiel.
- [ ] Proposer le plugin au catalogue (tier community d'abord).
- [ ] Évaluer Godot-MCP-Native (`gdmcp` CLI) comme variante sans dépendances.
