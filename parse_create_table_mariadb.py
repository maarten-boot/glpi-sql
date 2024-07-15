import logging
import sys
import yaml

from lark import logger
from myApp import MyApp

logger.setLevel(logging.WARN)


class IndentDumper(yaml.Dumper):  # pylint: disable=too-many-ancestors
    def increase_indent(
        self,
        flow=False,
        indentless=False,
    ):
        return super().increase_indent(flow, False)


def main() -> None:
    FILE = "glpi-empty.sql"
    GRAM = "gram.lark"
    VERBOSE = 0

    ma = MyApp(verbose=VERBOSE)
    rr = ma.run(GRAM, FILE)
    ma.count_common_fields(rr)
    rr2 = ma.detect_common_fields(rr)

    relations, rel_issues = ma.detect_relations(rr2)

    # extract col_name -> domain -> [table_names], to detect identical name with differnt domain
    t1 = ma.extract_name_collisions(rr2)
    for col in sorted(t1.keys()):
        if len(t1[col].keys()) <= 1:
            continue
        for domain in sorted(t1[col].keys()):
            count = len(t1[col][domain])

            print(col, domain, count, t1[col][domain], file=sys.stderr)

    parents = ma.extract_parents(rr2)

    analize = {
        "domain": ma.DOMAINS,
        "parents": parents,
        "relations": relations,
        "tables": rr2,
        "issues": {
            "relations": rel_issues,
        },
    }

    print(
        yaml.dump(
            analize,
            sort_keys=False,
            Dumper=IndentDumper,
            allow_unicode=True,
        )
    )


main()
