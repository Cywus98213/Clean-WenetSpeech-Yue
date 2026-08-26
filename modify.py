# modify_csv.py
import pandas as pd
from urllib.parse import urlparse

df = pd.read_csv("wenetspeech_refined.csv")

def extract_domain_name(link):
    try:
        netloc = urlparse(link).netloc   # e.g. "space.bilibili.com"
        if netloc.startswith("www."):
            netloc = netloc[4:]          # remove "www."
        parts = netloc.split(".")
        # If there's a subdomain, take the second part ("bilibili")
        if len(parts) >= 2:
            return parts[-2]
        return parts[0]
    except Exception:
        return "unknown"

df["link_type"] = df["link"].apply(lambda x: extract_domain_name(x) if pd.notna(x) else "none")

df.to_csv("wenetspeech_refined_with_domain.csv", index=False)
print("Updated CSV saved as wenetspeech_refined_with_domain.csv")
