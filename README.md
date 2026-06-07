# WiFi-Radar — human-sensing radar dashboard

A single-file browser dashboard styled like the viral "your WiFi can see through walls" clips: a sweeping Doppler radar, per-target detection cards, and a live CSI-style waveform. It runs in two modes.

- 🟢 **LIVE** — your **webcam** + an in-browser person detector ([TensorFlow.js COCO-SSD](https://github.com/tensorflow/tfjs-models/tree/master/coco-ssd)) drive the radar with **real people** it sees. The video **never leaves your browser** — no upload, no server. This is honest computer vision, *not* WiFi-through-wall.
- 🟠 **SIM** — a synthetic fallback (used if you deny the camera): a 4-room flat with a router and signal rays crossing walls, plus random-walking agents. This is the "WiFi sees through walls" fantasy, clearly labelled as fake.

> ▶ **Live demo:** runs on GitHub Pages — link in the repo's *About* sidebar. Click **Allow** when it asks for the camera, then walk around in frame.

## Run it

Open `index.html`, or serve it locally:

```bash
python -m http.server 8077   # → http://127.0.0.1:8077
```

The camera needs a secure context — `localhost` and the GitHub Pages `https://` URL both qualify (a raw `file://` open won't get camera access, and falls back to SIM).

## What's on screen

- **Sensor view (left)** — in LIVE mode, your mirrored webcam with bounding boxes on each detected person; in SIM mode, the floorplan with router→person signal rays.
- **Doppler radar (centre)** — each person plotted by bearing (their position across the frame) and range (bigger in frame ⇒ closer), with a sweep that brightens a blip as it passes.
- **Detections (right)** — count, per-target bearing/range/confidence/moving, RSSI / motion-index / frames-per-second, and a CSI amplitude trace that spikes with real movement.

## How real WiFi sensing works (what SIM pretends to be)

Moving bodies change how WiFi signals bounce around a room (multipath). A receiver that exposes **Channel State Information (CSI)** — amplitude and phase across the OFDM subcarriers — sees those changes as a body moves, even through a wall, since RF at 2.4/5 GHz partly passes through drywall. With enough subcarriers and some signal processing (or a model) you can infer presence, motion, breathing, rough position, and in research even coarse pose. Doing it for real needs CSI-capable hardware:

- **[ESP32-CSI-Tool](https://github.com/StevenMHernandez/ESP32-CSI-Tool)** — CSI from a ~$5 ESP32, the easiest real start.
- **[Nexmon CSI](https://github.com/seemoo-lab/nexmon_csi)** — CSI on Broadcom/Cypress chips (e.g. Raspberry Pi).
- **Intel 5300** — the classic [Linux 802.11n CSI Tool](https://dhalperi.github.io/linux-80211n-csitool/).
- Research: **DensePose From WiFi** (CMU, 2023); earlier *WiVi* / *RF-Pose* (MIT).

## What's real vs. not

| | LIVE mode | SIM mode |
|---|---|---|
| WiFi capture | ❌ never | ❌ never |
| Camera | ✅ your webcam (stays local) | ❌ |
| Detections | ✅ real (COCO-SSD person detection) | synthetic random-walk agents |
| Radar / CSI waveform | driven by real motion | driven by fake motion |
| "Through walls" | no — it's a camera | only as a visual conceit |

## Tech

Vanilla JS, three `<canvas>` layers, `requestAnimationFrame`. SIM mode is fully self-contained; LIVE mode loads TensorFlow.js + COCO-SSD from a CDN and runs inference in-browser. No build step.

## License

MIT — see [LICENSE](LICENSE). © 2026 Rafael Proenca.
