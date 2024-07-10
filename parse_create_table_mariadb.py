from typing import (
    Dict,
    Any,
    List,
)

import logging
import sys

# import json
import yaml

from lark import (
    Lark,
    logger,
    Transformer,
    v_args,
    # Visitor,
)

logger.setLevel(logging.WARN)

FILE = "glpi-empty.sql"
VERBOSE = 0

# we expect all these cols to have the same definition
COMMON_COLS: List[str] = [
    "id",
    "name",
    "comment",
    "date_creation",
    "date_mod",
    "is_deleted",
    "entities_id",
    "date_update",
]


class IndentDumper(yaml.Dumper):  # pylint: disable=too-many-ancestors
    def increase_indent(
        self,
        flow=False,
        indentless=False,
    ):
        return super().increase_indent(flow, False)


class TransformProcessor(Transformer):
    def __init__(self):
        super().__init__()
        self.tables = {}

    def start(self, z):
        _ = z
        return self.tables

    def ignore_until_semicolon(self, z):
        _ = z
        return ""

    def name(self, z):
        return str(z[0])

    def string(self, z):
        if z[0][0] == "'":
            return z[0][1:-1]

        return z[0]

    def number(self, z):
        if "." in str(z):
            return float(z[0])
        return int(z[0])

    def identifier(self, z):
        if VERBOSE:
            what = "IDENTIFIER"
            print(f"{what}: {len(z)} {z[0]}", file=sys.stderr)
        return str(z[0])

    def unsigned(self, z):
        _ = z
        return "unsigned"

    def expression(self, z):
        return z[0]

    def default_value(self, z):
        what = "default"
        k = str(z[1]).lower()
        if k in ["null", "current_timestamp"]:
            return {what: k}

        # print(f"{what}: {len(z)} {z}", file=sys.stderr)
        return {what: z[1]}

    def null_or_not_null(self, z):
        if str(z[0]).lower() == "not":
            return {"null": False}
        return {"null": True}

    def on_update(self, z):
        what = "ON_UPDATE"
        print(f"{what}: {len(z)} {z}", file=sys.stderr)
        raise Exception(f"{what} not implemented yet")

    def AUTO_INCREMENT(self, z):
        return {str(z).lower(): True}

    def comment(self, z):
        return {"comment": z[1]}

    def column_modifiers(self, z):
        rr = {}
        for item in z:
            for k, v in item.items():
                if k in rr:
                    raise Exception(f"duplicate column modifier for {k}: {rr} {z}")
                rr[k] = v
            # print(item, file=sys.stderr)
        return rr

    @v_args(meta=True)
    def data_type(self, meta, z):
        what = "data_type"

        if len(z) == 1:
            return str(z[0])

        if len(z) == 2:
            if z[0].lower() == "char":
                return f"char:{z[1]}"

            if z[0].lower() == "varchar":
                return f"varchar:{z[1]}"

            if str(z[1]).lower() == "unsigned":
                return f"{z[0]}:{z[1]}"

        if len(z) == 3:
            if z[0].lower() == "decimal":
                return f"decimal:{z[1]},{z[2]}"

        msg = f"{what}: {len(z)} {z} line: {meta.line},col: {meta.column}"
        print(msg, file=sys.stderr)
        raise Exception(msg)

    @v_args(meta=True)
    def column_definition(self, meta, z):
        for k in ["type", "name"]:
            if k in z[2]:
                raise Exception(f"unexpected '{k}' found in column definition; line: {meta.line},col: {meta.column}")
        z[2]["type"] = z[1]
        z[2]["name"] = z[0]
        return {"col": {z[0]: z[2]}}

    def index_column_names(self, z):
        return z

    @v_args(meta=True)
    def index_column_name(self, meta, z):
        what = "index_column_name"
        if len(z) == 1:
            return str(z[0])
        if len(z) == 2:
            return f"{z[0]}:{z[1]}"

        msg = f"{what}: {len(z)} {z} line: {meta.line},col: {meta.column}"
        print(msg, file=sys.stderr)
        raise Exception(msg)

    @v_args(meta=True)
    def index_definition(self, meta, z):
        what = "index_definition"

        if str(z[0]).lower() == "key":
            return {"key": {z[1]: z[2:][0]}}

        if str(z[0]).lower() == "key:primary":
            return {"key": {f"{z[0]}": z[1:][0]}}

        if str(z[0]).lower() == "key:unique":
            return {"key": {f"{z[1]}:unique": z[2:][0]}}

        if str(z[0]).lower() == "key:fulltext":
            return {"key": {f"{z[1]}:fulltext": z[2:][0]}}

        msg = f"{what}: {len(z)} {z} line: {meta.line},col: {meta.column}"
        print(msg, file=sys.stderr)
        raise Exception(msg)

    def check_expression(self, z):
        return {"check": z}

    def t_create_definition(self, z):
        return z

    def primary_key(self, z):
        _ = z
        return "key:primary"

    def fulltext_key(self, z):
        _ = z
        return "key:fulltext"

    def unique_key(self, z):
        _ = z
        return "key:unique"

    def table_create_definitions(self, z):
        rr = {
            "cols": {},
            "keys": {},
            "checks": {},
        }
        for items in z:
            for item in items:
                for k, _ in item.items():
                    if k == "col":
                        for name, val in item[k].items():
                            rr["cols"][name] = val
                    if k == "key":
                        for name, val in item[k].items():
                            rr["keys"][name] = val

        return rr

    def create_table_statement(self, z):
        table_name = str(z[1])
        k = "glpi_"
        if table_name.startswith(k):
            table_name = table_name[len(k) :]
        self.tables[table_name] = z[2]

        return [str(z[0]), table_name, z[2]]


def my_gram(filename: str) -> str:
    with open(filename, "r", encoding="UTF-8") as f:
        return f.read()


def load_file(filename: str) -> str:
    with open(filename, "r", encoding="UTF-8") as f:
        return f.read()


def detect_common_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    temp: Dict[str, Any] = {}

    result: Dict[str, Any] = {}
    for t_name, t_def in data.items():
        for c_name, c_def in t_def["cols"].items():
            if c_name not in temp:
                temp[c_name] = c_def
                continue

            z = temp[c_name]
            for k, _ in c_def.items():
                if k not in z:
                    print(f"missing {k} in def: {c_name}", t_name, file=sys.stderr)

    return result


def detect_relations(data: Dict[str, Any]) -> Dict[str, Any]:
    # temp: Dict[str, Any] = {}
    result: Dict[str, Any] = {}

    for t_name, t_def in data.items():
        for c_name, c_def in t_def["cols"].items():
            _ = c_def

            rel = False
            via = ""
            d_name = ""
            if c_name.endswith("_id"):
                if c_name[:-3] in data:
                    rel = True
                    via = c_name
                    d_name = c_name[:-3]

            if "_id_" in c_name:
                a = c_name.split("_id_")
                if a[0] in data:
                    rel = True
                    via = c_name
                    d_name = a[0]

            if rel:
                print("RELATION:", t_name, "->", d_name, "via", via, file=sys.stderr)
                if t_name not in result:
                    result[t_name] = {}

                if d_name not in result[t_name]:
                    result[t_name][d_name] = {}

                result[t_name][d_name][via] = {}

    return result


def main() -> None:
    text = load_file(FILE)
    gram = my_gram("gram.lark")

    larker = Lark(
        gram,
        propagate_positions=True,
    )

    t = larker.parse(text)
    # print(t.pretty(), file=sys.stderr)

    zz = TransformProcessor()
    # print(json.dumps(zz.tables, indent=2))

    rr = zz.transform(t)
    common_fields = detect_common_fields(rr)

    relations = detect_relations(rr)
    # we expect all relations to have indexes on the _id fields

    analize = {
        "domain": common_fields,
        "tables": rr,
        "relations": relations,
        "issues": {},
    }

    print(
        yaml.dump(
            analize,
            sort_keys=False,
            Dumper=IndentDumper,
            allow_unicode=True,
        )
    )

    sys.exit(0)


main()
