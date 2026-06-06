from __future__ import annotations

from pathlib import Path
import re
from collections import defaultdict


from config import Config


CREATE_TABLE_RE = re.compile(r'CREATE TABLE\s+([`"]?)(\w+)\1\s*\((.*?)\)\s*ENGINE=', re.S | re.I)
INSERT_RE = re.compile(r'INSERT INTO\s+([`"]?)(\w+)\1\s*\((.*?)\)\s*VALUES\s*(.*?);', re.S | re.I)
FK_RE = re.compile(r'FOREIGN KEY\s*\((`?)(\w+)\1\)\s*REFERENCES\s+(`?)(\w+)\3\s*\((`?)(\w+)\5\)', re.I)
TABLE_NAME_RE = re.compile(r'^[a-z]+(?:_[a-z]+)*$')


def build_connection(database: str | None = None, *, autocommit: bool = False):
    import pymysql
    return pymysql.connect(
        host=Config.MYSQL_HOST,
        port=int(Config.MYSQL_PORT),
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=database,
        charset=Config.MYSQL_CHARSET,
        autocommit=autocommit,
        cursorclass=__import__('pymysql').cursors.DictCursor,
    )


def split_sql(text: str):
    parts = []
    current = []
    in_single = False
    in_double = False
    escape = False
    for ch in text:
        current.append(ch)
        if escape:
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            continue
        if ch == ';' and not in_single and not in_double:
            statement = ''.join(current).strip()
            if statement:
                parts.append(statement[:-1].strip())
            current = []
    tail = ''.join(current).strip()
    if tail:
        parts.append(tail)
    return [item for item in parts if item]


def _parse_schema(schema_sql: str):
    table_order: list[str] = []
    table_defs: dict[str, dict] = {}
    for match in CREATE_TABLE_RE.finditer(schema_sql):
        table_name = match.group(2)
        table_order.append(table_name)
        body = match.group(3)
        columns = []
        nullable = {}
        foreign_keys = {}
        foreign_key_actions = {}
        for raw_line in body.splitlines():
            line = raw_line.strip().rstrip(',')
            if not line:
                continue
            fk_match = FK_RE.search(line)
            if fk_match:
                foreign_keys[fk_match.group(2)] = (fk_match.group(4), fk_match.group(6))
                foreign_key_actions[fk_match.group(2)] = {
                    'line': line,
                    'uses_set_null': 'SET NULL' in line.upper(),
                }
                continue
            upper = line.upper()
            if upper.startswith(('PRIMARY KEY', 'KEY ', 'UNIQUE KEY', 'CONSTRAINT ')):
                continue
            column_match = re.match(r'`?(\w+)`?\s+', line)
            if not column_match:
                continue
            column_name = column_match.group(1)
            columns.append(column_name)
            nullable[column_name] = 'NOT NULL' not in upper
        table_defs[table_name] = {
            'columns': columns,
            'nullable': nullable,
            'foreign_keys': foreign_keys,
            'foreign_key_actions': foreign_key_actions,
        }
    return table_order, table_defs


def _split_tuple_values(text: str):
    values = []
    current = []
    in_single = False
    escape = False
    for ch in text:
        if escape:
            current.append(ch)
            escape = False
            continue
        if ch == '\\':
            current.append(ch)
            escape = True
            continue
        if ch == "'":
            current.append(ch)
            in_single = not in_single
            continue
        if ch == ',' and not in_single:
            values.append(''.join(current).strip())
            current = []
            continue
        current.append(ch)
    values.append(''.join(current).strip())
    return values


def _parse_scalar(token: str):
    value = token.strip()
    if value.upper() == 'NULL':
        return None
    if value.startswith("'") and value.endswith("'"):
        inner = value[1:-1]
        return inner.replace("\\'", "'").replace('\\\\', '\\')
    if re.fullmatch(r'-?\d+', value):
        return int(value)
    if re.fullmatch(r'-?\d+\.\d+', value):
        return float(value)
    return value


def _split_value_tuples(blob: str):
    tuples = []
    current = []
    depth = 0
    in_single = False
    escape = False
    started = False
    for ch in blob:
        if not started:
            if ch.isspace() or ch == ',':
                continue
            if ch == '(':
                current = ['(']
                depth = 1
                started = True
            continue
        if escape:
            current.append(ch)
            escape = False
            continue
        if ch == '\\':
            current.append(ch)
            escape = True
            continue
        if ch == "'":
            current.append(ch)
            in_single = not in_single
            continue
        if ch == '(' and not in_single:
            depth += 1
        elif ch == ')' and not in_single:
            depth -= 1
        current.append(ch)
        if depth == 0:
            tuples.append(''.join(current))
            current = []
            started = False
    return tuples


def _parse_seed(seed_sql: str):
    insert_order: list[str] = []
    inserted_rows: dict[str, list[dict]] = defaultdict(list)
    for match in INSERT_RE.finditer(seed_sql):
        table_name = match.group(2)
        insert_order.append(table_name)
        columns = [item.strip(' `') for item in match.group(3).split(',')]
        for tuple_text in _split_value_tuples(match.group(4)):
            inner = tuple_text[1:-1]
            values = [_parse_scalar(item) for item in _split_tuple_values(inner)]
            if len(values) != len(columns):
                raise RuntimeError(f'Seed parse failed for table {table_name}: column count does not match value count.')
            inserted_rows[table_name].append(dict(zip(columns, values)))
    return insert_order, inserted_rows


def validate_mysql_artifacts(schema_sql: str, seed_sql: str) -> None:
    table_order, table_defs = _parse_schema(schema_sql)
    if not table_order:
        raise RuntimeError('MySQL schema validation failed: no CREATE TABLE statements were found.')

    for table_name in table_order:
        if not TABLE_NAME_RE.fullmatch(table_name):
            raise RuntimeError(f'MySQL schema validation failed: invalid table name {table_name}. Table names must use lowercase snake_case English words only.')
        if re.search(r'\d', table_name):
            raise RuntimeError(f'MySQL schema validation failed: table name {table_name} contains digits.')

    order_index = {name: idx for idx, name in enumerate(table_order)}
    for table_name, table_meta in table_defs.items():
        for column_name, (ref_table, ref_column) in table_meta['foreign_keys'].items():
            if ref_table not in order_index:
                raise RuntimeError(f'MySQL schema validation failed: {table_name}.{column_name} references unknown table {ref_table}.')
            if order_index[ref_table] > order_index[table_name]:
                raise RuntimeError(f'MySQL schema validation failed: {table_name} is created before referenced table {ref_table}.')
            fk_action = (table_meta.get('foreign_key_actions') or {}).get(column_name, {})
            if fk_action.get('uses_set_null') and not table_meta['nullable'].get(column_name, False):
                raise RuntimeError(f'MySQL schema validation failed: {table_name}.{column_name} uses SET NULL but is not nullable.')
            if ref_column not in table_defs.get(ref_table, {}).get('columns', []):
                raise RuntimeError(f'MySQL schema validation failed: {table_name}.{column_name} references missing column {ref_table}.{ref_column}.')

    insert_order, inserted_rows = _parse_seed(seed_sql)
    inserted_ids: dict[str, set] = defaultdict(set)
    for table_name in insert_order:
        if table_name not in table_defs:
            raise RuntimeError(f'MySQL seed validation failed: INSERT targets unknown table {table_name}.')
        for row in inserted_rows[table_name]:
            if 'id' in row and row['id'] is not None:
                inserted_ids[table_name].add(row['id'])
        for row in inserted_rows[table_name]:
            for column_name, (ref_table, ref_column) in table_defs[table_name]['foreign_keys'].items():
                value = row.get(column_name)
                if value is None:
                    continue
                if ref_column != 'id':
                    continue
                if value not in inserted_ids[ref_table]:
                    raise RuntimeError(
                        f'MySQL seed validation failed: {table_name}.{column_name}={value} references missing {ref_table}.{ref_column}. '
                        f'Please check insert order or seed values.'
                    )


def recreate_database() -> None:
    root_conn = build_connection(None, autocommit=True)
    try:
        with root_conn.cursor() as cursor:
            cursor.execute('SET NAMES utf8mb4')
            cursor.execute('SET FOREIGN_KEY_CHECKS = 0')
            cursor.execute(f'DROP DATABASE IF EXISTS `{Config.MYSQL_DATABASE}`')
            cursor.execute(
                f"CREATE DATABASE `{Config.MYSQL_DATABASE}` CHARACTER SET {Config.MYSQL_CHARSET} COLLATE {Config.MYSQL_CHARSET}_general_ci"
            )
            cursor.execute('SET FOREIGN_KEY_CHECKS = 1')
    finally:
        root_conn.close()


def execute_sql_file(cursor, sql_text: str) -> None:
    for statement in split_sql(sql_text):
        cursor.execute(statement)


def main():
    schema_path = Path(__file__).resolve().parent / 'database' / 'schema_mysql.sql'
    seed_path = Path(__file__).resolve().parent / 'database' / 'seed_mysql.sql'
    schema_sql = schema_path.read_text(encoding='utf-8')
    seed_sql = seed_path.read_text(encoding='utf-8')

    validate_mysql_artifacts(schema_sql, seed_sql)
    recreate_database()

    conn = build_connection(Config.MYSQL_DATABASE, autocommit=False)
    try:
        with conn.cursor() as cursor:
            cursor.execute('SET NAMES utf8mb4')
            cursor.execute('SET FOREIGN_KEY_CHECKS = 0')
            execute_sql_file(cursor, schema_sql)
            execute_sql_file(cursor, seed_sql)
            cursor.execute('SET FOREIGN_KEY_CHECKS = 1')
            cursor.execute("SHOW TABLES LIKE 'care_methods'")
            if not cursor.fetchone():
                raise RuntimeError('MySQL initialization verification failed: care_methods table was not created.')
            cursor.execute('select count(*) as total from recognitions')
            recognitions_total = int((cursor.fetchone() or {}).get('total') or 0)
            cursor.execute('select count(*) as total from feedbacks')
            feedback_total = int((cursor.fetchone() or {}).get('total') or 0)
            if recognitions_total < 1 or feedback_total < 1:
                raise RuntimeError('MySQL initialization verification failed: seed data was not written completely.')
        conn.commit()
        print('MySQL database initialized successfully.')
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()
