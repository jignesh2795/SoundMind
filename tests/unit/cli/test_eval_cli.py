from pathlib import Path

from soundmind.cli.main import build_parser, main


def test_eval_run_parser_defaults_and_options() -> None:
    args = build_parser().parse_args([
        "eval", "run", "--dataset", "queries.json", "--judgments",
        "data/eval/judgments.local.json", "--retrieval", "lexical",
        "--limit", "7", "--out", "data/eval/reports/test.json",
        "--db", "data/database/test.db",
    ])
    assert args.command == "eval"
    assert args.eval_command == "run"
    assert args.dataset == Path("queries.json")
    assert args.judgments == Path("data/eval/judgments.local.json")
    assert args.retrieval == "lexical"
    assert args.limit == 7
    assert args.out == Path("data/eval/reports/test.json")
    assert args.db == Path("data/database/test.db")


def test_eval_compare_parser() -> None:
    args = build_parser().parse_args([
        "eval", "compare", "--baseline", "data/eval/reports/base.json",
        "--candidate", "data/eval/reports/candidate.json",
    ])
    assert args.eval_command == "compare"
    assert args.baseline == Path("data/eval/reports/base.json")
    assert args.candidate == Path("data/eval/reports/candidate.json")


def test_eval_run_dispatches_to_evaluator(monkeypatch) -> None:
    captured = {}
    def fake_run(**kwargs):
        captured.update(kwargs)
        return 0
    monkeypatch.setattr("soundmind.evaluation.run_evaluation", fake_run)
    result = main([
        "eval", "run", "--dataset", "queries.json", "--judgments",
        "data/eval/judgments.local.json", "--retrieval", "catalog",
        "--limit", "10", "--out", "data/eval/reports/result.json",
    ])
    assert result == 0
    assert captured["dataset_path"] == Path("queries.json")
    assert captured["retrieval"] == "catalog"

def test_eval_fingerprint_parser() -> None:
    args = build_parser().parse_args(["eval", "fingerprint", "--db", "library.db"])
    assert args.command == "eval"
    assert args.eval_command == "fingerprint"
    assert args.db == Path("library.db")
