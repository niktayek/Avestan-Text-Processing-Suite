import pandas as pd
import numpy as np
from collections import defaultdict
from scipy.spatial.distance import pdist
from scipy.cluster.hierarchy import linkage, dendrogram, to_tree
import matplotlib.pyplot as plt
from io import StringIO
from Bio import Phylo

# === CONFIG ===
# ✅ Set the same rule version you used in the tagging phase:
RULE_VERSION = 1  # <--- Change this when you test different rule versions

# File paths
TAGGED_FILE = f"/home/nikta/Desktop/OCR/data/CAB/Yasna/yasna_tagged_optionC_v{RULE_VERSION}.csv"
DEBUG = True

# === Load tagged file ===
df = pd.read_csv(TAGGED_FILE)
df = df.dropna(subset=["manuscript_id"])
df = df[df["manuscript_id"].astype(str).str.strip() != ""]

# === Build structured changes ===
structured_changes = []

for _, row in df.iterrows():
    ms = str(row["manuscript_id"]).strip()
    change_str = row["the change"]
    tag_str = row["Leitfehler_tag"]

    if pd.isna(change_str) or tag_str == "=":
        continue

    subchanges = [ch.strip() for ch in change_str.split(",")]
    subtags = [ch.strip() for ch in tag_str.split(",")]

    for subchange, subtag in zip(subchanges, subtags):
        if subtag != "?":
            continue  # Only keep uncertain changes

        if "for" in subchange:
            parts = subchange.split("for")
            target = parts[0].strip()
            source = parts[1].strip()
            structured_changes.append((source, target, subtag, ms))
        elif "inserted" in subchange:
            token = subchange.replace("inserted", "").strip()
            structured_changes.append((None, token, "insertion", ms))
        elif "deleted" in subchange:
            token = subchange.replace("deleted", "").strip()
            structured_changes.append((token, None, "deletion", ms))
        else:
            structured_changes.append((None, None, "?", ms))

# === Build inverted index ===
inverted_index = defaultdict(set)
for source, target, ctype, ms in structured_changes:
    key = (source, target, ctype)
    inverted_index[key].add(ms)

all_manuscripts = sorted(set(ms for _, _, _, ms in structured_changes))

# === Build Leitfehler matrix ===
row_labels = []
matrix_rows = []

for (source, target, ctype), shared_by in inverted_index.items():
    if len(shared_by) <= 1 or len(shared_by) == len(all_manuscripts):
        continue  # must be shared by at least 2 manuscripts but not all

    label = f"{ctype}: {source} → {target}"
    row_labels.append(label)
    row = [1 if ms in shared_by else 0 for ms in all_manuscripts]
    matrix_rows.append(row)

# === Diagnostics ===
if DEBUG:
    print("Total manuscripts:", len(all_manuscripts))
    print("Total uncertain variants collected:", len(inverted_index))
    print("Variants surviving Leitfehler filtering:", len(row_labels))

if not matrix_rows:
    print("⚠ No valid Leitfehler found under current rule set. Exiting.")
    exit()

# === Build matrix ===
df_matrix = pd.DataFrame(matrix_rows, columns=all_manuscripts, index=row_labels)

# === Compute dendrogram ===
distance_matrix = pdist(df_matrix.T, metric="hamming")
linkage_matrix = linkage(distance_matrix, method="average")

plt.figure(figsize=(12, 6))
dendrogram(linkage_matrix, labels=all_manuscripts)
plt.title(f"Leitfehler Dendrogram (Option C, Rule Set v{RULE_VERSION})")
plt.tight_layout()
plt.show()

# === Generate Newick ===
def get_newick(node, leaf_names, newick="", parentdist=0.0):
    if node.is_leaf():
        return f"{leaf_names[node.id]}:{parentdist - node.dist:.6f}{newick}"
    else:
        if newick:
            newick = f"):{parentdist - node.dist:.6f}{newick}"
        else:
            newick = ");"
        newick = get_newick(node.get_left(), leaf_names, newick, node.dist)
        newick = get_newick(node.get_right(), leaf_names, f",{newick}", node.dist)
        newick = f"({newick}"
        return newick

tree_root, _ = to_tree(linkage_matrix, rd=True)
newick_string = get_newick(tree_root, all_manuscripts)

print("\n🧬 Newick Tree:")
print(newick_string)

# === Newick visualization ===
handle = StringIO(newick_string)
tree = Phylo.read(handle, "newick")

plt.figure(figsize=(10, 5))
Phylo.draw(tree, do_show=False)
plt.title(f"Newick Tree Visualization (Rule Set v{RULE_VERSION})")
plt.tight_layout()
plt.show()
