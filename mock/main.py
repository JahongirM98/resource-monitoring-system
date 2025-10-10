from fastapi import FastAPI
import random

app = FastAPI()

@app.get("/m/{mid}/metrics")
def metrics(mid: int):
    return {
        "cpu": random.randint(1, 95),
        "mem": f"{random.randint(10, 85)}%",
        "disk": f"{random.randint(5, 90)}%",
        "uptime": f"{random.randint(0,5)}d {random.randint(0,23)}h {random.randint(0,59)}m {random.randint(0,59)}s",
    }
