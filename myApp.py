from typing import (
    Dict,
    Any,
    Tuple,
    List,
)

import sys
import copy

from lark import (
    Lark,
)

from transformProcessor import TransformProcessor


class MyApp:
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

    DOMAINSx: Dict[str, Any] = {
        "varchar255_null": {
            "default": "null",
            "type": "varchar:255",
        },
        "default_pk": {
            "null": False,
            "auto_increment": True,
            "type": "int:unsigned",
        },
        "u_int_nn_d0": {
            "null": False,
            "type": "int:unsigned",
            "default": "0",
        },
        "bool_false": {
            "null": False,
            "default": "0",
            "type": "tinyint",
        },
        "timestamp_null": {
            "null": True,
            "default": "null",
            "type": "timestamp",
        },
    }

    DOMAINS: Dict[str, Any] = {}

    def __init__(
        self,
        verbose: bool = False,
    ) -> None:
        self.verbose = verbose
        self.text = ""
        self.gram = ""

    def load_file(self, filename: str) -> str:
        with open(filename, "r", encoding="UTF-8") as f:
            return f.read()

    def my_gram(
        self,
        filename: str,
    ) -> str:
        self.gram = self.load_file(filename)

    def load_text(
        self,
        filename: str,
    ) -> str:
        self.text = self.load_file(filename)

    def detect_domain(
        self,
        c_def: Dict[str, Any],
    ) -> Dict[str, Any]:
        rr = {}

        candidate = True
        for d_name, d_def in self.DOMAINS.items():
            candidate = True
            for k, v in c_def.items():
                rr[k] = v

            for k, v in d_def.items():
                if k not in c_def or c_def[k] != v:
                    candidate = False
                    break

            if candidate is True:
                rr["domain"] = d_name
                break

        if candidate is False:
            return c_def

        if "domain" in rr:
            for k in self.DOMAINS[rr["domain"]].keys():
                del rr[k]

        return rr

    def abstract_one_column(
        self,
        c_def: Dict[str, Any],
    ) -> Tuple[str, Dict[str, Any]]:
        # all but name and comment and create a name from that
        ll = []
        c = copy.deepcopy(c_def)

        z = {
            "type": "t",
            "default": "d",
            "null": "n",
            "auto_increment": "ai",
            "comment": None,
            "name": None,
        }

        seen = []
        domain = {}

        for k, v in z.items():
            if k not in c:
                continue

            if v is None:
                seen.append(k)
                continue

            if k == "null":
                ll.append(f"{v}:{'T' if c[k] is True else 'F'}")
            else:
                ll.append(f"{v}:{c[k]}")
            domain[k] = c_def[k]
            seen.append(k)

        for k in sorted(c_def.keys()):
            if k in seen:
                continue
            ll.append(f"{k}:{c_def[k]}")
            domain[k] = c_def[k]

        name = ", ".join(ll)
        return name, domain

    def count_common_fields(
        self,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for _, t_def in data.items():  # tables
            cols = t_def["cols"]
            for _, c_def in cols.items():  # columns
                name, domain = self.abstract_one_column(c_def)
                if name not in result:
                    self.DOMAINS[name] = domain
                    result[name] = 0
                result[name] += 1
        return result

    def detect_common_fields(
        self,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {}

        for t_name, t_def in data.items():  # tables
            cols = t_def["cols"]

            result[t_name] = copy.deepcopy(t_def)

            for c_name, c_def in cols.items():  # columns
                new_c_def = self.detect_domain(c_def)
                result[t_name]["cols"][c_name] = new_c_def

        return result

    def detect_relations(
        self,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        temp: Dict[str, Any] = {}
        result: Dict[str, Any] = {}

        for t_name, t_def in data.items():  # tables
            cols = t_def["cols"]
            keys = t_def["keys"]

            for c_name, c_def in cols.items():  # columns
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

                if not rel:
                    continue

                if self.verbose:
                    print("RELATION:", t_name, "->", d_name, "via", via, file=sys.stderr)

                if t_name not in result:
                    result[t_name] = {}

                if d_name not in result[t_name]:
                    result[t_name][d_name] = {}

                result[t_name][d_name][via] = {}

                if via not in keys:
                    if t_name not in temp:
                        temp[t_name] = {}
                    temp[t_name][via] = "NoIndexForReferencialIntegrity"

                    if self.verbose:
                        msg = (
                            f"    no index for {via} in table: {t_name}: "
                            + "would be needed to implement referential integrity"
                        )
                        print(
                            msg,
                            file=sys.stderr,
                        )

        return result, temp

    def extract_parents(
        self,
        data: Dict[str, Any],
    ) -> Dict[str, any]:
        """Extract common patterns and reduce the length of the table def, initially dont move the indexes

        typical common parents could be:
         - MinimalBase:
            having the default pk
         - HavingNameAndComment:
            name(vc 255, def null), comment(text, def null)
         - HavingDefaultTimeStampsCreMod:
            date_mod, date_create
        StandardBase:
            some tables are only that: MinimalBase, HavingNameAndComment, HavingDefaultTimeStampsCreMod
        WithEntityAndRecursive:
        HavingUserGroup:
        HavingTechUserGroup:
        FromTemplate:

        """

        _ = data
        result: Dict[str, Any] = {}

        return result

    def extract_name_collisions(
        self,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {}

        for t_name, t_def in data.items():
            c = data[t_name]["cols"]
            for c_name, c_def in c.items():
                if c_name not in result:
                    result[c_name] = {}
                d = c_def.get("domain")
                if d is None:
                    continue
                if d not in result[c_name]:
                    result[c_name][d] = []
                result[c_name][d].append(t_name)

        return result

    def run(
        self,
        gram_file: str,
        text_file: str,
    ) -> Dict[str, Any]:
        self.my_gram(gram_file)
        self.load_text(text_file)

        larker = Lark(
            self.gram,
            propagate_positions=True,
        )

        t = larker.parse(self.text)
        zz = TransformProcessor(
            verbose=self.verbose,
        )
        rr = zz.transform(t)

        return rr
