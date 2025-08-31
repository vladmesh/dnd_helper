## Spells enrichment from auxiliary JSON

Scope:
- Add missing caster classes to DTN spells by English name match
- Optionally add `ritual` and `concentration` flags when derivable

Data sources:
- DTN: `DnD5e_spells_BD.dtn` contains `allSpells`: list of objects with `en`/`ru` blocks, including `name`, `duration`, `components`, etc.
- Auxiliary: `spells.json` is an array of objects with `name`, `description`, and `properties` (e.g., `Level`, `School`, `Components`, optional class hints).

Findings:
- DTN has no explicit `classes`. English names are present under `allSpells[].en.name` and are suitable as stable keys.
- `concentration` can often be inferred from DTN `duration`: English contains "Concentration" text; Russian contains "конц" abbreviation.
- `ritual` is not explicitly present in DTN; it may appear in auxiliary as `Ritual: Yes` or in description as `(ritual)`.
- Auxiliary `properties` does not always include explicit `Classes`, but class lists can appear in `description` as `Classes: ...`, `Available For: ...`, or `Spell Lists: ...`.

Implementation:
- Script `enrich_spells_from_json.py`:
  - Index `spells.json` by English `name`
  - Extract classes from `properties[Classes|Class|Available For|Spell Lists]` or from `description` fallback
  - Extract `ritual` from `properties.Ritual` or `(ritual)` marker
  - Derive `concentration` from auxiliary (properties/description) with fallback to DTN `duration`
  - Update both `en` and `ru` blocks with discovered fields: `classes: list[str]`, `ritual: bool`, `concentration: bool`
  - Minimal edits: add only when value is known

Open questions / next steps:
- Class name normalization: current mapping covers core PHB classes. Extend if needed (homebrew/UA variants).
- Additional fields potentially derivable from auxiliary:
  - `material_desc`: already present in DTN via `materials`, no change required
  - `range_feet` numeric: not implemented; would require parsing ranges (out of scope per architecture policy)
  - `components` flags: present in DTN as `components` string; conversion to structured flags is handled during API seeding, not in DTN

How to run:
```
python3 enrich_spells_from_json.py \
  --dtn DnD5e_spells_BD.dtn \
  --spells-json spells.json \
  --out DnD5e_spells_BD.enriched.dtn
```

If the result looks good, overwrite in place:
```
python3 enrich_spells_from_json.py --in-place
```


