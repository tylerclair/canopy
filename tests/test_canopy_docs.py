"""Tests for canopy/scripts/canopy_docs.py — AST helpers and file collection."""

import ast
import textwrap
from pathlib import Path

from canopy.scripts.canopy_docs import (
    _collect_api_files,
    _get_canvas_params,
    _get_summary,
    _index_file,
    _infer_return_type,
    load_excluded_specs,
)

# ── Fixtures ─────────────────────────────────────────────────────────


def _parse_func(src: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    """Parse a source snippet and return the first function definition."""
    tree = ast.parse(textwrap.dedent(src))
    return tree.body[0]


def _make_api_file(tmp_path: Path, name: str, src: str) -> Path:
    p = tmp_path / name
    p.write_text(textwrap.dedent(src))
    return p


# ── _infer_return_type ───────────────────────────────────────────────


class TestInferReturnType:
    def test_all_pages_returns_list(self):
        func = _parse_func("def f(self):\n    client.get(url, all_pages=True)")
        assert _infer_return_type(func) == "list[dict]"

    def test_single_item_returns_dict(self):
        func = _parse_func("def f(self):\n    client.get(url, single_item=True)")
        assert _infer_return_type(func) == "dict"

    def test_poly_response_returns_union(self):
        func = _parse_func("def f(self):\n    client.get(url, poly_response=True)")
        assert _infer_return_type(func) == "dict | list[dict]"

    def test_no_special_kwarg_defaults_to_dict(self):
        func = _parse_func("def f(self):\n    client.get(url)")
        assert _infer_return_type(func) == "dict"

    def test_async_function_all_pages(self):
        func = _parse_func("async def f(self):\n    await client.async_get(url, all_pages=True)")
        assert _infer_return_type(func) == "list[dict]"

    def test_priority_all_pages_over_single_item(self):
        # all_pages takes first-match priority via the if chain
        func = _parse_func(
            "def f(self):\n    client.get(url, all_pages=True, single_item=True)"
        )
        assert _infer_return_type(func) == "list[dict]"


# ── _get_canvas_params ───────────────────────────────────────────────


class TestGetCanvasParams:
    def test_filters_canopy_kwargs(self):
        func = _parse_func(
            "def f(self, course_id, as_user_id=None, do_not_process=None, no_data=None):\n    pass"
        )
        params = _get_canvas_params(func)
        assert "as_user_id=None" not in params
        assert "do_not_process=None" not in params
        assert "no_data=None" not in params
        assert "self" not in params

    def test_required_param_no_default(self):
        func = _parse_func("def f(self, course_id, include=None):\n    pass")
        params = _get_canvas_params(func)
        assert "course_id" in params
        assert "include=None" in params

    def test_optional_param_with_default(self):
        func = _parse_func("def f(self, order_by=None):\n    pass")
        params = _get_canvas_params(func)
        assert params == ["order_by=None"]

    def test_no_canvas_params(self):
        func = _parse_func(
            "def f(self, as_user_id=None, do_not_process=None, no_data=None):\n    pass"
        )
        assert _get_canvas_params(func) == []

    def test_multiple_required_params(self):
        func = _parse_func("def f(self, course_id, assignment_id, include=None):\n    pass")
        params = _get_canvas_params(func)
        assert "course_id" in params
        assert "assignment_id" in params
        assert "include=None" in params


# ── _get_summary ─────────────────────────────────────────────────────


class TestGetSummary:
    def test_returns_first_docstring_line(self):
        func = _parse_func(
            'def f(self):\n    """List all courses for an account.\n\n    Extra notes.\n    """\n    pass'
        )
        assert _get_summary(func) == "List all courses for an account"

    def test_strips_trailing_period(self):
        func = _parse_func('def f(self):\n    """Get a single account."""\n    pass')
        assert _get_summary(func) == "Get a single account"

    def test_no_docstring_returns_empty(self):
        func = _parse_func("def f(self):\n    pass")
        assert _get_summary(func) == ""

    def test_multiline_only_first_line(self):
        func = _parse_func(
            'def f(self):\n    """First line.\n    Second line.\n    """\n    pass'
        )
        assert _get_summary(func) == "First line"


# ── _index_file ──────────────────────────────────────────────────────


SYNC_API_SRC = """\
class Accounts:
    def __init__(self, client):
        self.client = client

    def list_accounts(self, as_user_id=None, do_not_process=None, no_data=None):
        \"\"\"List all accounts.\"\"\"
        return self.client.get("/api/v1/accounts", all_pages=True)

    def get_account(self, id, as_user_id=None, do_not_process=None, no_data=None):
        \"\"\"Get a single account.\"\"\"
        return self.client.get(f"/api/v1/accounts/{id}", single_item=True)
"""

ASYNC_API_SRC = """\
class AccountsAsync:
    def __init__(self, client):
        self.client = client

    async def list_accounts(self, as_user_id=None, do_not_process=None, no_data=None):
        \"\"\"List all accounts.\"\"\"
        return await self.client.async_get("/api/v1/accounts", all_pages=True)
"""


class TestIndexFile:
    def test_sync_file_produces_output(self, tmp_path):
        p = _make_api_file(tmp_path, "accounts.py", SYNC_API_SRC)
        result = _index_file(p)
        assert result is not None

    def test_sync_class_header(self, tmp_path):
        p = _make_api_file(tmp_path, "accounts.py", SYNC_API_SRC)
        result = _index_file(p)
        assert "## Accounts (accounts.py)" in result

    def test_sync_skips_init(self, tmp_path):
        p = _make_api_file(tmp_path, "accounts.py", SYNC_API_SRC)
        result = _index_file(p)
        assert "__init__" not in result

    def test_sync_list_method_return_type(self, tmp_path):
        p = _make_api_file(tmp_path, "accounts.py", SYNC_API_SRC)
        result = _index_file(p)
        assert "list_accounts(self, ...) -> list[dict]" in result

    def test_sync_single_item_method_return_type(self, tmp_path):
        p = _make_api_file(tmp_path, "accounts.py", SYNC_API_SRC)
        result = _index_file(p)
        assert "get_account(self, id, ...) -> dict" in result

    def test_sync_summary_included(self, tmp_path):
        p = _make_api_file(tmp_path, "accounts.py", SYNC_API_SRC)
        result = _index_file(p)
        assert "# List all accounts" in result

    def test_sync_canopy_kwargs_collapsed_to_ellipsis(self, tmp_path):
        p = _make_api_file(tmp_path, "accounts.py", SYNC_API_SRC)
        result = _index_file(p)
        assert "as_user_id" not in result
        assert "do_not_process" not in result
        assert "no_data" not in result

    def test_async_file_uses_async_def(self, tmp_path):
        p = _make_api_file(tmp_path, "accounts_async.py", ASYNC_API_SRC)
        result = _index_file(p)
        assert "async def list_accounts" in result

    def test_async_class_header(self, tmp_path):
        p = _make_api_file(tmp_path, "accounts_async.py", ASYNC_API_SRC)
        result = _index_file(p)
        assert "## AccountsAsync (accounts_async.py)" in result

    def test_syntax_error_returns_none(self, tmp_path):
        p = tmp_path / "broken.py"
        p.write_text("def (:\n    pass")
        assert _index_file(p) is None

    def test_file_with_no_class_returns_none(self, tmp_path):
        p = tmp_path / "noclass.py"
        p.write_text("x = 1\n")
        assert _index_file(p) is None


# ── _collect_api_files ───────────────────────────────────────────────


class TestCollectApiFiles:
    def _make_dir(self, tmp_path: Path, names: list[str]) -> Path:
        for name in names:
            (tmp_path / name).write_text("# stub")
        return tmp_path

    def test_excludes_canvas_client_and_init(self, tmp_path):
        self._make_dir(tmp_path, ["accounts.py", "canvas_client.py", "__init__.py"])
        files = _collect_api_files(tmp_path, False, False, set())
        names = [f.name for f in files]
        assert "canvas_client.py" not in names
        assert "__init__.py" not in names
        assert "accounts.py" in names

    def test_sync_only_excludes_async(self, tmp_path):
        self._make_dir(tmp_path, ["accounts.py", "accounts_async.py", "courses.py", "courses_async.py"])
        files = _collect_api_files(tmp_path, True, False, set())
        names = [f.name for f in files]
        assert "accounts_async.py" not in names
        assert "courses_async.py" not in names
        assert "accounts.py" in names

    def test_async_only_excludes_sync(self, tmp_path):
        self._make_dir(tmp_path, ["accounts.py", "accounts_async.py"])
        files = _collect_api_files(tmp_path, False, True, set())
        names = [f.name for f in files]
        assert "accounts.py" not in names
        assert "accounts_async.py" in names

    def test_excluded_specs_removes_both_sync_and_async(self, tmp_path):
        self._make_dir(tmp_path, ["accounts.py", "accounts_async.py", "courses.py", "courses_async.py"])
        files = _collect_api_files(tmp_path, False, False, {"accounts.json"})
        names = [f.name for f in files]
        assert "accounts.py" not in names
        assert "accounts_async.py" not in names
        assert "courses.py" in names
        assert "courses_async.py" in names

    def test_results_are_sorted(self, tmp_path):
        self._make_dir(tmp_path, ["courses.py", "accounts.py", "enrollments.py"])
        files = _collect_api_files(tmp_path, False, False, set())
        names = [f.name for f in files]
        assert names == sorted(names)

    def test_non_py_files_excluded(self, tmp_path):
        self._make_dir(tmp_path, ["accounts.py", "README.md", "config.toml"])
        files = _collect_api_files(tmp_path, False, False, set())
        names = [f.name for f in files]
        assert "README.md" not in names
        assert "config.toml" not in names


# ── load_excluded_specs ──────────────────────────────────────────────


class TestLoadExcludedSpecs:
    def test_none_returns_empty_set(self):
        assert load_excluded_specs(None) == set()

    def test_loads_excluded_list(self, tmp_path):
        toml_file = tmp_path / "exclude.toml"
        toml_file.write_text('excluded = ["quiz_extensions.json", "moderated_grading.json"]\n')
        result = load_excluded_specs(toml_file)
        assert result == {"quiz_extensions.json", "moderated_grading.json"}

    def test_empty_excluded_list(self, tmp_path):
        toml_file = tmp_path / "exclude.toml"
        toml_file.write_text("excluded = []\n")
        assert load_excluded_specs(toml_file) == set()
