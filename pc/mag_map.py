#!/usr/bin/env python3
"""Live magnetometer viewer + grid mapper for Pyboard + BNO055.

Install:  pip install pyserial matplotlib numpy
Run:      python mag_map.py COM5 --rows 5 --cols 5 --spacing 10
          (Linux: /dev/ttyACM0   Mac: /dev/tty.usbmodemXXXX)

Mark a point: press the Pyboard USR button, or press SPACE in the plot window.
Points fill the grid row by row (left->right, top->bottom).
Saves: mag_raw_<time>.csv (every sample) and mag_points_<time>.csv (grid points).
"""
import argparse, collections, csv, threading, time
import numpy as np
import serial
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Rectangle

ap = argparse.ArgumentParser()
ap.add_argument("port")
ap.add_argument("--rows", type=int, default=5)
ap.add_argument("--cols", type=int, default=5)
ap.add_argument("--spacing", type=float, default=10.0, help="grid spacing in cm")
args = ap.parse_args()

N = 300
lock = threading.Lock()
hist = {k: collections.deque(maxlen=N) for k in "xyzb"}
live = {"heading": 0.0, "cal": 0, "err": ""}
grid = np.full((args.rows, args.cols), np.nan)
n_marked = [0]

stamp = time.strftime("%Y%m%d_%H%M%S")
raw_f = open(f"mag_raw_{stamp}.csv", "w", newline="")
raw = csv.writer(raw_f)
raw.writerow(["time_s", "mx_uT", "my_uT", "mz_uT", "B_uT", "heading_deg", "mag_cal"])
pts_f = open(f"mag_points_{stamp}.csv", "w", newline="")
pts = csv.writer(pts_f)
pts.writerow(["point", "row", "col", "x_cm", "y_cm", "mx_uT", "my_uT", "mz_uT", "B_uT"])


def mark_point():
    """Average the last 10 samples and store them in the next grid cell (call with lock held)."""
    i = n_marked[0]
    if i >= args.rows * args.cols:
        print("Grid is full - restart the script for a new map.")
        return
    k = min(10, len(hist["b"]))
    if k == 0:
        return
    mx, my, mz, b = (float(np.mean(list(hist[c])[-k:])) for c in "xyzb")
    r, c = divmod(i, args.cols)
    grid[r, c] = b
    pts.writerow([i + 1, r, c, c * args.spacing, r * args.spacing,
                  round(mx, 2), round(my, 2), round(mz, 2), round(b, 2)])
    pts_f.flush()
    n_marked[0] += 1
    print(f"Point {i + 1}: row {r}, col {c}  |B| = {b:.1f} uT")


def reader():
    ser = serial.Serial(args.port, 115200, timeout=1)
    ser.write(b"\x03\x03\x04")  # Ctrl-C, Ctrl-C, Ctrl-D: soft-reset so main.py restarts cleanly
    t0 = time.time()
    while True:
        line = ser.readline().decode(errors="ignore").strip()
        if line.startswith("D,"):
            try:
                _, x, y, z, h, cal = line.split(",")
                x, y, z, h, cal = float(x), float(y), float(z), float(h), int(cal)
            except ValueError:
                continue
            b = (x * x + y * y + z * z) ** 0.5
            with lock:
                for key, v in zip("xyzb", (x, y, z, b)):
                    hist[key].append(v)
                live.update(heading=h, cal=cal, err="")
            raw.writerow([round(time.time() - t0, 3), x, y, z, round(b, 2), h, cal])
        elif line == "M":
            with lock:
                mark_point()
        elif line.startswith("ERR"):
            with lock:
                live["err"] = line
            print(line)


threading.Thread(target=reader, daemon=True).start()

# ---------- plots ----------
fig = plt.figure(figsize=(14, 5))
fig.canvas.manager.set_window_title("Pyboard magnetometer")

ax1 = fig.add_subplot(1, 3, 1)
colors = {"x": "#d62728", "y": "#2ca02c", "z": "#1f77b4", "b": "#222222"}
names = {"x": "X", "y": "Y", "z": "Z", "b": "|B| total"}
lines = {k: ax1.plot([], [], color=colors[k], lw=2 if k == "b" else 1.2, label=names[k])[0] for k in "xyzb"}
ax1.set_xlim(0, N)
ax1.set_xlabel("samples (~20 per second)")
ax1.set_ylabel("magnetic field (µT)")
ax1.legend(loc="upper left", fontsize=8)
ax1.grid(alpha=0.3)

ax2 = fig.add_subplot(1, 3, 2, projection="polar")
ax2.set_theta_zero_location("N")
ax2.set_theta_direction(-1)
ax2.set_yticks([])
needle, = ax2.plot([0, 0], [0, 1], color="#d62728", lw=3)

ax3 = fig.add_subplot(1, 3, 3)
im = ax3.imshow(grid, cmap="viridis", origin="upper")
cb = fig.colorbar(im, ax=ax3, fraction=0.046, pad=0.04)
cb.set_label("|B| (µT)")
ax3.set_xticks(range(args.cols), [f"{c * args.spacing:g}" for c in range(args.cols)])
ax3.set_yticks(range(args.rows), [f"{r * args.spacing:g}" for r in range(args.rows)])
ax3.set_xlabel("x (cm)")
ax3.set_ylabel("y (cm)")
ax3.set_title("Field map - press USR button / SPACE")
cell_txt = [[ax3.text(c, r, "", ha="center", va="center", fontsize=8, color="white")
             for c in range(args.cols)] for r in range(args.rows)]
next_box = Rectangle((-0.5, -0.5), 1, 1, fill=False, ec="#ff7f0e", lw=2.5)
ax3.add_patch(next_box)


def on_key(ev):
    if ev.key == " ":
        with lock:
            mark_point()


fig.canvas.mpl_connect("key_press_event", on_key)


def update(_):
    with lock:
        data = {k: list(v) for k, v in hist.items()}
        h, cal, err = live["heading"], live["cal"], live["err"]
        g = grid.copy()
        i = n_marked[0]
    if data["b"]:
        xs = range(len(data["b"]))
        for k in "xyzb":
            lines[k].set_data(xs, data[k])
        allv = data["x"] + data["y"] + data["z"] + data["b"]
        lo, hi = min(allv), max(allv)
        pad = max(5, (hi - lo) * 0.1)
        ax1.set_ylim(lo - pad, hi + pad)
        ax1.set_title(f"|B| = {data['b'][-1]:.1f} µT")
    needle.set_data([np.radians(h)] * 2, [0, 1])
    cal_txt = ["not calibrated", "low", "medium", "CALIBRATED"][cal]
    ax2.set_title(err or f"Heading {h:.0f}°   mag cal: {cal}/3 ({cal_txt})", fontsize=10,
                  color="#d62728" if err or cal < 3 else "#2ca02c")
    if not np.all(np.isnan(g)):
        im.set_data(g)
        im.set_clim(np.nanmin(g), max(np.nanmax(g), np.nanmin(g) + 0.1))
        for r in range(args.rows):
            for c in range(args.cols):
                cell_txt[r][c].set_text("" if np.isnan(g[r, c]) else f"{g[r, c]:.1f}")
    if i < args.rows * args.cols:
        r, c = divmod(i, args.cols)
        next_box.set_xy((c - 0.5, r - 0.5))
        next_box.set_visible(True)
    else:
        next_box.set_visible(False)
    raw_f.flush()
    return []


ani = FuncAnimation(fig, update, interval=100, cache_frame_data=False)
plt.tight_layout()
try:
    plt.show()
finally:
    raw_f.close()
    pts_f.close()
    print(f"Saved mag_raw_{stamp}.csv and mag_points_{stamp}.csv")
