from jnav.filtering import Filter, build_combined_expression, text_search_expr


def _f(
    expr: str,
    *,
    enabled: bool = True,
    combine: str = "and",
) -> Filter:
    return {"expr": expr, "enabled": enabled, "combine": combine}


class TestBuildCombinedExpression:
    def test_empty_list(self) -> None:
        assert build_combined_expression([]) is None

    def test_all_disabled(self) -> None:
        assert build_combined_expression([_f(".a", enabled=False)]) is None

    def test_single_and(self) -> None:
        assert build_combined_expression([_f(".a")]) == ".a"

    def test_single_or(self) -> None:
        assert build_combined_expression([_f(".a", combine="or")]) == ".a"

    def test_two_and(self) -> None:
        result = build_combined_expression([_f(".a"), _f(".b")])
        assert result == ".a and .b"

    def test_two_or(self) -> None:
        result = build_combined_expression([_f(".a", combine="or"), _f(".b", combine="or")])
        assert result == ".a or .b"

    def test_mixed_and_or(self) -> None:
        result = build_combined_expression([
            _f(".a"),
            _f(".b"),
            _f(".c", combine="or"),
        ])
        assert result == "(.a and .b) or .c"

    def test_disabled_filters_excluded(self) -> None:
        result = build_combined_expression([
            _f(".a"),
            _f(".b", enabled=False),
            _f(".c"),
        ])
        assert result == ".a and .c"

    def test_two_or_with_spaces_in_expr(self) -> None:
        result = build_combined_expression([
            _f('.a == "a"', combine="or"),
            _f('.a == "b"', combine="or"),
        ])
        assert result == '.a == "a" or .a == "b"'

    def test_mix_with_disabled(self) -> None:
        result = build_combined_expression([
            _f(".a"),
            _f(".b", combine="or", enabled=False),
            _f(".c", combine="or"),
        ])
        assert result == ".a or .c"


class TestTextSearchExpr:
    def test_simple_term(self) -> None:
        expr = text_search_expr("error")
        assert 'contains("error")' in expr

    def test_case_insensitive(self) -> None:
        expr = text_search_expr("Error")
        assert 'contains("error")' in expr

    def test_escapes_backslash(self) -> None:
        expr = text_search_expr("a\\b")
        assert "a\\\\b" in expr

    def test_escapes_quotes(self) -> None:
        expr = text_search_expr('say "hi"')
        assert r"say \"hi\"" in expr
