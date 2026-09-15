# SØNA Agent Runtime

Единый слой skills/agents для FastAPI backend. Архитектура намеренно additive: существующие audio, auth, Telegram и frontend-маршруты не требуют миграции.

## Источники

- OpenClaw — совместимый `SKILL.md`/AgentSkills формат и skill discovery.
- Hermes Agent — progressive disclosure, `SKILL.md`, metadata/gating и разделение skills/tools.
- prompts.chat — публичный REST/MCP prompt catalog.

## Почему не подключаем целиком

OpenClaw — отдельный Node gateway/runtime; Hermes — отдельный Python agent runtime с большим набором зависимостей. Установка их целиком в SØNA создаст конфликтующие runtimes, lockfiles и поверхности безопасности. Мы переносим только формат и выбранные инструкции, а исполнение оставляем в текущем SØNA/OpenAI runtime.

## Поток

`HTTP /agents/invoke -> AgentRequest -> registry -> skill loader -> optional prompts.chat -> existing OpenAI provider -> JSON response -> JSONL audit log`

## API

### GET `/agents`

Возвращает каталог доступных agents.

### POST `/agents/invoke`

```json
{
  "agent": "songwriter",
  "message": "Придумай припев про то, что проблемы только в голове",
  "history": [],
  "context": {"project": "ВСЁ РАВНО"}
}
```

Ответ:

```json
{
  "ok": true,
  "agent": "songwriter",
  "answer": "...",
  "sources": []
}
```

## Безопасность

- External skill/prompt text считается недоверенным контекстом.
- Никакие shell-команды из SKILL.md автоматически не выполняются.
- Agent endpoint проходит существующую auth middleware.
- API keys не помещаются в prompts или логи.
- Размеры input/history ограничены.
- Ошибки провайдера наружу не раскрываются.

## Добавление нового skill

1. Добавить `.sona/skills/<name>.md` или `agents/skills/external/<name>/SKILL.md`.
2. Добавить запись в `agents/registry.json`.
3. Если skill требует реального кода, бинарных файлов или OAuth — делать отдельный tool adapter, а не прятать выполнение в Markdown.
4. Добавить минимальный тест: happy path, missing dependency, provider failure.
