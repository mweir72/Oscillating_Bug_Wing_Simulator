"""
Flapping-wing simulation FastAPI backend.
"""

from run_simulation import base_params
from physics import quasi_steady_flap
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import FastAPI
import matplotlib.pyplot as plt
import io
import base64
import numpy as np
import matplotlib
matplotlib.use("Agg")

# Local project imports (must still be above any executable code)


# ------------------------- FastAPI Setup -------------------------

app = FastAPI()

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


# ------------------------- Data Models -------------------------

class SimRequest(BaseModel):
    f: float
    pitch_amp: float
    t_end: float


class SweepStepsRequest(BaseModel):
    sweep_type: str
    base: float
    freq_hz: float
    pitch_deg: float
    step: float
    t_end: float


# ------------------------- Helper -------------------------

def fig_to_base64(fig):
    """Convert matplotlib figure to base64 PNG string."""
    buf = io.BytesIO()
    fig.savefig(
        buf,
        format="png",
        bbox_inches="tight",
        dpi=120
    )
    buf.seek(0)
    img = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return img


# ------------------------- Endpoints -------------------------

@app.get("/")
def serve_ui():
    return FileResponse("static/index.html")


@app.post("/simulate_plot")
def simulate_plot(req: SimRequest):
    params = base_params.copy()
    params["f"] = req.f
    params["pitch_amp"] = req.pitch_amp
    params["t_end"] = req.t_end

    result = quasi_steady_flap(params)

    plt.style.use("dark_background")
    fig, axs = plt.subplots(3, 2, figsize=(10, 10))

    titles = [
        ("Lift (N)", result["L"]),
        ("Drag (N)", result["D"]),
        ("Power (W)", result["P"]),
        ("Efficiency", result["eta"]),
        ("Pitch Angle (deg)", result["theta_deg"]),
        ("Stroke Position (m)", result["x_pos"])
    ]

    positions = [
        (0, 0),
        (0, 1),
        (1, 0),
        (1, 1),
        (2, 0),
        (2, 1)
    ]

    for (title, data), (i, j) in zip(titles, positions):
        axs[i, j].plot(
            result["t"],
            data,
            color="#00ff88"
        )
        axs[i, j].set_title(title)
        axs[i, j].set_xlabel("Time (s)")
        axs[i, j].grid(True, alpha=0.3)

    return {"plot_base64": fig_to_base64(fig)}


@app.post("/sweep_steps")
def sweep_steps(req: SweepStepsRequest):
    values = [
        req.base - 2 * req.step,
        req.base - req.step,
        req.base,
        req.base + req.step,
        req.base + 2 * req.step
    ]

    plt.style.use("dark_background")
    fig, axs = plt.subplots(3, 2, figsize=(10, 10))

    colors = [
        "#00ff88", "#ffaa00",
        "#ffee00", "#0099ff",
        "#bb44ff"
    ]

    for idx, val in enumerate(values):
        params = base_params.copy()
        params["t_end"] = req.t_end

        if req.sweep_type == "pitch":
            params["pitch_amp"] = np.deg2rad(val)
            params["f"] = req.freq_hz
            unit = "deg"

        elif req.sweep_type == "frequency":
            params["pitch_amp"] = np.deg2rad(req.pitch_deg)
            params["f"] = val
            unit = "Hz"

        r = quasi_steady_flap(params)

        axs[0, 0].plot(
            r["t"],
            r["L"],
            color=colors[idx],
            label=f"{val} {unit}"
        )
        axs[0, 1].plot(r["t"], r["D"], color=colors[idx])
        axs[1, 0].plot(r["t"], r["P"], color=colors[idx])
        axs[1, 1].plot(r["t"], r["eta"], color=colors[idx])
        axs[2, 0].plot(r["t"], r["theta_deg"], color=colors[idx])
        axs[2, 1].plot(r["t"], r["x_pos"], color=colors[idx])

    graph_titles = [
        "Lift (N)",
        "Drag (N)",
        "Power (W)",
        "Efficiency",
        "Pitch Angle (deg)",
        "Stroke Position (m)"
    ]

    for ax, title in zip(axs.flat, graph_titles):
        ax.set_title(title)
        ax.set_xlabel("Time (s)")
        ax.grid(True, alpha=0.3)

    axs[0, 0].legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.2),
        ncol=3
    )

    return {"plot_base64": fig_to_base64(fig)}
