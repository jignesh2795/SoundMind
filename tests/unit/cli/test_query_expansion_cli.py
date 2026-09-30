from soundmind.cli.main import build_parser


def test_search_accepts_query_expansion_flag() -> None:
    args = build_parser().parse_args(
        ["search", "hero bgm", "--expand-query"]
    )

    assert args.expand_query is True


def test_recommend_accepts_query_expansion_flag() -> None:
    args = build_parser().parse_args(
        [
            "recommend",
            "hero bgm",
            "--context",
            "coding",
            "--retrieval",
            "hybrid",
            "--expand-query",
        ]
    )

    assert args.expand_query is True
