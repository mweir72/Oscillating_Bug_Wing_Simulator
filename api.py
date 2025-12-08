import io
import base64

import matplotlib
matplotlib.use("Agg")  # headless backend for server use
import matplotlib.pyplot as plt
import numpy as np

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from physics import quasi_steady_flap
from run_simulation import base_params


app = FastAPI(title="Bug Wing Simulator API")

# Serve the static web UI under /static and index at /
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def root():
    """Serve the main website."""
    return FileResponse("static/index.html")


class SimRequest(BaseModel):
    """Single-run simulation request.

    NOTE: pitch_amp is in radians.
    Your UI can send degrees converted to radians on the client side.
    """
    f: float = 150.0
    stroke_amp: float = 0.01
    pitch_amp: float = 0.785  # 45 deg in radians
    t_end: float = 0.02


class SweepStepsRequest(BaseModel):
    """5-step sweep request around a nominal operating point.

    sweep_type:
        "pitch"      -> vary pitch (deg) around pitch_deg, hold freq = freq_hz
        "frequency"  -> vary frequency (Hz) around freq_hz, hold pitch = pitch_deg
    """
    sweep_type: str  # "pitch" or "frequency"
    freq_hz: float = 150.0       # nominal frequency (Hz)
    pitch_deg: float = 45.0      # nominal pitch (deg)
    step: float = 15.0           # step in deg (for pitch) or Hz (for freq)
    stroke_amp: float = 0.01
    t_end: float = 0.02


@app.post("/simulate_plot")
def simulate_plot(req: SimRequest):
    """Run a single simulation and return a 6-panel base64 PNG."""
    params = base_params.copy()
    params["f"] = req.f
    params["stroke_amp"] = req.stroke_amp
    params["pitch_amp"] = req.pitch_amp  # already in radians
    params["t_end"] = req.t_end

    r = quasi_steady_flap(params)

    fig, axs = plt.subplots(3, 2, figsize=(10, 10))

    axs[0, 0].plot(r["t"], r["L"])
    axs[0, 0].set_title("Lift vs Time")

    axs[0, 1].plot(r["t"], r["D"])
    axs[0, 1].set_title("Drag vs Time")

    axs[1, 0].plot(r["t"], r["P"])
    axs[1, 0].set_title("Power vs Time")

    axs[1, 1].plot(r["t"], r["eta"])
    axs[1, 1].set_title("Efficiency")

    axs[2, 0].plot(r["t"], r["theta_deg"])
    axs[2, 0].set_title("Pitch Angle")

    axs[2, 1].plot(r["t"], r["x_pos"])
    axs[2, 1].set_title("Stroke Position")

    for ax in axs.flat:
        ax.set_xlabel("Time (s)")
        ax.grid(True)

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close(fig)

    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    return {"plot_base64": img_base64}


@app.post("/sweep_steps")
def sweep_steps(req: SweepStepsRequest):
    """5-step sweep: base ± step, base ± 2*step, for pitch or frequency."""
    sweep_type = req.sweep_type.lower()
    if sweep_type not in ("pitch", "frequency"):
        return {"error": "sweep_type must be 'pitch' or 'frequency'"}

    # Build the 5 sweep values
    offsets = [-2, -1, 0, 1, 2]

    if sweep_type == "pitch":
        pitch_vals_deg = [req.pitch_deg + k * req.step for k in offsets]
        freq_vals_hz = [req.freq_hz] * len(pitch_vals_deg)
    else:  # "frequency"
        freq_vals_hz = [req.freq_hz + k * req.step for k in offsets]
        pitch_vals_deg = [req.pitch_deg] * len(freq_vals_hz)

    fig, axs = plt.subplots(3, 2, figsize=(10, 10))
    colors = plt.cm.viridis(np.linspace(0.0, 1.0, len(freq_vals_hz)))

    for idx, (f_hz, pitch_deg) in enumerate(zip(freq_vals_hz, pitch_vals_deg)):
        params = base_params.copy()
        params["t_end"] = req.t_end
        params["stroke_amp"] = req.stroke_amp
        params["f"] = f_hz
        params["pitch_amp"] = np.deg2rad(pitch_deg)

        r = quasi_steady_flap(params)

        label = f"{pitch_deg:.1f} deg" if sweep_type == "pitch" else f"{f_hz:.1f} Hz"

        axs[0, 0].plot(r["t"], r["L"], color=colors[idx], label=label)
        axs[0, 1].plot(r["t"], r["D"], color=colors[idx])
        axs[1, 0].plot(r["t"], r["P"], color=colors[idx])
        axs[1, 1].plot(r["t"], r["eta"], color=colors[idx])
        axs[2, 0].plot(r["t"], r["theta_deg"], color=colors[idx])
        axs[2, 1].plot(r["t"], r["x_pos"], color=colors[idx])

    axs[0, 0].set_title("Lift")
    axs[0, 1].set_title("Drag")
    axs[1, 0].set_title("Power")
    axs[1, 1].set_title("Efficiency")
    axs[2, 0].set_title("Pitch Angle")
    axs[2, 1].set_title("Stroke Position")

    for ax in axs.flat:
        ax.set_xlabel("Time (s)")
        ax.grid(True)

    legend_title = "Pitch Sweep (deg)" if sweep_type == "pitch" else "Frequency Sweep (Hz)"
    axs[0, 0].legend(title=legend_title)

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close(fig)

    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    return {"plot_base64": img_base64}
