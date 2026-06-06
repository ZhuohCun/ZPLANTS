from __future__ import annotations

from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from init_db import validate_mysql_artifacts


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    schema_sql = (base_dir / 'schema_mysql.sql').read_text(encoding='utf-8')
    seed_sql = (base_dir / 'seed_mysql.sql').read_text(encoding='utf-8')
    validate_mysql_artifacts(schema_sql, seed_sql)
    print('MySQL schema and seed validation passed.')


if __name__ == '__main__':
    main()
