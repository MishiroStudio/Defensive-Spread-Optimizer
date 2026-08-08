"""Cordy's Lab regulation importer — version 3.

Import Pokémon Champions VGC regulation pools from Pokémon Showdown.

Run from the project root with:

    python3 tools/import_regulations_v3.py

The importer reads data/pokemon_v2.json, discovers the Pokémon Champions VGC
regulations currently present in Pokémon Showdown, maps
Showdown species/form IDs to the local PokéAPI-based pokemon_id values, and
writes data/regulations.json.

The currently active regulation is detected from Showdown's ``vgc`` alias.
Only actual regulations are stored; ``National Dex`` remains a dynamic scope in
apps/pokedex/main.py so the full Pokédex is never duplicated in this file.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_NAME = "regulations.json"

SHOWDOWN_RAW_ROOT = (
    "https://raw.githubusercontent.com/smogon/pokemon-showdown/master"
)
FORMATS_URL = f"{SHOWDOWN_RAW_ROOT}/config/formats.ts"
ALIASES_URL = f"{SHOWDOWN_RAW_ROOT}/data/aliases.ts"
FORMATS_DATA_URL = (
    f"{SHOWDOWN_RAW_ROOT}/data/mods/{{mod}}/formats-data.ts"
)
USER_AGENT = "CordysLab-Regulation-Importer/3.0"

FORMAT_NAME_RE = re.compile(
    r"^\[Gen 9 Champions\] VGC (?P<year>\d{4}) Reg "
    r"(?P<code>[A-Za-z0-9-]+)$"
)

# A few Showdown IDs abbreviate gender/form names compared with PokéAPI.
# Candidate generation handles most forms automatically; these aliases cover
# the common cases where the canonical Showdown ID is intentionally shorter.
SHOWDOWN_ID_ALIASES: dict[str, tuple[str, ...]] = {
    "urshifusinglestrike": ("urshifu",),
    "basculegionfemale": ("basculegionf",),
    "basculegionmale": ("basculegionm",),
    "indeedeefemale": ("indeedeef",),
    "indeedeemale": ("indeedee",),
    # Female Meowstic is a separate Showdown species ID, but its formats-data
    # entry inherits from the base Meowstic entry and is therefore often not
    # written explicitly in formats-data.ts.
    "meowsticfemale": ("meowsticf", "meowstic"),
    "meowsticmale": ("meowstic",),
    # Champions has separate male/female Mega Meowstic IDs in Showdown. The
    # local Pokédex may expose a single generic Mega Meowstic form.
    "meowsticmega": ("meowsticmmega", "meowsticfmega"),
    "meowsticmegameowstic": ("meowsticmmega", "meowsticfmega"),
    "oinkolognefemale": ("oinkolognef",),
    "oinkolognemale": ("oinkologne",),
    "unfezantfemale": ("unfezantf",),
    "unfezantmale": ("unfezant",),
    "frillishfemale": ("frillishf",),
    "frillishmale": ("frillish",),
    "jellicentfemale": ("jellicentf",),
    "jellicentmale": ("jellicent",),
    # PokéAPI/local display names are more verbose than Showdown's IDs.
    "taurospaldeanformcombatbreed": ("taurospaldeacombat",),
    "taurospaldeanformblazebreed": ("taurospaldeablaze",),
    "taurospaldeanformaquabreed": ("taurospaldeaaqua",),
    "taurospaldeacombatbreed": ("taurospaldeacombat",),
    "taurospaldeablazebreed": ("taurospaldeablaze",),
    "taurospaldeaaquabreed": ("taurospaldeaaqua",),
    # Battle-state forms are not always separate entries in formats-data.ts.
    # They should follow the legality of the selectable base form.
    "meloettapirouette": ("meloetta",),
    "meloettapirouetteforme": ("meloetta",),
    "miniormeteor": ("minior",),
    "miniormeteorform": ("minior",),
    "eiscuenoice": ("eiscue",),
    "eiscuenoiceface": ("eiscue",),
    "palafinhero": ("palafin",),
    "terapagosterastal": ("terapagos",),
    "terapagosterastalform": ("terapagos",),
}


def fetch_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError(f"Could not download {url}: {error}") from error


def load_json(path: Path) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"Missing data file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {path}: {error}") from error


def write_json_atomically(data: dict[str, Any], output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_file.with_name(
        f"{output_file.stem}.tmp{output_file.suffix}"
    )
    with temporary.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
        file.write("\n")
    temporary.replace(output_file)


def to_showdown_id(value: str) -> str:
    """Approximate Showdown's toID() for Pokémon/form labels."""
    normalized = unicodedata.normalize("NFKD", value).casefold()
    normalized = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return re.sub(r"[^a-z0-9]", "", normalized)


def iter_top_level_object_blocks(text: str) -> list[tuple[str, str]]:
    """Extract ``key: { ... }`` entries from a TS exported object."""
    lines = text.splitlines()
    entries: list[tuple[str, str]] = []
    index = 0
    key_re = re.compile(r"^\t([a-zA-Z0-9_]+)\s*:\s*\{\s*$")

    while index < len(lines):
        match = key_re.match(lines[index])
        if match is None:
            index += 1
            continue

        key = match.group(1)
        block_lines = [lines[index]]
        depth = lines[index].count("{") - lines[index].count("}")
        index += 1
        while index < len(lines) and depth > 0:
            line = lines[index]
            block_lines.append(line)
            depth += line.count("{") - line.count("}")
            index += 1
        entries.append((key, "\n".join(block_lines)))

    return entries


def parse_formats_data(text: str) -> tuple[set[str], set[str]]:
    """Return all known Showdown form IDs and the legal subset."""
    all_ids: set[str] = set()
    legal_ids: set[str] = set()

    for showdown_id, block in iter_top_level_object_blocks(text):
        all_ids.add(showdown_id)
        is_nonstandard = re.search(r"\bisNonstandard\s*:", block) is not None
        is_illegal = (
            re.search(
                r"\btier\s*:\s*['\"]Illegal['\"]",
                block,
            )
            is not None
        )
        if not is_nonstandard and not is_illegal:
            legal_ids.add(showdown_id)

    if not all_ids:
        raise ValueError("Could not parse any Pokémon from Showdown formats-data.ts")
    return all_ids, legal_ids


def extract_ts_object_blocks(text: str) -> list[str]:
    """Extract top-level object literals from Showdown's Formats array."""
    blocks: list[str] = []
    depth = 0
    start: int | None = None
    quote: str | None = None
    escape = False

    for index, char in enumerate(text):
        if quote is not None:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote:
                quote = None
            continue

        if char in ("'", '"', "`"):
            quote = char
            continue
        if char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                blocks.append(text[start : index + 1])
                start = None

    return blocks


def parse_champions_vgc_formats(text: str) -> list[dict[str, Any]]:
    """Discover non-Bo3 Champions VGC regulations and their Showdown mods."""
    records: list[dict[str, Any]] = []
    name_re = re.compile(r"\bname\s*:\s*['\"]([^'\"]+)['\"]")
    mod_re = re.compile(r"\bmod\s*:\s*['\"]([^'\"]+)['\"]")

    for source_order, block in enumerate(extract_ts_object_blocks(text)):
        name_match = name_re.search(block)
        if name_match is None:
            continue
        format_name = name_match.group(1)
        if "(Bo3)" in format_name:
            continue
        parsed = FORMAT_NAME_RE.match(format_name)
        if parsed is None:
            continue
        mod_match = mod_re.search(block)
        if mod_match is None:
            raise ValueError(f"No Showdown mod found for {format_name}")

        code = parsed.group("code").upper()
        records.append(
            {
                "id": f"reg-{code.casefold()}",
                "name": f"Regulation {code}",
                "format_name": format_name,
                "year": int(parsed.group("year")),
                "code": code,
                "mod": mod_match.group(1),
                "source_order": source_order,
            }
        )

    if not records:
        raise ValueError("No Pokémon Champions VGC regulations found in formats.ts")

    # Deduplicate identical regulation entries while retaining their source order.
    unique: dict[str, dict[str, Any]] = {}
    for record in records:
        unique.setdefault(str(record["id"]), record)
    return list(unique.values())


def parse_current_vgc_format(aliases_text: str) -> str:
    match = re.search(
        r"(?:^|[,\n{])\s*vgc\s*:\s*['\"]([^'\"]+)['\"]",
        aliases_text,
        flags=re.MULTILINE,
    )
    if match is None:
        raise ValueError("Could not detect Showdown's current 'vgc' alias.")
    return match.group(1)


def flatten_forms(pokemon_data: Any) -> list[dict[str, Any]]:
    if not isinstance(pokemon_data, list):
        raise ValueError("pokemon_v2.json must contain a JSON list.")

    forms: list[dict[str, Any]] = []
    for species in pokemon_data:
        if not isinstance(species, dict):
            continue
        dex = species.get("dex")
        species_forms = species.get("forms")
        if not isinstance(dex, int) or not isinstance(species_forms, list):
            raise ValueError("pokemon_v2.json contains an invalid species record.")
        for form in species_forms:
            if not isinstance(form, dict):
                raise ValueError("pokemon_v2.json contains an invalid form record.")
            pokemon_id = form.get("pokemon_id")
            if not isinstance(pokemon_id, int):
                raise ValueError("pokemon_v2.json contains an invalid pokemon_id.")
            forms.append({**form, "national_dex": dex})
    return forms


def _showdown_candidate_variants(showdown_id: str) -> list[str]:
    """Return conservative naming variants used by PokéAPI/local form labels."""
    variants = [showdown_id]

    def add(value: str) -> None:
        if value and value not in variants:
            variants.append(value)

    # PokéAPI/local labels sometimes contain descriptive words Showdown omits.
    for value in tuple(variants):
        add(value.replace("paldean", "paldea"))
        add(value.replace("forme", ""))
        add(value.replace("form", ""))
        add(value.replace("breed", ""))

    # Run the same reductions again on the newly generated strings so a label
    # such as "Paldean Form (Combat Breed)" can become "paldeacombat".
    for value in tuple(variants):
        add(value.replace("paldean", "paldea"))
        add(value.replace("forme", ""))
        add(value.replace("form", ""))
        add(value.replace("breed", ""))

    return variants


def form_showdown_candidates(form: dict[str, Any]) -> list[str]:
    candidates: list[str] = []

    def add(value: str) -> None:
        showdown_id = to_showdown_id(value)
        if not showdown_id:
            return
        for variant in _showdown_candidate_variants(showdown_id):
            if variant not in candidates:
                candidates.append(variant)
            for alias in SHOWDOWN_ID_ALIASES.get(variant, ()):
                if alias not in candidates:
                    candidates.append(alias)

    api_name = str(form.get("api_name", ""))
    add(api_name)

    # The Pokémon importer deliberately retains all four Squawkabilly
    # plumages. Showdown normally has specific IDs for the non-green forms,
    # but some format files collapse cosmetic forms to the base species. Keep
    # the specific candidate first and the family representative last.
    api_tokens = set(api_name.split("-"))
    if api_name.startswith("squawkabilly-"):
        showdown_by_plumage = {
            "green": "squawkabilly",
            "blue": "squawkabillyblue",
            "yellow": "squawkabillyyellow",
            "white": "squawkabillywhite",
        }
        for plumage, showdown_id in showdown_by_plumage.items():
            if plumage in api_tokens:
                add(showdown_id)
                add("squawkabilly")
                break

    # Likewise retain all three Tatsugiri appearances and all three Mega
    # appearances. The upstream API may place the ``mega`` token before or
    # after the form token, whereas Showdown uses compact IDs such as
    # tatsugiridroopymega. The generic Mega alias resolves to Curly-Mega, so
    # that is used only as a final legality fallback for the cosmetic family.
    if api_name.startswith("tatsugiri-"):
        form_token = next(
            (
                token
                for token in ("curly", "droopy", "stretchy")
                if token in api_tokens
            ),
            None,
        )
        if form_token is not None:
            if "mega" in api_tokens:
                add(f"tatsugiri{form_token}mega")
                add("tatsugiricurlymega")
            else:
                add("tatsugiri" if form_token == "curly" else f"tatsugiri{form_token}")
                add("tatsugiri")

    english_name = str(form.get("name_en", ""))
    add(english_name)

    # The displayed name of the default form may include a form suffix even
    # though Showdown uses the bare species ID (Deoxys, Oricorio, Lycanroc…).
    if bool(form.get("is_default")) and " (" in english_name:
        add(english_name.split(" (", 1)[0])

    # Generic gender abbreviation used by several Showdown form IDs.
    for candidate in tuple(candidates):
        if candidate.endswith("female"):
            shortened = candidate[: -len("female")] + "f"
            if shortened not in candidates:
                candidates.append(shortened)
        if candidate.endswith("male"):
            shortened = candidate[: -len("male")] + "m"
            if shortened not in candidates:
                candidates.append(shortened)

    return candidates


def resolve_form_showdown_id(
    form: dict[str, Any],
    known_ids: set[str],
) -> str | None:
    for candidate in form_showdown_candidates(form):
        if candidate in known_ids:
            return candidate
    return None


def regulation_ids_for_mod(
    forms: list[dict[str, Any]],
    known_ids: set[str],
    legal_ids: set[str],
) -> tuple[list[int], list[dict[str, Any]]]:
    """Map local forms to the legal Pokémon pool for one Showdown mod.

    ``learnsets.json`` is intentionally not used as a legality oracle here.
    A form can have imported Champions move data while still being unavailable
    in a particular regulation, and battle-state forms may not have their own
    formats-data entry. Showdown's regulation mod remains the source of truth.
    """
    local_ids: list[int] = []
    unresolved_forms: list[dict[str, Any]] = []

    for form in forms:
        pokemon_id = int(form["pokemon_id"])
        showdown_id = resolve_form_showdown_id(form, known_ids)
        if showdown_id is None:
            unresolved_forms.append(form)
            continue
        if showdown_id in legal_ids:
            local_ids.append(pokemon_id)

    return sorted(set(local_ids)), unresolved_forms


def import_regulations(data_dir: Path) -> tuple[Path, dict[str, Any]]:
    pokemon_data = load_json(data_dir / "pokemon_v2.json")
    forms = flatten_forms(pokemon_data)
    output_file = data_dir / OUTPUT_NAME

    # Preserve already archived regulations if Showdown later removes their
    # format definitions. Newly discovered data always wins for matching IDs.
    existing_records: list[dict[str, Any]] = []
    if output_file.is_file():
        existing = load_json(output_file)
        if isinstance(existing, dict) and isinstance(
            existing.get("regulations"), list
        ):
            existing_records = [
                dict(record)
                for record in existing["regulations"]
                if isinstance(record, dict)
            ]

    print("Downloading Pokémon Showdown regulation metadata …")
    formats_text = fetch_text(FORMATS_URL)
    aliases_text = fetch_text(ALIASES_URL)
    formats = parse_champions_vgc_formats(formats_text)
    current_format_name = parse_current_vgc_format(aliases_text)

    current_record = next(
        (
            record
            for record in formats
            if record["format_name"] == current_format_name
        ),
        None,
    )
    if current_record is None:
        raise ValueError(
            "Showdown's current vgc alias points to a format that was not "
            f"found in config/formats.ts: {current_format_name}"
        )

    # Current first; historical regulations afterwards, newest to oldest.
    historical = sorted(
        (
            record
            for record in formats
            if record["id"] != current_record["id"]
        ),
        key=lambda record: int(record["source_order"]),
        reverse=True,
    )
    ordered = [current_record, *historical]

    parsed_mods: dict[str, tuple[set[str], set[str]]] = {}
    regulation_records: list[dict[str, Any]] = []
    unresolved_by_mod: dict[str, list[str]] = {}

    for record in ordered:
        mod = str(record["mod"])
        if mod not in parsed_mods:
            url = FORMATS_DATA_URL.format(mod=mod)
            print(f"Downloading Showdown mod {mod} …")
            parsed_mods[mod] = parse_formats_data(fetch_text(url))
        known_ids, legal_ids = parsed_mods[mod]

        pokemon_ids, unresolved = regulation_ids_for_mod(
            forms,
            known_ids,
            legal_ids,
        )
        if unresolved:
            unresolved_by_mod[mod] = sorted(
                {
                    str(form.get("name_en") or form.get("api_name"))
                    for form in unresolved
                }
            )

        regulation_records.append(
            {
                "id": record["id"],
                "name": record["name"],
                "format_name": record["format_name"],
                "year": record["year"],
                "code": record["code"],
                "mod": mod,
                "status": (
                    "current"
                    if record["id"] == current_record["id"]
                    else "expired"
                ),
                "pokemon_ids": pokemon_ids,
            }
        )
        print(f"  {record['name']}: {len(pokemon_ids)} local forms")

    discovered_ids = {str(record["id"]) for record in regulation_records}
    for old_record in existing_records:
        old_id = old_record.get("id")
        if (
            not isinstance(old_id, str)
            or old_id in discovered_ids
            or old_id == current_record["id"]
        ):
            continue
        preserved = dict(old_record)
        preserved["status"] = "expired"
        regulation_records.append(preserved)
        discovered_ids.add(old_id)
        print(f"  Preserved archived {preserved.get('name', old_id)}")

    output = {
        "schema_version": 1,
        "source": {
            "name": "Pokémon Showdown",
            "repository": "smogon/pokemon-showdown",
            "formats_url": FORMATS_URL,
            "aliases_url": ALIASES_URL,
            "imported_at": datetime.now(timezone.utc).isoformat(),
        },
        "current_regulation_id": current_record["id"],
        "regulations": regulation_records,
    }

    write_json_atomically(output, output_file)

    if unresolved_by_mod:
        print()
        print("Unresolved local form names by Showdown mod:")
        for mod, names in unresolved_by_mod.items():
            print(f"  {mod}: {', '.join(names[:20])}")
            if len(names) > 20:
                print(f"    … and {len(names) - 20} more")
        print(
            "These entries are diagnostic only. They are skipped unless an "
            "explicit Showdown mapping is added. Regulation legality itself "
            "comes from the selected Showdown mod."
        )

    return output_file, output


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Import Pokémon Champions VGC regulation pools from Pokémon Showdown."
        )
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing pokemon_v2.json.",
    )
    return parser.parse_args()


def main() -> None:
    print("Cordy\'s Lab regulation importer v3")
    arguments = parse_arguments()
    output_file, output = import_regulations(arguments.data_dir)
    print()
    print(f"Current regulation: {output['current_regulation_id']}")
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    main()
