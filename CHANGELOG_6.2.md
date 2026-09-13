# Eliza Bett Music Lab 6.2 — Audio Intelligence

## Added
- Five-second spectral intelligence map: sub, bass, low-mid, mid, presence, high and air.
- Spectral descriptors: centroid, rolloff, flatness, RMS, peak and crest per section.
- Stereo/phase timeline: L/R correlation, M/S width, side-energy percentage and L/R balance.
- Transient map using onset strength/detection with section density.
- Full-mix vocal event map using `librosa.pyin`: voiced ratio, median pitch and pitch movement by section.
- Evidence-based findings layer connecting observations to possible actions without forcing processing.
- `/intelligence?source=original|master|reference` API endpoint.
- Master report now contains `final_intelligence` for post-processing verification.
- New Intelligence workspace in the React UI.
- Post-master finding summary.

## Design rule
Observations are not automatically treated as defects. The intelligence layer supplies evidence; the Decision Engine and QC remain responsible for processing decisions.

## Metering note
Loudness compliance remains separate from the visual intelligence layer. The project uses the existing backend loudness/true-peak analysis for final QC. ITU-R BS.1770-5 remains the reference for programme loudness and true-peak measurement; EBU R 128 also uses loudness range and maximum true peak as programme descriptors.
