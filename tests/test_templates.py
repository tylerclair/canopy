"""Tests for Jinja2 template output correctness."""

import pytest

from canopy.scripts.canvas_api_builder import get_jinja_env

MINIMAL_SPEC = {
    "apiVersion": "1.0",
    "apis": [
        {
            "path": "/courses/{course_id}/assignments",
            "operations": [
                {
                    "nickname": "list_assignments",
                    "summary": "List assignments for a course",
                    "notes": "Returns paginated list.",
                    "method": "GET",
                    "type": "array",
                    "parameters": [
                        {
                            "name": "course_id",
                            "paramType": "path",
                            "required": True,
                            "type": "integer",
                        },
                        {
                            "name": "due_at",
                            "paramType": "query",
                            "required": False,
                            "type": "DateTime",
                        },
                        {
                            "name": "order_by",
                            "paramType": "query",
                            "required": False,
                            "type": "string",
                            "enum": ["position", "name", "due_at"],
                        },
                    ],
                }
            ],
        }
    ],
}


@pytest.fixture
def sync_output():
    env = get_jinja_env()
    template = env.get_template("canopy_api.py.jinja2")
    return template.render(spec=MINIMAL_SPEC, api_name="Assignments", api_file_name="assignments")


@pytest.fixture
def async_output():
    env = get_jinja_env()
    template = env.get_template("canopy_api_async.py.jinja2")
    return template.render(
        spec=MINIMAL_SPEC, api_name="Assignments", api_file_name="assignments_async"
    )


class TestSyncTemplate:
    def test_no_object_base_class(self, sync_output):
        assert "class Assignments(object)" not in sync_output
        assert "class Assignments:" in sync_output

    def test_correct_import(self, sync_output):
        assert "from canopy.helpers import _validate_enum, coerce_to_iso8601" in sync_output
        assert "_validate_iso8601_string" not in sync_output

    def test_no_issubclass(self, sync_output):
        assert "issubclass" not in sync_output

    def test_coerce_to_iso8601_used(self, sync_output):
        assert "coerce_to_iso8601(due_at)" in sync_output

    def test_validate_enum_used(self, sync_output):
        assert '_validate_enum(order_by, ["position", "name", "due_at"])' in sync_output

    def test_generated_code_is_valid_python(self, sync_output):
        compile(sync_output, "<generated>", "exec")


class TestAsyncTemplate:
    def test_no_object_base_class(self, async_output):
        assert "class AssignmentsAsync(object)" not in async_output
        assert "class AssignmentsAsync:" in async_output

    def test_correct_import(self, async_output):
        assert "from canopy.helpers import _validate_enum, coerce_to_iso8601" in async_output
        assert "_validate_iso8601_string" not in async_output

    def test_no_issubclass(self, async_output):
        assert "issubclass" not in async_output

    def test_async_def_present(self, async_output):
        assert "async def list_assignments" in async_output

    def test_generated_code_is_valid_python(self, async_output):
        compile(async_output, "<generated>", "exec")
