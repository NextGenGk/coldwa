import re
import pandas as pd

REQUIRED_COLUMNS = ["mobile", "name", "clinic_name", "location"]

COUNTRY_CODES = {
    "91 - India": "91",
    "1 - USA / Canada": "1",
    "44 - UK": "44",
    "61 - Australia": "61",
    "971 - UAE": "971",
    "966 - Saudi Arabia": "966",
    "65 - Singapore": "65",
    "60 - Malaysia": "60",
    "92 - Pakistan": "92",
    "880 - Bangladesh": "880",
}


class SafeDict(dict):
    """Returns the literal placeholder if a key is missing."""
    def __missing__(self, key):
        return "{" + key + "}"


def format_phone_number(raw: str, default_country_code: str = "91") -> str:
    """
    Normalise a raw phone number string to E.164 format (+XXXXXXXXXXX).
    - Strips all non-digit characters
    - If exactly 10 digits, prepends default_country_code
    - Prepends '+' if missing
    - Raises ValueError for invalid lengths
    """
    digits = re.sub(r"\D", "", str(raw))
    if len(digits) == 10:
        digits = default_country_code + digits
    if not (10 <= len(digits) <= 15):
        raise ValueError(
            f"'{raw}' → {len(digits)} digits after stripping — expected 10-15"
        )
    return "+" + digits


def substitute_template(template: str, row: dict) -> str:
    """
    Replace {name}, {clinic_name}, {location} (and any other keys) with
    values from row. Missing keys are left as-is so the user can spot them.
    """
    safe = SafeDict(
        {k: (str(v) if pd.notna(v) else "") for k, v in row.items()}
    )
    return template.format_map(safe)


def validate_dataframe(df: pd.DataFrame):
    """
    Returns (is_valid: bool, errors: list[str]).
    Checks required columns and that the file is not empty.
    """
    errors = []
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        errors.append(f"Missing required columns: {missing}")
    if df.dropna(how="all").empty:
        errors.append("The file contains no data rows.")
    return (len(errors) == 0, errors)
