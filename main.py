from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List, Dict
import matplotlib.pyplot as plt
import io
from fastapi.responses import Response

app = FastAPI()

class ChartConfig(BaseModel):
    type: str  # e.g., "line", "bar"
    x: str     # x-axis column name
    y: str     # y-axis column name

class ChartRequest(BaseModel):
    data: List[Dict]
    config: ChartConfig

@app.post("/generate-chart")
async def generate_chart(payload: ChartRequest):
    data = payload.data
    config = payload.config

    x_vals = [item[config.x] for item in data]
    y_vals = [item[config.y] for item in data]

    fig, ax = plt.subplots()
    if config.type == "line":
        ax.plot(x_vals, y_vals)
    elif config.type == "bar":
        ax.bar(x_vals, y_vals)
    else:
        return {"error": "Unsupported chart type"}

    ax.set_xlabel(config.x)
    ax.set_ylabel(config.y)
    ax.set_title(f"{config.type.title()} Chart of {config.y} by {config.x}")

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png")
    plt.close()
    buf.seek(0)

    return Response(content=buf.read(), media_type="image/png")
