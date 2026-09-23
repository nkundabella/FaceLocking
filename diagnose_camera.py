#!/usr/bin/env python3
"""
Camera diagnostic -- finds why an external camera shows a black window.

Tests every index (0-5) against BOTH Windows backends:
  - MSMF  (Media Foundation, default on Windows)
  - DSHOW (DirectShow, often needed for USB webcams)

For each working camera it:
  - Warms it up (skips the first ~30 black frames many cameras emit)
  - Reports resolution, FPS cap, brightness, mean pixel value
  - Shows a live window so you can see whether it's actually black
  - Prints the exact VideoCapture() call to copy into your scripts
"""

import time
import cv2
import numpy as np

INDICES   = list(range(6))
WARMUP    = 40          # frames to discard before judging (many cameras need this)
SHOW_SECS = 5           # seconds to show the live window per working camera


def mean_brightness(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray))


def try_camera(idx, backend_flag, backend_name):
    cap = cv2.VideoCapture(idx, backend_flag)
    if not cap.isOpened():
        return None

    # --- warm-up: drain the first WARMUP frames --------------------------
    last_frame = None
    for i in range(WARMUP):
        ok, f = cap.read()
        if ok and f is not None:
            last_frame = f

    if last_frame is None:
        cap.release()
        return None

    brightness = mean_brightness(last_frame)
    w  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h  = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    info = {
        "cap":        cap,
        "backend":    backend_name,
        "idx":        idx,
        "width":      w,
        "height":     h,
        "fps":        fps,
        "brightness": brightness,
        "frame":      last_frame,
    }
    return info


def show_live(info):
    cap      = info["cap"]
    idx      = info["idx"]
    backend  = info["backend"]
    deadline = time.time() + SHOW_SECS

    win = f"Camera {idx} [{backend}]  --  press Q to stop"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win, 800, 500)

    frame_n = 0
    while time.time() < deadline:
        ok, frame = cap.read()
        if not ok or frame is None:
            continue

        frame_n += 1
        brt = mean_brightness(frame)

        cv2.putText(frame, f"Camera {idx}  [{backend}]  frame={frame_n}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(frame, f"Brightness: {brt:.1f}  (0=black, 127=mid, 255=white)",
                    (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
        cv2.putText(frame, f"Size: {info['width']}x{info['height']}  FPS cap: {info['fps']:.0f}",
                    (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)

        remaining = int(deadline - time.time())
        cv2.putText(frame, f"Auto-closing in {remaining}s  (Q to close now)",
                    (10, 135), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 200, 255), 2)

        cv2.imshow(win, frame)
        if (cv2.waitKey(1) & 0xFF) == ord('q'):
            break

    cv2.destroyWindow(win)


def main():
    print()
    print("=" * 60)
    print("  CAMERA DIAGNOSTIC")
    print("=" * 60)
    print(f"  OpenCV {cv2.__version__}")
    print(f"  Scanning indices {INDICES[0]}-{INDICES[-1]}, two backends each")
    print(f"  Warm-up frames: {WARMUP}")
    print("=" * 60)

    BACKENDS = [
        (cv2.CAP_DSHOW, "DSHOW"),
        (cv2.CAP_MSMF,  "MSMF"),
    ]

    working = []

    for idx in INDICES:
        for flag, name in BACKENDS:
            print(f"\n  [{name}] Trying index {idx} ...", end="", flush=True)
            info = try_camera(idx, flag, name)

            if info is None:
                print("  -> not available")
                continue

            brt = info["brightness"]
            status = "BLACK (brightness ~0)" if brt < 5 else f"OK  brightness={brt:.1f}"
            print(f"  -> {info['width']}x{info['height']} @ {info['fps']:.0f}fps  |  {status}")

            if brt < 5:
                print(f"       *** Likely cause: camera opened but sends black frames ***")
                print(f"       *** Try the OTHER backend, or check USB power / privacy settings ***")

            working.append(info)
            show_live(info)
            info["cap"].release()

    print()
    print("=" * 60)
    print("  RESULTS")
    print("=" * 60)

    if not working:
        print("  No cameras found at all.")
        print()
        print("  Possible causes:")
        print("  1. Camera not plugged in / not recognised by Windows")
        print("  2. Camera in use by another app (Teams, OBS, etc.)")
        print("  3. Windows Camera Privacy: Settings > Privacy > Camera -> ON")
        print("  4. Missing or corrupt USB driver -- check Device Manager")
        return

    best = max(working, key=lambda i: i["brightness"])

    for info in working:
        brt_flag = "  <-- BLACK" if info["brightness"] < 5 else ""
        print(f"  index={info['idx']}  backend={info['backend']}"
              f"  {info['width']}x{info['height']}"
              f"  brightness={info['brightness']:.1f}{brt_flag}")

    print()
    if best["brightness"] < 5:
        print("  ALL cameras returned black frames.")
        print()
        print("  Most common causes on Windows:")
        print("  A) Windows Camera Privacy setting is OFF")
        print("     -> Settings > Privacy & security > Camera -> Allow apps to access camera")
        print("  B) Wrong exposure/gain -- camera autoexposure hasn't kicked in yet")
        print("     -> Run fix_camera_exposure.py if available")
        print("  C) USB bandwidth -- unplug other USB devices on the same controller")
        print("  D) Camera lens cap still on  (happens more than you'd think!)")
    else:
        print(f"  Best camera:  index={best['idx']}  backend={best['backend']}")
        print()
        print("  Use this exact call in your scripts:")
        print()
        print(f"    cap = cv2.VideoCapture({best['idx']}, cv2.CAP_{best['backend']})")
        print()
        print("  And skip the first ~30 frames so the exposure can settle:")
        print()
        print("    for _ in range(30):")
        print("        cap.read()")

    print("=" * 60)


if __name__ == "__main__":
    main()
