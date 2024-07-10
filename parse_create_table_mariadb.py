import logging
import sys
import json


from lark import (
    Lark,
    logger,
    Transformer,
    v_args,
    # Visitor,
)

logger.setLevel(logging.WARN)

FILE = "glpi-empty.sql"


class TransformProcessor(Transformer):
    def __init__(self):
        # super().__init__()
        self.tables = {}

    def name(self, z):
        # what = "NAME"
        # print(f"{what}: {len(z)} {z}", file=sys.stderr)
        return str(z[0])

    def string(self, z):
        # what = "STRING"
        # print(f"{what}: {len(z)} {z}", file=sys.stderr)

        if z[0][0] == "'":
            return z[0][1:-1]

        return z[0]

    def number(self, z):
        # what = "NUMBER"
        # print(f"{what}: {len(z)} {z[0]}", file=sys.stderr)

        if "." in str(z):
            return float(z[0])
        return int(z[0])

    def identifier(self, z):
        what = "IDENTIFIER"
        print(f"{what}: {len(z)} {z[0]}", file=sys.stderr)
        return str(z[0])

    def unsigned(self, z):
        _ = z
        return "unsigned"

    def expression(self, z):
        # what = "EXPRESSION"
        # print(f"{what}: {len(z)} {z}", file=sys.stderr)
        return z[0]

    def default_value(self, z):
        what = "default"
        # print(f"{what}: {len(z)} {z}", file=sys.stderr)
        return {what: z[1]}

    def null_or_not_null(self, z):
        # what = "NULL"
        # print(f"{what}: {len(z)} {z}", file=sys.stderr)
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
        # what = "comment"
        # print(f"{what}: {len(z)} {z}", file=sys.stderr)
        return {"comment": z[1]}

    def column_modifiers(self, z):
        rr = {}
        for item in z:
            for k, v in item.items():
                if k in rr:
                    raise Exception(f"duplicate column modifier for {k}: {rr} {z}")
                rr[k] = v
            print(item, file=sys.stderr)
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

    def column_definition(self, z):
        # what = "column_definition"
        # print(f"{what}: {len(z)} {z}", file=sys.stderr)
        # col_name, col_type, col_modifiers_dict
        return {"col": {z[0]: {z[1]: z[2]}}}

    def index_column_names(self, z):
        # what = "index_column_names"
        # print(f"{what}: {len(z)} {z}", file=sys.stderr)
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
        # what = "check_expression"
        # print(f"{what}: {len(z)} {z}", file=sys.stderr)
        return {"check": z}

    def t_create_definition(self, z):
        what = "t_create_definition"
        print(f"{what}: {len(z)} {z}", file=sys.stderr)
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
        # what = "table_create_definitions"
        # print(f"{what}: {len(z)} {z}", file=sys.stderr)
        rr = {
            "cols": {},
            "keys": {},
            "checks": {},
        }
        for items in z:
            for item in items:
                # print(f"{what}: {item}", file=sys.stderr)

                for k, _ in item.items():
                    if k == "col":
                        for name, val in item[k].items():
                            rr["cols"][name] = val
                    if k == "key":
                        for name, val in item[k].items():
                            rr["keys"][name] = val

        # print(json.dumps(rr, indent=2), file=sys.stderr)

        return rr

    def create_table_statement(self, z):
        what = "create_table_statement"
        print(f"{what}: {len(z)} {z}", file=sys.stderr)
        self.tables[z[1]] = z[2]
        return z


def my_gram(filename: str) -> str:
    with open(filename, "r", encoding="UTF-8") as f:
        return f.read()


def load_file(filename: str) -> str:
    with open(filename, "r", encoding="UTF-8") as f:
        return f.read()


def main() -> None:
    text = load_file(FILE)
    gram = my_gram("gram.lark")

    larker = Lark(
        gram,
        propagate_positions=True,
    )

    t = larker.parse(text)
    print(t.pretty(), file=sys.stderr)

    zz = TransformProcessor()
    print(json.dumps(zz.tables, indent=2))

    rr = zz.transform(t)
    print(rr)

    sys.exit(0)


main()
