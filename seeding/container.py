from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any, Dict, List


def upsert_enum_and_ui_translations_in_container(enum_rows: List[Dict[str, Any]], ui_rows: List[Dict[str, Any]]) -> None:
    payload = json.dumps({"enum": enum_rows, "ui": ui_rows}, ensure_ascii=False)
    inline = (
        "import sys,json;\n"
        "from sqlmodel import Session;\n"
        "from sqlalchemy.dialects.postgresql import insert as pg_insert;\n"
        "from dnd_helper_api.db import engine;\n"
        "from shared_models.enum_translation import EnumTranslation;\n"
        "from shared_models.ui_translation import UiTranslation;\n"
        "data=json.load(sys.stdin); enum=data.get('enum') or []; ui=data.get('ui') or [];\n"
        "with Session(engine) as session:\n"
        "    if enum:\n"
        "        t=EnumTranslation.__table__;\n"
        "        s=pg_insert(t).values(enum);\n"
        "        s=s.on_conflict_do_update(index_elements=[t.c.enum_type,t.c.enum_value,t.c.lang], set_={'label': s.excluded.label, 'description': s.excluded.description, 'synonyms': s.excluded.synonyms});\n"
        "        session.exec(s);\n"
        "    if ui:\n"
        "        t=UiTranslation.__table__;\n"
        "        s=pg_insert(t).values(ui);\n"
        "        s=s.on_conflict_do_update(index_elements=[t.c.namespace,t.c.key,t.c.lang], set_={'text': s.excluded.text});\n"
        "        session.exec(s);\n"
        "    session.commit()\n"
    )
    proc = subprocess.run(
        [
            "docker",
            "compose",
            "exec",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "-T",
            "api",
            "python",
            "-c",
            inline,
        ],
        input=payload,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
        raise SystemExit(proc.returncode)


