# Eliza Bett Music Lab — Product Truth

Eliza Bett Music Lab is a local-first AI audio engineering workstation for musicians and producers. It analyzes a finished mix, translates measurements into explainable corrective decisions, searches mastering candidates, performs quality control, and preserves the original when processing is rejected.

## Product register
- Register: product. The interface serves an audio engineering workflow; visual design must not compete with the audio information.
- Primary user: a producer/artist who wants a professional master without losing visibility into what the system changed.
- Core promise: measure first, decide second, process only when evidence supports it.
- Operating context: local Windows workstation, NVIDIA CUDA GPU, Python/FastAPI backend and React/Vite frontend.
- Privacy: audio processing is local. Do not imply proprietary access to Suno internals.
- Voice: concise, technical, calm, evidence-led. Avoid hype inside analytical states.
- Primary workflow: Load track → Analyze → Explain decisions → Master → Compare A/B → QC → Export.
- Secondary workflow: Vocal Intelligence, GPU stem separation, reference comparison.


## 6.1 Audio Intelligence Layer

6.1 adds a visual signal layer to the workstation: waveform envelope, segment loudness movement, seekable loudness blocks, and level-matched A/B preview. The timeline is an explanatory visualization, not a compliance meter. Final loudness and true-peak decisions remain on the backend analysis/QC path.

## 6.1 Product rule

**Measure → visualize → explain → process → verify.**
The UI must expose enough evidence that an engineer can understand why a processing decision exists without opening a separate diagnostic tool.

## 6.2 Audio Intelligence
The Intelligence workspace exposes time-local evidence rather than only track-wide numbers: spectral movement, stereo/phase behavior, transient density and full-mix vocal pitch events. Findings are observations with severity and rationale. They are intentionally separated from the processing executor so the product can explain uncertainty and avoid treating every deviation as an error.
