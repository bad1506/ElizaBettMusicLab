# SØNA external agent sources

Этот каталог содержит только адаптированные или отобранные skills. Полные runtime OpenClaw/Hermes в основной backend не устанавливаются.

| Source | Revision | Integration | License |
|---|---|---|---|
| OpenClaw | `3e3e41df1e840ebb33926b19089d96aa39bfb6ef` | AgentSkills `SKILL.md` loader | MIT |
| Hermes Agent | `78d338b9ee917b73468c38ba4633ed53de4942e6` | AgentSkills `SKILL.md` loader | MIT |
| prompts.chat | `f78a1c5136fa080155d928e0d7e2b4a41ddef03e` | HTTP prompt catalog / optional MCP | MIT source + CC0 prompt data |

## Почему не подключаем целиком

OpenClaw — отдельный Node/pnpm gateway/runtime, а Hermes — отдельный Python agent runtime с большим набором pinned dependencies. Установка целых runtime в SØNA создала бы конфликт Node/Python зависимостей и увеличила поверхность атаки.

SØNA использует совместимую идею AgentSkills: metadata + `SKILL.md` + optional references/scripts. Поэтому skill-пакеты можно добавлять без изменения ядра приложения.

## Правило импорта

1. Зафиксировать upstream commit.
2. Скопировать только нужный skill и его необходимые `references/`, `templates/`, `scripts/`.
3. Сохранить upstream license/notice для скопированного материала.
4. Проверить frontmatter и отсутствие опасных команд/секретов.
5. Не давать внешнему skill прямой доступ к секретам или произвольному shell без отдельного разрешения.
