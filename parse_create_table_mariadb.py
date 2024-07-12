import logging

import yaml

from lark import (
    Lark,
    logger,
)

from transformProcessor import TransformProcessor
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
    VERBOSE = 0

    ma = MyApp(verbose=VERBOSE)

    text = ma.load_text(FILE)
    gram = ma.my_gram("gram.lark")

    larker = Lark(
        gram,
        propagate_positions=True,
    )
    t = larker.parse(text)
    zz = TransformProcessor(verbose=VERBOSE)
    rr = zz.transform(t)

    rr2 = ma.detect_common_fields(rr)

    relations, rel_issues = ma.detect_relations(rr2)
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
