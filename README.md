# Eliza Bett Music Lab 6.0 — Local AI Audio Workstation

## Запуск на Windows 10 + RTX 4060

1. Распакуйте архив в удобную папку.
2. Нужен Python 3.11/3.12 и Node.js LTS.
3. Создайте виртуальное окружение:
   `python -m venv .venv`
4. Активируйте его и установите зависимости:
   `\.venv\Scripts\python.exe -m pip install -r requirements.txt`
5. Для RTX 4060 установите совместимый PyTorch с CUDA. Проверьте:
   `\.venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"`
6. Запустите `run_lab.bat`.
7. Откройте `http://127.0.0.1:5173`.

При первом запуске frontend выполняет `npm install` автоматически.

## UI / UX 6.0

The 6.0 interface is a product-first mastering workstation redesign. It keeps the existing React/Vite + FastAPI stack and adds: evidence-led overview, explicit A/B original/master preview, before/after master metrics, candidate QC table, decision context, clearer AI Engineer states, and persistent product/design registers (`PRODUCT.md`, `DESIGN.md`).

## Pipeline

AUDIO → DEEP AUDIO ENGINE → AI DECISION ENGINE → PROCESSING PLAN → MASTER ENGINE → ITERATIVE CANDIDATES → QC → ROLLBACK/FINAL MASTER

## Модули

- Deep Audio Analysis: loudness, RMS, peak, true peak, crest, stereo, spectral bands и timeline.
- Decision Engine: проблемные области, severity/confidence и corrective actions.
- Master Engine: adaptive processing, несколько кандидатов, loudness finalization, QC и rollback.
- Reference: сравнительный отчёт по loudness, dynamics, stereo и spectral profile.
- Vocal Intelligence: `librosa.pyin` для pitch/range/stability на полном миксе; это оценка, а не изолированная вокальная дорожка.
- Stem Lab: Demucs `htdemucs` через локальный Python/CUDA.
- AI Engineer: локальный контекст текущего анализа и решений.

## Master profiles

- Suno 6 · Commercial — target -10.5 LUFS.
- Suno 5.5 · Balanced — target -11 LUFS.
- Clean Streaming — target -12 LUFS.

Это **Suno-oriented commercial profiles**, а не копия proprietary DSP Suno.

## Точность

Browser UI не используется как эталонный loudness meter. Авторитетные loudness/QC расчёты выполняет Python engine. True Peak рассчитывается собственным измерителем проекта; для финального релиза рекомендуется дополнительная проверка в независимом сертифицированном meter.

## Troubleshooting

- `Python venv not found`: создайте `.venv` в корне или установите рабочее окружение рядом с проектом.
- `npm install` не проходит: проверьте Node.js/npm и доступ к npm registry.
- Demucs падает: сначала проверьте `torch.cuda.is_available()`; при необходимости замените `-d cuda` на CPU вручную.
- Порт 8000/5173 занят: остановите старый экземпляр API/UI.

### 6.2 Audio Intelligence
The Intelligence workspace maps spectral movement, stereo/phase, transients and full-mix vocal events. Use these observations together with the Decision Engine and QC; they are not automatic defect labels.

## 6.9 AI Song Director

Songwriter Studio now includes AI Song Director. It combines audio analysis, Vocal Intelligence, Artist DNA, optional reference context and trend research into a structured creative brief, lyric draft and Suno-ready production direction. Full AI generation requires OPENAI_API_KEY; without it a deterministic local fallback uses available project metrics and DNA.

## 11.0 Song Project Workflow

The Production workspace can finalize a portable project bundle. `FINALIZE PROJECT` packages the current demo, latest accepted master, production report, lyrics, Suno prompt and notes into one ZIP. The bundle is a delivery package, not a DAW session.

API: `/project`, `/project/save`, `/project/export`.

## Production billing

YooKassa payments use a durable pending-payment ledger and authoritative payment-status reconciliation. The webhook path re-fetches the payment from YooKassa before activation, while duplicate payment activation is idempotent. A protected `POST /billing/admin/reconcile` endpoint is available.

After the production API is deployed, configure these GitHub Actions repository secrets:

- `SONA_BILLING_API_URL` — public API base URL, for example the deployed Render service URL.
- `SONA_BILLING_ADMIN_KEY` — the same high-entropy value configured as the API's `SONA_BILLING_ADMIN_KEY`.

The `Billing reconciliation` workflow runs every 15 minutes from the repository's default branch and can also be started manually. It reconciles up to 50 pending YooKassa payments per run and retries transient HTTP failures. Keep the admin key secret and use HTTPS for the API URL.
