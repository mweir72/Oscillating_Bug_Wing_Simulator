import io
import base64
import matplotlib.pyplot as plt
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from physics import quasi_steady_flap
from run_simulation import base_params

app = FastAPI(title="Bug Wing Simulator API")

# Serve website from /static folder
app.mount("/", StaticFiles(directory="static", html=True), name="static")


class SimRequest(BaseModel):
    f: float = 150
    stroke_amp: float = 0.01
    pitch_amp: float = 0.785  # 45 deg
    t_end: float = 0.02


@app.post("/simulate_plot")
def simulate_plot(req: SimRequest):
    """Run simulation and return a 6-grid plot as base64 PNG."""
    params = base_params.copy()
    params["f"] = req.f
    params["stroke_amp"] = req.stroke_amp
    params["pitch_amp"] = req.pitch_amp
    params["t_end"] = req.t_end

    r = quasi_steady_flap(params)

    # Create 6 subplot figure like MATLAB version
    fig, axs = plt.subplots(3, 2, figsize=(10, 10))

    axs[0, 0].plot(r["t"], r["L"]); axs[0, 0].set_title("Lift vs Time")
    axs[0, 1].plot(r["t"], r["D"]); axs[0, 1].set_title("Drag vs Time")
    axs[1, 0].plot(r["t"], r["P"]); axs[1, 0].set_title("Power vs Time")
    axs[1, 1].plot(r["t"], r["eta"]); axs[1, 1].set_title("Efficiency")
    axs[2, 0].plot(r["t"], r["theta_deg"]); axs[2, 0].set_title("Pitch Angle")
    axs[2, 1].plot(r["t"], r["x_pos"]); axs[2, 1].set_title("Stroke Position")

    for ax in axs.flat:
        ax.set_xlabel("Time (s)")
        ax.grid(True)

    # Convert to PNG
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close(fig)

    img_base64 = base64.b64encode(buf.read()).decode("utf-8")

    return {"plot_base64": img_base64}
