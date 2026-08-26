# clean_cppg.py
import pandas as pd

# Load your domain-refined CSV
df = pd.read_csv("wenetspeech_refined_with_domain.csv")

# Drop rows where link_type is "cppg"
df_cleaned = df[df["link_type"] != "cppg"]

# Save cleaned CSV
df_cleaned.to_csv("wenetspeech_refined_clean.csv", index=False)

print("Original rows:", len(df))
print("Cleaned rows:", len(df_cleaned))
print("Removed rows:", len(df) - len(df_cleaned))
