#!/usr/bin/env python3
"""
Tag apparatus <rdg> elements with @type based on variant classification.

Uses classification_policy.yaml and orthography_families_v4.yaml to determine:
- trivial: Orthographic/phonetic variants with no philological significance
- meaningful: Substantive variants (phonological, morphological, or lexical differences)
- missing: Empty reading (witness lacks this section)
- unknown: Unable to classify

Categories align with the philological analysis from the variant classification PDF.
"""

import argparse
from lxml import etree
from typing import Dict, Set, List, Tuple
import re
import unicodedata
import yaml
from pathlib import Path


def load_classification_rules(policy_path: str) -> List[Dict]:
    """Load classification rules from YAML policy file."""
    with open(policy_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config.get('rules', [])


def load_orthography_families(families_path: str) -> Dict:
    """Load orthography families from YAML file."""
    with open(families_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config.get('families', {})


def normalize_for_comparison(text: str) -> str:
    """Normalize text for comparison: lowercase, NFC normalization, remove editorial symbols."""
    text = unicodedata.normalize('NFC', text.strip().lower())
    # Remove editorial symbols (daggers, etc.) that don't affect philological meaning
    text = text.replace('※', '').replace('⁛', '')
    return text


def detect_atomic_ops(lem_text: str, rdg_text: str) -> List[str]:
    """
    Detect atomic operations between lemma and reading.
    Returns list of operation strings like "ī→ū", "a deleted", "h inserted", etc.
    
    This is a simplified detector - ideally would use the same logic as the
    variant annotator that generates these operations.
    """
    lem_norm = normalize_for_comparison(lem_text)
    rdg_norm = normalize_for_comparison(rdg_text)
    
    # Simple detection based on direct comparison
    # (This is a placeholder - ideally use proper grapheme alignment)
    ops = []
    
    # Check for exact match
    if lem_norm == rdg_norm:
        return []
    
    # Check for simple substitutions (very simplified)
    # Real implementation would use character-level alignment
    # For now, just detect some common patterns
    
    # Detect insertions/deletions
    if len(rdg_norm) < len(lem_norm):
        # Something deleted
        if lem_norm.replace('h', '') == rdg_norm:
            ops.append('h deleted')
        elif lem_norm.replace('ə', '') == rdg_norm:
            ops.append('ə deleted')
        elif lem_norm.replace('a', '') == rdg_norm:
            ops.append('a deleted')
    elif len(rdg_norm) > len(lem_norm):
        # Something inserted
        if rdg_norm.replace('h', '') == lem_norm:
            ops.append('h inserted')
        elif rdg_norm.replace('ə', '') == lem_norm:
            ops.append('ə inserted')
        elif rdg_norm.replace('a', '') == lem_norm:
            ops.append('a inserted')
    
    # Check for vowel substitutions
    vowel_pairs = [
        ('ī', 'ū'), ('ū', 'ī'),
        ('i', 'e'), ('i', 'ə'), ('e', 'i'), ('e', 'ə'), ('ə', 'i'), ('ə', 'e'),
        ('ē', 'ī'), ('ī', 'ē'), ('ē', 'e'),
        ('ā', 'ō'), ('ō', 'ā'), ('āō', 'ō'), ('ō', 'āō'),
        ('y', 'ẏ'), ('ẏ', 'y'),
        ('ą', 'ą̇'), ('ą̇', 'ą'),
        ('t', 'ϑ'), ('ϑ', 't'),
    ]
    
    for a, b in vowel_pairs:
        if a in lem_norm and b in rdg_norm:
            if lem_norm.replace(a, b) == rdg_norm:
                ops.append(f'{a}→{b}')
                break
    
    return ops


def classify_by_rules(ops: List[str], rules: List[Dict], witness_group: str = None) -> str:
    """
    Classify variant based on detected operations and classification rules.
    
    Returns: "trivial", "meaningful", or None (if no rule matches)
    """
    for rule in rules:
        # Check if rule has match (exact string) or match_regex (pattern)
        pattern = rule.get('match') or rule.get('match_regex')
        if not pattern:
            continue
        
        # Check if rule applies to this witness group
        if witness_group:
            groups = rule.get('groups', [])
            exclude_groups = rule.get('exclude_groups', [])
            if groups and witness_group not in groups:
                continue
            if exclude_groups and witness_group in exclude_groups:
                continue
        
        # Check if any operation matches this rule
        for op in ops:
            if rule.get('match'):
                # Exact match
                if op == pattern:
                    return rule.get('label', 'trivial')
            elif rule.get('match_regex'):
                # Regex match
                if re.search(pattern, op):
                    return rule.get('label', 'trivial')
    
    return None


def apply_orthography_families(lem_text: str, rdg_text: str, families: Dict) -> bool:
    """
    Check if texts match after applying orthography family neutralizations.
    Returns True if texts are equivalent under family rules (trivial variant).
    """
    lem_norm = normalize_for_comparison(lem_text)
    rdg_norm = normalize_for_comparison(rdg_text)
    
    # Try each family's neutralization rules
    for family_name, family_config in families.items():
        if not isinstance(family_config, dict):
            continue
            
        # Apply compare_only_regex patterns
        compare_patterns = family_config.get('compare_only_regex', [])
        for pattern in compare_patterns:
            # Replace pattern with placeholder for both texts
            lem_test = re.sub(pattern, '#', lem_norm)
            rdg_test = re.sub(pattern, '#', rdg_norm)
            if lem_test == rdg_test:
                return True
        
        # Apply bidirectional patterns
        patterns = family_config.get('patterns', [])
        for pattern in patterns:
            lem_test = re.sub(pattern, '#', lem_norm)
            rdg_test = re.sub(pattern, '#', rdg_norm)
            if lem_test == rdg_test:
                return True
    
    return False


def _is_spacing_only_merge(lem_text: str, rdg_text: str,
                           prev_lem_text: str = None, next_lem_text: str = None) -> bool:
    """Return True if rdg_text is a simple concatenation (spacing-only merge) of
    the current lemma token with its previous or next lemma token.

    Examples considered trivial merges:
      lem[i] = 'frā.'   rdg = 'frāmąm.'   next = 'mąm.'  -> merge with next
      lem[i] = 'mąm.'   rdg = 'frāmąm.'   prev = 'frā.'  -> merge with previous

    Conditions:
      - rdg has a single trailing '.' (or none) but no internal segmentation dots
      - rdg core equals concatenation of adjacent lemma cores (order preserved)
      - No additional characters besides boundary dot removal
    """
    if not rdg_text:
        return False
    rdg_core = rdg_text.strip().lower()
    # Remove one trailing '.' for core comparison
    if rdg_core.endswith('.'):
        rdg_core = rdg_core[:-1]

    # Reject if rdg contains internal segmentation dots (other than trailing)
    if '.' in rdg_core:
        return False

    def core(t: str) -> str:
        if not t:
            return ''
        c = t.strip().lower()
        # remove trailing dot
        if c.endswith('.'):
            c = c[:-1]
        return c

    this_core = core(lem_text)
    prev_core = core(prev_lem_text) if prev_lem_text else None
    next_core = core(next_lem_text) if next_lem_text else None

    # Merge with next: current + next
    if next_core and this_core + next_core == rdg_core:
        return True
    # Merge with previous: previous + current
    if prev_core and prev_core + this_core == rdg_core:
        return True
    return False


def classify_rdg(lem_text: str, rdg_text: str, wit_id: str, 
                 rules: List[Dict], families: Dict,
                 prev_lem_text: str = None, next_lem_text: str = None) -> str:
    """
    Classify a reading variant using classification policy and orthography families.
    
    Strategy:
      1. Empty reading -> missing
      2. Exact match -> trivial
      3. Spacing-only merge/split (compound) -> trivial
      4. Orthography family neutralization -> trivial
      5. YAML rule match -> apply rule label (meaningful/trivial)
      6. Default for unmatched -> trivial (spacing/structural differences are not philologically meaningful)
    
    Returns: "trivial", "meaningful", "missing", or "unknown"
    """
    # Empty reading = missing
    if not rdg_text or rdg_text.strip() == "":
        return "missing"
    
    # Exact match = trivial
    lem_norm = normalize_for_comparison(lem_text)
    rdg_norm = normalize_for_comparison(rdg_text)
    if lem_norm == rdg_norm:
        return "trivial"
    
    # Check spacing-only merge (compound) with adjacent lemma tokens
    if _is_spacing_only_merge(lem_text, rdg_text, prev_lem_text, next_lem_text):
        return "trivial"

    # Check orthography families (neutralization rules)
    if apply_orthography_families(lem_text, rdg_text, families):
        return "trivial"
    
    # Check for substantial textual differences (meaningful by default)
    # 1. Large omissions: reading is significantly shorter than lemma
    lem_length = len(lem_norm.replace('.', '').replace(' ', ''))
    rdg_length = len(rdg_norm.replace('.', '').replace(' ', ''))
    if lem_length > 0:
        length_ratio = rdg_length / lem_length
        # If reading is less than 60% of lemma length, it's a significant omission
        if length_ratio < 0.6:
            return "meaningful"
    
    # 2. Large additions: reading is significantly longer than lemma
    if rdg_length > lem_length * 1.5:
        return "meaningful"
    
    # 3. Word-level substitution: check if core consonants differ substantially
    # Remove all diacritics, length marks, and normalize to check if it's just orthographic
    import unicodedata
    def strip_diacritics(text):
        # Remove combining diacritics and normalize
        nfd = unicodedata.normalize('NFD', text)
        return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
    
    lem_core = strip_diacritics(lem_norm.replace('.', '').replace(' ', '').lower())
    rdg_core = strip_diacritics(rdg_norm.replace('.', '').replace(' ', '').lower())
    
    # Further normalize vowel variations - remove all vowels to compare consonants
    vowels = 'aāiīuūeēoōəą̇įų'
    lem_consonants = ''.join(c for c in lem_core if c not in vowels)
    rdg_consonants = ''.join(c for c in rdg_core if c not in vowels)
    
    # If consonantal structure differs significantly, it's meaningful
    if lem_consonants != rdg_consonants:
        # Allow small differences (1-2 characters) for common variations
        import difflib
        similarity = difflib.SequenceMatcher(None, lem_consonants, rdg_consonants).ratio()
        if similarity < 0.8:  # Less than 80% consonant similarity = meaningful change
            return "meaningful"
    
    # Detect atomic operations
    ops = detect_atomic_ops(lem_text, rdg_text)
    
    # Extract witness group from wit_id (e.g., #ms0005 -> check if Iranian/Indian)
    # This is simplified - ideally load from witness_groups.yaml
    witness_group = None  # TODO: load from witness_groups.yaml
    
    # Classify using YAML rules
    if ops:
        classification = classify_by_rules(ops, rules, witness_group)
        if classification:
            return classification
    
    # Default: if no YAML rule matched, treat as trivial
    # (spacing/segmentation/compound differences are structural, not philologically meaningful)
    return "trivial"


def tag_apparatus_xml(input_path: str, output_path: str,
                     policy_path: str, families_path: str):
    """Add @type attributes to all <rdg> elements in apparatus XML."""
    
    # Load classification configuration
    rules = load_classification_rules(policy_path)
    families = load_orthography_families(families_path)
    
    print(f"Loaded {len(rules)} classification rules")
    print(f"Loaded {len(families)} orthography families")
    
    # Parse XML
    tree = etree.parse(input_path)
    root = tree.getroot()
    
    # Find namespace (if any)
    nsmap = root.nsmap
    ns = {'tei': nsmap[None]} if None in nsmap else {}
    
    # Find all apparatus entries
    app_count = 0
    rdg_count = 0
    type_counts = {"trivial": 0, "meaningful": 0, "missing": 0, "unknown": 0}
    
    # Collect lemmas in document order for adjacency-based merge detection
    apps = root.xpath('.//tei:app', namespaces=ns) if ns else root.xpath('.//app')
    lem_texts: List[str] = []
    for app in apps:
        lem_el = app.find('.//tei:lem' if ns else './/lem', namespaces=ns if ns else None)
        if lem_el is None:
            lem_texts.append('')
        else:
            lem_texts.append(''.join(lem_el.itertext()).strip())

    for idx, app in enumerate(apps):
        app_count += 1
        lem_text = lem_texts[idx]
        prev_lem = lem_texts[idx - 1] if idx > 0 else None
        next_lem = lem_texts[idx + 1] if idx + 1 < len(lem_texts) else None

        for rdg in app.findall('.//tei:rdg' if ns else './/rdg', namespaces=ns if ns else None):
            rdg_count += 1
            rdg_text = ''.join(rdg.itertext()).strip()
            wit_id = rdg.get('wit', '')
            rdg_type = classify_rdg(lem_text, rdg_text, wit_id, rules, families, prev_lem, next_lem)
            rdg.set('type', rdg_type)
            type_counts[rdg_type] += 1
    
    # Write output
    tree.write(output_path, encoding='utf-8', xml_declaration=True, pretty_print=True)
    
    # Print statistics
    print(f"✅ Tagged apparatus written to: {output_path}")
    print(f"   {app_count} apparatus entries processed")
    print(f"   {rdg_count} readings tagged:")
    for rdg_type, count in sorted(type_counts.items()):
        pct = 100.0 * count / rdg_count if rdg_count > 0 else 0
        print(f"      {rdg_type}: {count} ({pct:.1f}%)")


def main():
    parser = argparse.ArgumentParser(description="Tag apparatus readings with @type attribute using YAML rules")
    parser.add_argument('--input', required=True, help='Input apparatus XML file')
    parser.add_argument('--output', required=True, help='Output tagged apparatus XML file')
    parser.add_argument('--policy', default='res/Yasna/meta/classification_policy.yaml',
                       help='Path to classification_policy.yaml')
    parser.add_argument('--families', default='res/Yasna/meta/orthography_families_v4.yaml',
                       help='Path to orthography_families_v4.yaml')
    
    args = parser.parse_args()
    tag_apparatus_xml(args.input, args.output, args.policy, args.families)


if __name__ == '__main__':
    main()
