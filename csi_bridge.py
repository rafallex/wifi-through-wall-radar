#!/usr/bin/env python3
"""
ESP32 WiFi-CSI -> WebSocket bridge for the WiFi-Radar dashboard.

Reads Channel State Information (CSI) from an ESP32 over serial (the
espressif/esp-csi "csi_recv_router" CSV format), turns it into an honest
*motion magnitude* + *presence* signal, and streams it as JSON to the
dashboard over a WebSocket at ws://127.0.0.1:8765.

  python csi_bridge.py                 # MOCK mode: synthesises CSI, no hardware needed
  python csi_bridge.py --port COM5     # real ESP32 on COM5 (Windows)
  python csi_bridge.py --port /dev/ttyUSB0   # Linux/Mac

Honest by design: ONE ESP32 = one antenna = "something moved / is present",
NOT a position. This bridge never invents an (x, y); it only emits a 0..1
motion score, a present flag, RSSI and the raw subcarrier amplitudes.

Deps:  pip install websockets        (+ pyserial only if you use --port)
"""
import argparse, asyncio, json, time, math, random, collections, statistics, sys

try:
    import websockets
except ImportError:
    sys.exit("Missing dependency. Run:  pip install websockets")

HOST = "127.0.0.1"


# ----------------------------------------------------------------------------
# Feature extraction: per-subcarrier amplitude -> coefficient-of-variation
# over a sliding window -> adaptive 0..1 motion score.
# ----------------------------------------------------------------------------
def amps_from_iq(arr):
    """arr = [imag0, real0, imag1, real1, ...] signed ints -> amplitudes."""
    out = []
    for i in range(0, len(arr) - 1, 2):
        im, re = arr[i], arr[i + 1]
        out.append(math.hypot(re, im))
    return out


class MotionDetector:
    """Empty room => flat subcarrier variance; a moving body spikes it.
    Coefficient of variation (std/mean) is gain-invariant; an adaptive quiet
    floor makes it robust to the static-but-unique CSI of each room."""

    def __init__(self, win=48, gain=14.0):
        self.win = win
        self.gain = gain
        self.hist = collections.deque(maxlen=win)
        self.floor = None

    def update(self, amps):
        if not amps:
            return 0.0
        self.hist.append(amps)
        if len(self.hist) < 8:
            return 0.0
        n = min(len(a) for a in self.hist)
        cvs = []
        for col in zip(*[a[:n] for a in self.hist]):
            m = sum(col) / len(col)
            if m > 1e-6:
                cvs.append(statistics.pstdev(col) / m)
        cv = sum(cvs) / len(cvs) if cvs else 0.0
        # adaptive quiet floor: track down fast, drift up slow
        if self.floor is None:
            self.floor = cv
        elif cv < self.floor:
            self.floor = 0.95 * self.floor + 0.05 * cv
        else:
            self.floor = 0.999 * self.floor + 0.001 * cv
        return max(0.0, min(1.0, (cv - self.floor) * self.gain))


# ----------------------------------------------------------------------------
# Sources: real serial, or a synthetic mock so the pipeline runs without an ESP32
# ----------------------------------------------------------------------------
async def serial_source(port, baud, q):
    try:
        import serial  # pyserial
    except ImportError:
        sys.exit("Real-board mode needs pyserial. Run:  pip install pyserial")
    ser = serial.Serial(port, baud, timeout=1)
    print(f"[csi] reading ESP32 CSI from {port} @ {baud} baud")
    while True:
        raw = await asyncio.to_thread(ser.readline)
        line = raw.decode("ascii", "ignore").strip()
        if "[" not in line or "]" not in line:
            continue
        try:
            inner = line[line.index("[") + 1: line.rindex("]")]
            vals = [int(x) for x in inner.replace(",", " ").split()]
            rssi = -50
            # esp-csi CSV puts rssi early in the line; grab it if present
            head = line.split("[", 1)[0].replace(",", " ").split()
            for tok in head:
                try:
                    v = int(tok)
                    if -100 < v < -10:
                        rssi = v
                        break
                except ValueError:
                    pass
            await q.put((amps_from_iq(vals), rssi))
        except Exception:
            pass


async def mock_source(q):
    print("[csi] MOCK mode - synthesising CSI (no hardware). Use --port COMx for a real ESP32.")
    N = 52
    t = 0.0
    event = 0.0
    next_event = 2.0
    while True:
        t += 0.04
        if t > next_event:                      # "someone walks through"
            event = 1.0
            next_event = t + random.uniform(3.5, 9.0)
        event *= 0.94                            # decay back to quiet
        amps = []
        for k in range(N):
            base = 20 + 8 * math.sin(k * 0.30)
            noise = random.gauss(0, 0.6 + event * 6.5)   # motion widens variance
            amps.append(max(0.0, base + noise))
        rssi = -42 - int(event * 5)
        await q.put((amps, rssi))
        await asyncio.sleep(0.04)                # ~25 Hz


# ----------------------------------------------------------------------------
# WebSocket server: fan out detections to every connected dashboard
# ----------------------------------------------------------------------------
async def main():
    ap = argparse.ArgumentParser(description="ESP32 WiFi-CSI -> WebSocket bridge")
    ap.add_argument("--port", help="ESP32 serial port (e.g. COM5 or /dev/ttyUSB0). Omit for MOCK mode.")
    ap.add_argument("--baud", type=int, default=921600)
    ap.add_argument("--ws-port", type=int, default=8765)
    args = ap.parse_args()

    q = asyncio.Queue(maxsize=8)
    det = MotionDetector()
    clients = set()

    async def register(ws, *_):
        clients.add(ws)
        print(f"[ws] dashboard connected ({len(clients)} client(s))")
        try:
            await ws.wait_closed()
        finally:
            clients.discard(ws)
            print(f"[ws] dashboard left ({len(clients)} client(s))")

    async def produce():
        last_present = None
        pkt, t_pkt, pps = 0, time.time(), 0
        while True:
            amps, rssi = await q.get()
            motion = det.update(amps)
            present = motion > 0.12
            pkt += 1
            if time.time() - t_pkt >= 1.0:
                pps, pkt, t_pkt = pkt, 0, time.time()
            if present != last_present:
                print(f"[csi] {'PRESENCE / motion' if present else 'quiet'}  motion={motion:.2f}")
                last_present = present
            msg = json.dumps({
                "source": "esp32-csi",
                "t": int(time.time() * 1000),
                "present": present,
                "motion": round(motion, 3),
                "rssi": rssi,
                "pps": pps,
                "sub": [round(a, 1) for a in amps[:64]],
            })
            if clients:
                await asyncio.gather(*(c.send(msg) for c in list(clients)),
                                     return_exceptions=True)

    src = serial_source(args.port, args.baud, q) if args.port else mock_source(q)
    async with websockets.serve(register, HOST, args.ws_port):
        print(f"[ws] streaming CSI on ws://{HOST}:{args.ws_port}")
        print("[ws] open the dashboard (served from localhost) and pick CSI mode")
        await asyncio.gather(src, produce())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[csi] stopped")
