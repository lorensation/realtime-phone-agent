from importlib import import_module
from pathlib import Path


__path__ = [str(Path(__file__).with_name("api"))]

app = import_module("realtime_phone_agents.api.main").app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
