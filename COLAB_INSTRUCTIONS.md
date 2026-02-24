# XML ID Relabeler - Google Colab Edition

## Quick Start (No Installation Needed!)

### For Your Colleague:

1. **Open Google Colab**
   - Go to [colab.research.google.com](https://colab.research.google.com)
   - Click "New notebook"

2. **Paste the Code**
   - Open file: `XML_ID_Relabeler_Colab_Final.py`
   - Copy ALL the code (Ctrl+A, Ctrl+C)
   - Paste into Colab cell (Ctrl+V)

3. **Run the Cell**
   - Press Shift+Enter or click the play button
   - Wait for the upload prompts

4. **Upload Files**
   - **Step 1**: Upload your TARGET TEI file (the one you want to relabel)
     - Example: `2109.xml` or `0088_broken.xml`
   - **Step 2**: Upload your SOURCE TEI file (the reference/correct version)
     - Example: `0088_correct.xml`

5. **Get Results**
   - Four files will automatically download to your computer:
     - `relabeled_TIMESTAMP.xml` - Your relabeled target file
     - `backup_original_TIMESTAMP.xml` - Safety copy of original
     - `replacements_report_TIMESTAMP.csv` - All ID changes made
     - `verification_report_TIMESTAMP.txt` - Detailed summary

### That's it!

---

## What the Tool Does

**Goal**: Replace incorrect XML ids in one TEI file using ids from a correct reference file

**Three-Pass Matching Algorithm**:
1. **Exact Text Match** - Finds identical content between files and copies IDs
2. **Nested <ab> Match** - Matches content within `<ab>` elements under same `<group>`
3. **Suffix Matching** - Handles suffix letters (Y8.12a → VrS8.12a, etc.)

**Special Feature**: parals.xml is **EMBEDDED in the code** - no need to upload it separately!

---

## Troubleshooting

### "Nothing matched"
- Files may have different text/spacing
- Try adjusting NESTED_AB_ONLY or ENABLE_SUFFIX_MATCH (see config at top)

### "Too many matches"
- Text content might be too generic
- Enable DRY_RUN = True to preview without saving

### "File didn't download"
- Check your browser's downloads folder
- Files auto-delete from Colab after ~30 mins, download immediately

---

## Advanced: Configuration Options

At the top of the code, you can adjust:

```python
ENABLE_SUFFIX_MATCH = True      # Match suffix letters (Y8.12a ↔ VrS8.12a)
NESTED_AB_ONLY = False          # Only match within <ab> elements
DRY_RUN = False                 # Set True to preview without modifying
TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"
```

---

## Questions?

The code includes detailed error messages. If something fails:
1. Read the error message in Colab output
2. Check that both XML files are valid
3. Verify files aren't extremely large (>50MB may timeout)

---

**Status**: Ready to use - no Python installation, no CLI, no Terminal knowledge required!
