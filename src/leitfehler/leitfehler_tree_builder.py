import pandas as pd
import numpy as np
import re
from collections import defaultdict
from scipy.spatial.distance import pdist
from scipy.cluster.hierarchy import linkage, dendrogram, to_tree
import matplotlib.pyplot as plt
import seaborn as sns
from io import StringIO
from Bio import Phylo

# === CONFIG ===
FILLED_CHANGES_FILE = "/home/nikta/Desktop/OCR/data/CAB/Yasna/yasna matches filled changes - 5,6,8,15,40,400,60_filled_changes_hybrid.csv"
SUBSTITUTION_RULES_FILE = "/home/nikta/Desktop/OCR/data/CAB/Yasna/substitution_rules_v6.csv"

# === LOAD DATA ===
df = pd.read_csv(FILLED_CHANGES_FILE)
rules_df = pd.read_csv(SUBSTITUTION_RULES_FILE)

# Clean NaNs from manuscript_id just to be sure:
df = df.dropna(subset=["manuscript_id"])
df = df[df['manuscript_id'] != ""]

# === BUILD RULE DICTIONARY ===
type_dict = {}
for _, row in rules_df.iterrows():
    rule = f"{row['to']} for {row['from']}".strip()
    rule_type = row['type'].strip()
    type_dict[tuple(rule.split(" for "))] = rule_type


# === CLASSIFICATION FUNCTION ===
def classify_change(change_str):
    if pd.isna(change_str) or change_str.strip() == "":
        return "="  # exact matches

    subchanges = [ch.strip() for ch in change_str.split(",")]
    result = []
    for sub in subchanges:
        if "for" in sub:
            parts = sub.split("for")
            to = parts[0].strip()
            from_ = parts[1].strip()
            rule_type = type_dict.get((to, from_), "?")
            result.append((from_, to, rule_type))
        elif "inserted" in sub:
            token = sub.replace("inserted", "").strip()
            result.append((None, token, "insertion"))
        elif "deleted" in sub:
            token = sub.replace("deleted", "").strip()
            result.append((token, None, "deletion"))
        else:
            result.append((None, None, "?"))
    return result


# === EXTRACT STRUCTURED CHANGES ===
structured_changes = []
for _, row in df.iterrows():
    ms = str(row['manuscript_id']).strip()
    classified = classify_change(row['the change'])
    for change in classified:
        structured_changes.append((change[0], change[1], change[2], ms))

# === INVERTED INDEX ===
inverted_index = defaultdict(set)
for source, target, ctype, ms in structured_changes:
    key = (source, target, ctype)
    inverted_index[key].add(ms)

# === CALCULATE WEIGHTED LEITFEHLER ===

# Count manuscripts
all_manuscripts = sorted(set(ms for _, _, _, ms in structured_changes))

# Weight system (Option C weights)
weights = {
    "1": 0.3,
    "r-b": 0.6,
    "?": 1.0,
    "insertion": 0.8,
    "deletion": 0.8
}

# Build weighted matrix
row_labels = []
weighted_matrix = []

for (source, target, ctype), shared_by in inverted_index.items():
    # Skip cases shared by all manuscripts
    if len(shared_by) == len(all_manuscripts):
        continue

    # Get weight
    weight = weights.get(ctype, 1.0)

    # Apply frequency penalty
    penalty = 1 - (len(shared_by) / len(all_manuscripts))
    final_weight = weight * penalty

    row_labels.append(f"{ctype}: {source} → {target}")
    row = [final_weight if ms in shared_by else 0 for ms in all_manuscripts]
    weighted_matrix.append(row)

if len(weighted_matrix) == 0:
    raise ValueError("No Leitfehler patterns detected after filtering.")

df_matrix = pd.DataFrame(weighted_matrix, columns=all_manuscripts, index=row_labels)

# === Build dendrogram ===
distance_matrix = pdist(df_matrix.T, metric="euclidean")
linkage_matrix = linkage(distance_matrix, method="average")

plt.figure(figsize=(12, 5))
dendrogram(linkage_matrix, labels=all_manuscripts)
plt.title("Weighted Leitfehler Dendrogram (Option C)")
plt.show()

# === Also show heatmap for inspection ===
plt.figure(figsize=(12, 8))
sns.heatmap(df_matrix, cmap="Blues", cbar=False, linewidths=0.3, linecolor='gray')
plt.title("Weighted Leitfehler Presence Matrix")
plt.xlabel("Manuscripts")
plt.ylabel("Leitfehler")
plt.tight_layout()
plt.show()


# === Newick Export ===
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

handle = StringIO(newick_string)
tree = Phylo.read(handle, "newick")

plt.figure(figsize=(8, 5))
Phylo.draw(tree, do_show=False)
plt.title("Newick Tree Visualization")
plt.tight_layout()
plt.show()
