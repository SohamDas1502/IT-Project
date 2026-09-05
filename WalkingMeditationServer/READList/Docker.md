# Running the server with Docker

No Python, no ffmpeg, no venv. Same setup for everyone.

You need ~12 GB free disk to install it(it settles at 7 GB — the extra is
temp space used while installing and downloading).


## Setup (once)

**1. Install Docker Desktop** — https://www.docker.com/products/docker-desktop/ — and open it.

**2. Add your keys:**

```bash
cp .env.example .env
```

Open `.env` and fill in both (ask the team for the values):

```
GOOGLE_MAPS_API_KEY=...
OPENAI_API_KEY=(given to us)
```


---

## Run it

From the `WalkingMeditationServer/` folder:

```bash
docker compose up
```

Server: **http://localhost:8000** — test it at **http://localhost:8000/docs**

**First start takes ~5 minutes and looks frozen.** It's downloading the voice
model.

---

## Day to day

Rebuild only if `requirements.txt` or the `Dockerfile` changed:

```bash
docker compose up --build
```

Other commands:

```bash
docker compose down # if you want to stop and clean up
```

---

## Why it's 7 GB

| | |
|---|---|
| Voice model weights (Qwen3-TTS) | 2.4 GB |
| Python libraries it needs | 1.0 GB |
| PyTorch | 0.75 GB |
| ffmpeg + audio libs | 0.5 GB |
| Linux + Python base | 0.25 GB |
| Docker overhead | 1.4 GB |

It's the AI. None of it is optional.
