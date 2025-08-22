import pandas as pd
import unicodedata

# === FILE PATHS ===
matrix_path = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/tree_matrix_output/manuscript_block_matrix_filtered.csv"

comparison_files = {
    "omission": "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/omission_block_comparison.csv",
    "addition": "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/addition_block_comparison.csv",
    "substitution": "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/block_level_substitution_stanza_level_comparison.csv",
    "permutation": "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/permutation_block_comparison.csv"
}

output_path = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/leitfehler_candidates_with_exact_types.csv"

# === Unicode normalization ===
def normalize(text):
    return unicodedata.normalize("NFC", str(text).strip())

# === Step 1: Load the Manuscript × Leitfehler matrix ===
df = pd.read_csv(matrix_path, index_col=0)

# === Step 2: Filter Leitfehler shared by ≥2 manuscripts ===
leitfehler_cols = df.columns[df.sum() >= 2]

# === Step 3: Build type + description lookup with fallback ===
def build_type_lookup():
    lookup = {}
    for type_name, path in comparison_files.items():
        comp_df = pd.read_csv(path)

        for _, row in comp_df.iterrows():
            block_id = normalize(row.get("block_id", ""))

            if type_name == "substitution":
                desc = normalize(row.get("the_change", ""))
            elif type_name == "addition":
                desc = normalize(row.get("added_words", ""))
            elif type_name == "omission":
                desc = normalize(row.get("omitted_words", ""))
            elif type_name == "permutation":
                desc = "True"
            else:
                desc = ""

            leitfehler_id_full = normalize(f"{block_id} | {desc}")
            lookup[leitfehler_id_full] = {
                "type": type_name,
                "block_id": block_id,
                "description": desc,
            }
            # Also fallback to block_id only
            lookup[block_id] = {
                "type": type_name,
                "block_id": block_id,
                "description": desc,
            }

    return lookup

type_lookup = build_type_lookup()

# === Step 4: Create long-form presence table ===
presence_table = (
    df[leitfehler_cols]
    .stack()
    .reset_index()
    .rename(columns={"level_0": "manuscript_id", "level_1": "leitfehler_id", 0: "present"})
)
presence_table = presence_table[presence_table["present"] == 1].drop(columns=["present"])

# === Step 5: Group by Leitfehler and attach metadata ===
leitfehler_groups = presence_table.groupby("leitfehler_id")["manuscript_id"].apply(list).reset_index()
leitfehler_groups["num_mss"] = leitfehler_groups["manuscript_id"].apply(len)

# === Step 6: Resolve metadata (support fallback ID) ===
def resolve_field(lf_id, field):
    lf_id = normalize(lf_id)
    return type_lookup.get(lf_id, {}).get(field, "❌ ERROR")

leitfehler_groups["block_id"] = leitfehler_groups["leitfehler_id"].apply(lambda x: resolve_field(x, "block_id"))
leitfehler_groups["description"] = leitfehler_groups["leitfehler_id"].apply(lambda x: resolve_field(x, "description"))
leitfehler_groups["type"] = leitfehler_groups["leitfehler_id"].apply(lambda x: resolve_field(x, "type"))

# === Step 7: Check for unresolved cases ===
errors = leitfehler_groups[leitfehler_groups["type"] == "❌ ERROR"]
if not errors.empty:
    print("❗ WARNING: Unresolved Leitfehler IDs found!")
    print(errors.head())
    raise ValueError("❌ Some Leitfehler IDs could not be resolved.")

# === Step 8: Save result ===
leitfehler_groups = leitfehler_groups[[
    "leitfehler_id", "block_id", "description", "type", "manuscript_id", "num_mss"
]]
leitfehler_groups = leitfehler_groups.sort_values(by="num_mss", ascending=False)

leitfehler_groups.to_csv(output_path, index=False)
print(f"✅ Leitfehler list with exact types saved to:\n{output_path}")
