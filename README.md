# WiFi-Radar — through-wall human sensing (simulation)

A single-file, dependency-free browser dashboard that visualises what "seeing people through walls with WiFi" looks like: a floorplan with signal rays crossing walls, a Doppler-style radar sweep, live per-target detections, and a scrolling CSI waveform.

**It is a simulation.** Every blip is generated in your browser — no router, no WiFi capture, no camera. I built it after seeing the viral "your WiFi can see through walls" clips, to recreate the look of those radar UIs and to have an honest place to explain how the real thing actually works.

> ▶ **Live demo:** runs on GitHub Pages — see the link in the repo's *About* sidebar.

## Run it

Just open `index.html` — it's one self-contained file (vanilla HTML/CSS/JS, `<canvas>`).

```bash
# or serve it locally
python -m http.server 8077
# → http://127.0.0.1:8077
```

A live version runs on GitHub Pages (see the repo's Pages settings).

## What's on screen

- **Floorplan / reflection map** — a 4-room flat, a router, and dashed signal paths from the router to each detected person. The rays cross interior walls on purpose; that "through-wall" line is the whole conceit.
- **Doppler radar** — people mapped to polar coordinates around the router, with a rotating sweep that brightens a blip as it passes.
- **Detections** — count, per-target room / range / confidence / moving-vs-still, plus an RSSI / motion-index / packets-per-second readout and a CSI amplitude trace that gets noisier as the simulated people move.

## How the real thing works

Moving bodies change how WiFi signals bounce around a room (multipath). A receiver that exposes **Channel State Information (CSI)** — amplitude and phase across the OFDM subcarriers — sees those changes as the body moves, even through a wall, because RF at 2.4/5 GHz partially passes through drywall. With enough subcarriers and some signal processing (or a model), you can infer presence, motion, breathing, rough position, and in research even coarse pose.

This demo fakes the *output*; the real pipeline needs CSI-capable hardware:

- **[Nexmon CSI](https://github.com/seemoo-lab/nexmon_csi)** — CSI extraction on Broadcom/Cypress WiFi chips (e.g. Raspberry Pi).
- **[ESP32-CSI-Tool](https://github.com/StevenMHernandez/ESP32-CSI-Tool)** — CSI from a ~$5 ESP32, the easiest way to start for real.
- **Intel 5300** — the classic [Linux CSI Tool](https://dhalperi.github.io/linux-80211n-csitool/).
- Research: **DensePose From WiFi** (CMU, 2023), and earlier work like *WiVi* / *RF-Pose* (MIT).

## What's simulated vs. real

| | this repo |
|---|---|
| WiFi capture | ❌ none |
| Camera | ❌ none |
| Detections | random-walking agents generated client-side |
| CSI waveform | a sine + motion-scaled noise, not real subcarrier data |
| The vibe | ✅ |

## Tech

Vanilla JS, three `<canvas>` layers, `requestAnimationFrame`. No build step, no dependencies, ~1 file.

## License

MIT — see [LICENSE](LICENSE).
