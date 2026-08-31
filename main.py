import json
import csv
import os
from dotenv import load_dotenv
from tqdm import tqdm
from huggingface_hub import HfFileSystem

# Load Hugging Face token from .env
load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")

# Dataset details
REPO_ID = "ASLP-lab/WenetSpeech-Yue"
FILENAME = "wenetspeech_yue_meta.jsonl"   # the actual file name in the repo


def parse_time_stamp(time_stamp: str | None):
    """Return (start, end) seconds from a timestamp string like 9798.410_9801.030."""
    if not time_stamp:
        return None, None
    if not isinstance(time_stamp, str):
        return None, None

    parts = time_stamp.split("_")
    if len(parts) != 2:
        return None, None

    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        return None, None


def refine_entry(data: dict) -> dict | None:
    """
    Extract only the fields we need from a single JSON entry.
    Returns None if there is no 'link' (i.e., skip this row).
    """
    meta_info = data.get("meta_info") or {}
    link = meta_info.get("link")
    if not link:
        return None

    return {
        "key": data.get("key"),
        "rover_result": data.get("rover_result"),
        "link": link,
        "region": meta_info.get("region"),
        "time_stamp": meta_info.get("time_stamp"),
        "duration": data.get("duration"),
    }


def main():
    # Connect to the Hugging Face Hub file system
    fs = HfFileSystem(token=HF_TOKEN)

    # Open the remote JSONL file (streaming, no download)
    with fs.open(f"datasets/{REPO_ID}/{FILENAME}", "r", encoding="utf-8") as remote_file:
        # Open local CSV for writing
        with open("wenetspeech_refined.csv", "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=["key", "rover_result", "region", "link", "time_stamp", "duration"],
            )
            writer.writeheader()

            count = 0

            # Iterate line by line with a progress bar
            for line in tqdm(remote_file, desc="Processing rows", unit="rows"):
                # 1. Skip lines that are not valid JSON
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # 2. Skip rows that cause any other error (missing keys, etc.)
                try:
                    entry = refine_entry(data)
                except Exception:
                    continue

                # 3. Write only if entry is not None (has a valid link)
                if entry is not None:
                    writer.writerow(entry)
                    count += 1

            print(f"Finished writing {count} entries.")


if __name__ == "__main__":
    main()
