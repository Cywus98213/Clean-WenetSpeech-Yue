# Clean WenetSpeech-Yue

Pipeline for downloading Cantonese speech source audio from online links, cutting timestamped clips from the WenetSpeech-Yue metadata, and browsing the results in a Streamlit app.

This repository has two workflows:

1. **Main pipeline** (recommended): download full audio → cut clips using dataset timestamps → browse clips
2. **STT test ground** (optional / experimental): transcribe full audio with a Hugging Face Cantonese model → cut clips from STT segments

The main pipeline and STT test ground are separate. The main pipeline does not depend on PyTorch or Transformers.

---

## 1. What you need installed

### System tools

| Tool | Why it is needed |
|------|------------------|
| **Python 3.10+** | Runs the scripts |
| **ffmpeg** | Audio conversion (downloader) and clip cutting (`extract_clips.py`) |

Install ffmpeg and make sure it is on your `PATH`:

- Windows: [ffmpeg downloads](https://ffmpeg.org/download.html) or `winget install ffmpeg`
- macOS: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

Check:

```bash
python --version
ffmpeg -version
```

### Python packages (main pipeline)

From the project root:

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

This installs:

- `pandas` — CSV handling
- `tqdm` — progress bars
- `yt-dlp` — video/audio downloading
- `streamlit` — web explorer

### Optional: cookies file

Some sites (especially Bilibili) may require login cookies.

1. Export cookies from your browser (Netscape format)
2. Save as `cookies.txt` in the project root

The downloader uses `cookies.txt` automatically if the file exists.

---

## 2. Input data

The default input file is:

```text
wenetspeech_refined_clean.csv
```

Important columns:

| Column | Meaning |
|--------|---------|
| `key` | Unique row id |
| `link` | Source URL (Douyin, Bilibili, Xigua, etc.) |
| `time_stamp` | Clip range in seconds, format `start_end` (e.g. `620.270_624.350`) |
| `rover_result` | Reference transcript text |
| `region` | Region label (e.g. 广东, 香港) |
| `duration` | Clip length in seconds (optional fallback if timestamp is incomplete) |

Example row:

```text
key,rover_result,region,link,time_stamp,duration,link_type
gd0027722_620270_624350,但系小母你又睬都唔睬佢入咗船舱添,广东,https://...,620.270_624.350,4.352,douyin
```

---

## 3. Main pipeline (step by step)

Run these commands from the project root with your virtual environment activated.

### Step 1 — Download full source audio

```bash
python downloader.py
```

Or with a small test batch:

```bash
python downloader.py --limit 20
```

**What it does**

- Reads `wenetspeech_refined_clean.csv`
- Deduplicates by source audio (`cache_key`), so each unique video/part is downloaded once
- Saves full MP3 files into `success/`
- Writes two reports:
  - `success/success_links.csv` — rows where full audio was downloaded
  - `failed/failed_links.csv` — rows that failed (with `error` column)

**What to expect**

- Progress bar: `Downloading full audio`
- Summary at the end with success/failed counts
- Not every link will succeed (expired URLs, geo/login restrictions, non-video pages, etc.)
- Bilibili multi-part videos are handled separately (e.g. `BVxxx_p354.mp3`)

Useful flags:

```bash
python downloader.py --help
python downloader.py --limit 100 --workers 4 --quiet
```

### Step 2 — Cut timestamped clips

```bash
python extract_clips.py
```

Test on a subset first:

```bash
python extract_clips.py --limit 50
```

**What it does**

- Reads `success/success_links.csv`
- For each row, finds the full audio file and cuts the segment defined by `time_stamp`
- Saves clips to `speech_clips/`
- Writes `speech_clips/clip_view.csv` with a `local_audio_path` column for each successful clip

**What to expect**

- Progress bar: `Cutting clips`
- Summary with success/failed counts
- Clip filenames look like: `BV18p4y1B7Az_579010_581320_gd0046218_579010_581320.mp3`
- Rows are skipped/failed when:
  - Full audio file is missing
  - Timestamp is outside the downloaded audio duration
  - ffmpeg produces an invalid/tiny output file

Useful flags:

```bash
python extract_clips.py --help
python extract_clips.py --workers 8 --limit 100
```

### Step 3 — Browse results in Streamlit

```bash
streamlit run visual.py
```

**What it shows**

- Metrics: clip count, failed download count, playable audio files found
- **Clipped audio** tab: table + expandable rows with text, timing, audio player
- **Failed downloads** tab: failed rows from the downloader

Open the URL shown in the terminal (usually `http://localhost:8501`).

---

## 4. Output folder layout

After running the main pipeline:

```text
Clean_WenetSpeech-Yue/
├── wenetspeech_refined_clean.csv      # Input metadata
├── success/
│   ├── success_links.csv              # Rows with downloaded full audio
│   ├── BV18p4y1B7Az.mp3                # Example full audio files
│   └── ...
├── failed/
│   └── failed_links.csv               # Rows that failed to download
├── speech_clips/
│   ├── clip_view.csv                  # Successful clip index
│   └── *.mp3                          # Cut clip files
├── downloader.py                      # Step 1 entry point
├── extract_clips.py                   # Step 2 entry point
└── visual.py                          # Step 3 entry point
```

---

## 5. STT test ground (optional)

> Only use this if the `stt_testground/` folder is included in your copy of the repo.
> This is experimental and separate from the main pipeline.

Instead of relying on dataset timestamps, this approach:

1. Takes a full downloaded MP3 from `success/`
2. Runs Cantonese speech-to-text with a Hugging Face Whisper model
3. Cuts one clip per transcript segment
4. Pairs STT text with each clip

### Extra install (STT only)

```bash
pip install -r stt_testground/requirements-stt.txt
```

First run downloads model weights from Hugging Face (can take several minutes).

### Run STT extraction

Quick CPU test (recommended first):

```bash
python stt_extract.py --max-sources 1 --max-segments 5 --max-audio-sec 120
```

Fuller run:

```bash
python stt_extract.py --max-sources 1 --max-segments 20
```

**What to expect**

- Clear status messages: model loading, transcription, clipping, done
- CPU transcription is slow on long audio (e.g. 20+ minutes of audio can take 10–30+ minutes)
- Output goes to `stt_testground/output/`:
  - `stt_clip_view.csv`
  - `clips/`
  - `transcripts/`

Browse STT results:

```bash
streamlit run stt_visual.py
```

Useful STT flags:

```bash
python stt_extract.py --help
python stt_extract.py --max-audio-sec 120    # only first 2 minutes per file
python stt_extract.py --skip-clips           # transcribe only, no ffmpeg cuts
python stt_extract.py --verbose              # show Hugging Face / HTTP logs
```

---

## 6. Recommended first run (sanity check)

For a first test, use small limits so you can verify the full flow quickly:

```bash
python downloader.py --limit 10
python extract_clips.py --limit 10
streamlit run visual.py
```

You should see:

1. Some files in `success/`
2. Some clips in `speech_clips/`
3. A working explorer in the browser

It is normal for some links to fail. Check `failed/failed_links.csv` for reasons.

---

## 7. Troubleshooting

### `ffmpeg` not found

Install ffmpeg and restart your terminal. Both `downloader.py` and `extract_clips.py` need it.

### Downloader fails for many Bilibili links

- Add `cookies.txt` in the project root
- Try lowering concurrency: `python downloader.py --workers 2`

### Clip extraction fails with “timestamp outside source duration”

The metadata timestamp points beyond the actual downloaded audio length. This can happen when:

- The link is not a direct video page
- The downloaded file is shorter than the original source
- The URL resolved to a different video/part

These rows are rejected on purpose to avoid invalid tiny MP3 files.

### Streamlit shows “Clip file missing on disk”

Re-run `python extract_clips.py` after downloading, or check that `local_audio_path` in `clip_view.csv` points to an existing file under `speech_clips/`.

### STT appears stuck on “Running speech-to-text”

This usually means transcription is still running on CPU. Use `--max-audio-sec 120` for faster tests. You should see heartbeat messages every ~30 seconds.

---

## 8. Project structure (code)

```text
audio_utils.py          Shared helpers (timestamps, paths, ffmpeg probes)
download/               Downloader package
  cli.py                CLI argument parsing
  pipeline.py           Download orchestration
  ydl_client.py         yt-dlp integration
  reports.py            success/failed CSV writing
extract_clips.py        Timestamp-based clip cutting
explorer/               Streamlit app for main pipeline
visual.py               Streamlit entry point
stt_testground/         Optional STT experiment (if included)
stt_extract.py          STT CLI entry point (if included)
stt_visual.py           STT Streamlit entry point (if included)
```

---

## 9. Typical workflow summary

```text
wenetspeech_refined_clean.csv
        │
        ▼
  python downloader.py
        │
        ├─► success/success_links.csv + success/*.mp3
        └─► failed/failed_links.csv
        │
        ▼
  python extract_clips.py
        │
        └─► speech_clips/clip_view.csv + speech_clips/*.mp3
        │
        ▼
  streamlit run visual.py
        │
        └─► Browse clips and failed downloads in browser
```

If you have questions about a specific failed row, check the `error` column in `failed/failed_links.csv` or the clip timing shown in the Streamlit expander view.
