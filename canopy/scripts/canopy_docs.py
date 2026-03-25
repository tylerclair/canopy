"""canopy_docs — LLM documentation generator for Canopy projects.

Commands:
    generate-index   Parse generated API files and emit a compact method index.
    generate-llms    Write a static llms.txt describing the Canopy framework.
    generate-all     Run both commands in one step.
"""

import ast
from pathlib import Path

import click

CANOPY_KWARGS = {"as_user_id", "do_not_process", "no_data", "self"}

LLMS_TXT = """\
# Canopy

Canopy is a Python library for the Instructure Canvas LMS REST API. It provides
generated API modules (sync and async) built from Canvas OpenAPI/Swagger spec
files via a Jinja2 template, plus a CanvasSession client that handles auth,
pagination, and request dispatching.

Source: https://github.com/tylerclair/canopy


---
## Installation

```bash
# Runtime only
uv add git+https://github.com/tylerclair/canopy.git

# With dotenv + async rate limiting
uv add "canopy[extras] @ git+https://github.com/tylerclair/canopy.git"

# With API module builder
uv add "canopy[builder] @ git+https://github.com/tylerclair/canopy.git"
```


---
## Core classes

### CanvasSession (canopy.CanvasSession)

The HTTP client. Handles Bearer auth, lazy httpx client init, pagination, and
both sync and async requests.

```python
from canopy import CanvasSession

session = CanvasSession(
    instance_address="https://yourschool.instructure.com",  # trailing slash stripped automatically
    access_token="your_token_here",
    max_per_page=100,  # injected as per_page on all paginated requests
)
```

Supports context managers for connection cleanup:

```python
with CanvasSession(url, token) as session:
    ...

async with CanvasSession(url, token) as session:
    ...
```

### CanvasClient (canvas_client.CanvasClient)

Generated file that wraps CanvasSession and attaches all generated API modules
as attributes. Produced by `canvas_api_builder build-canvas-client-file`.

```python
from canvas_client import CanvasClient

client = CanvasClient(
    instance_address="https://yourschool.instructure.com",
    access_token="your_token_here",
    max_per_page=100,
)
```

Sync modules are accessed as `client.<resource>`, async as `client.<resource>_async`:

```python
client.accounts          # Accounts (sync)
client.accounts_async    # AccountsAsync (async)
client.courses           # Courses (sync)
client.courses_async     # CoursesAsync (async)
# ...one attribute per generated spec file
```

### CanvasAPIError (canopy.CanvasAPIError)

Raised for all non-2xx responses.

```python
from canopy import CanvasAPIError

try:
    account = client.accounts.get_account(id=99999)
except CanvasAPIError as e:
    e.status_code   # int, e.g. 404
    e.content       # parsed JSON (dict/list) or raw text if not JSON
    e.response      # the underlying httpx.Response
    e.to_json()     # serializes status_code and content to JSON string
```


---
## Generated API modules

Each generated module (e.g. `accounts.py`, `courses.py`) contains a single class
with one method per Canvas API endpoint. Modules are generated from Canvas
OpenAPI/Swagger spec files using `canvas_api_builder`. They are not included in
the Canopy package — they are generated into your project's `apis/` folder.

### Method signatures

Every generated method follows this pattern:

```python
# Sync
def <endpoint_name>(self, <canvas_params>, as_user_id=None, do_not_process=None, no_data=None):

# Async
async def <endpoint_name>(self, <canvas_params>,
                           as_user_id=None, do_not_process=None, no_data=None):
```

Canvas parameters come from the spec and are either required positional args or
optional keyword args defaulting to None. Required path parameters (e.g. `id`,
`course_id`) are always positional. Optional query and form parameters are
keyword-only with `=None`.

### Return values

| Canvas endpoint type | Default return value |
|---|---|
| Array (list endpoint) | `list[dict]` — all pages fetched automatically |
| Single object | `dict` |
| Void / action | `dict` or `list[dict]` (auto-paginated if list) |
| Any + `do_not_process=True` | `httpx.Response` |
| Any + `no_data=True` | `int` (HTTP status code) |

### Canopy kwargs

These three kwargs are present on every generated method. They are intercepted
by Canopy and never forwarded to Canvas as API parameters.

**as_user_id** `str | int | None`
Masquerade as another Canvas user. Accepts a Canvas user ID (int) or a SIS ID
string (e.g. `"sis_login_id:abc123"`, `"sis_user_id:abc123"`). Requires act-as
permission on the account. Passed to Canvas as the `as_user_id` query parameter.

**do_not_process** `bool | None`
When truthy, bypasses all response processing and returns the raw
`httpx.Response` object. Use when you need direct access to headers, status
codes, or raw bytes.

**no_data** `bool | None`
When truthy, bypasses JSON parsing and returns the HTTP status code as an int.
Useful for DELETE or PUT calls where you only need to confirm success.


---
## Pagination

Automatic. Methods that return arrays fetch all pages before returning. The
`max_per_page` set on `CanvasSession` / `CanvasClient` is injected as `per_page`
on every paginated request. No manual pagination is ever needed.


---
## Async

The async variant of every generated class has an `Async` suffix and all methods
are `async def`. Use `asyncio.gather()` for concurrent requests — this is where
Canopy's async support provides the most benefit (e.g. fetching details for 100+
users concurrently vs sequentially).

```python
import asyncio

async def main():
    # Single call
    account = await client.accounts_async.get_account(id=1)

    # Concurrent calls
    ids = ["111", "222", "333"]
    results = await asyncio.gather(*[
        client.users_async.show_user_details(id=i) for i in ids
    ])

asyncio.run(main())
```


---
## Usage examples

```python
from canvas_client import CanvasClient
from canopy import CanvasAPIError

client = CanvasClient("https://yourschool.instructure.com", "your_token")

# List all accounts (auto-paginated, returns list[dict])
accounts = client.accounts.list_accounts()

# Get a single account (returns dict)
account = client.accounts.get_account(id=1)

# With optional Canvas param
accounts = client.accounts.list_accounts(include="course_count")

# Masquerade as another user
profile = client.users.get_user_profile("self", as_user_id=12345)

# Get raw response (headers, status, etc.)
response = client.accounts.list_accounts(do_not_process=True)
print(response.headers["X-Request-Cost"])

# Fire-and-forget delete, just confirm status
status = client.accounts.delete_user_from_root_account(
    account_id=1, user_id=99, no_data=True
)

# Error handling
try:
    account = client.accounts.get_account(id=99999)
except CanvasAPIError as e:
    print(e.status_code, e.content)
```


---
## Building API modules

Canopy includes a CLI (`canvas_api_builder`) for generating API modules from
Canvas spec files. Requires the `builder` optional dependency.

```bash
# Download spec files from Canvas live docs
canvas_api_builder update-spec-files --specs-folder specs/

# Generate a sync module
canvas_api_builder build-api-from-specfile --specfile specs/accounts.json --output-folder apis/

# Generate an async module
canvas_api_builder build-api-from-specfile \
    --specfile specs/accounts.json --output-folder apis/ --generate-async

# Generate CanvasClient (after generating all desired modules)
canvas_api_builder build-canvas-client-file --apis-folder apis/

# Regenerate all modules from existing specs
canvas_api_builder rebuild-apis --specs-folder specs/ --apifolder-path apis/
```

Generated files go in your project's `apis/` folder (gitignored by convention).
The generated `canvas_client.py` goes in the project root.


---
## Environment variables (canopy[extras])

```python
from dotenv import load_dotenv
import os

load_dotenv(".env.local")
client = CanvasClient(os.environ["CANVAS_URL"], os.environ["CANVAS_TOKEN"])
```

`.env.local` format:
```
CANVAS_TOKEN=your_token_here
CANVAS_URL=https://yourschool.instructure.com
```
"""


# ── AST helpers ─────────────────────────────────────────────────────


def _infer_return_type(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Infer return type from keyword args on the client call in the function body."""
    keywords: set[str] = set()
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg:
                    keywords.add(kw.arg)
    if "all_pages" in keywords:
        return "list[dict]"
    if "single_item" in keywords:
        return "dict"
    if "poly_response" in keywords:
        return "dict | list[dict]"
    return "dict"


def _get_canvas_params(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Return param names and defaults, excluding self and Canopy kwargs."""
    args = func_node.args
    all_args = args.args
    defaults_offset = len(all_args) - len(args.defaults)
    result = []
    for i, arg in enumerate(all_args):
        if arg.arg in CANOPY_KWARGS:
            continue
        has_default = i >= defaults_offset
        result.append(f"{arg.arg}=None" if has_default else arg.arg)
    return result


def _get_summary(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Extract first line of docstring as a short summary."""
    docstring = ast.get_docstring(func_node)
    if not docstring:
        return ""
    return docstring.split("\n")[0].strip().rstrip(".")


def _index_file(path: Path) -> str | None:
    """Parse a single generated API file and return its index block, or None on error."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return None

    is_async = "async" in path.stem
    func_type = ast.AsyncFunctionDef if is_async else ast.FunctionDef
    prefix = "async def" if is_async else "def"

    lines: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        lines.append(f"## {node.name} ({path.name})")
        for item in node.body:
            if not isinstance(item, func_type) or item.name == "__init__":
                continue
            canvas_params = _get_canvas_params(item)
            ret = _infer_return_type(item)
            summary = _get_summary(item)
            params_str = ", ".join(canvas_params)
            canvas_args = params_str + ", " if params_str else ""
            sig = f"{prefix} {item.name}(self, {canvas_args}...) -> {ret}"
            lines.append(f"  {sig}")
            if summary:
                lines.append(f"    # {summary}")
        lines.append("")
        break  # one class per generated file

    return "\n".join(lines) if lines else None


def _collect_api_files(
    apis_folder: Path,
    sync_only: bool,
    async_only: bool,
) -> list[Path]:
    excluded = {"canvas_client.py", "__init__.py"}
    files = sorted(p for p in apis_folder.iterdir() if p.suffix == ".py" and p.name not in excluded)
    if sync_only:
        return [p for p in files if "_async" not in p.stem]
    if async_only:
        return [p for p in files if "_async" in p.stem]
    return files


# ── CLI ──────────────────────────────────────────────────────────────


@click.group()
def cli() -> None:
    """Generate LLM documentation for a Canopy project."""


@cli.command()
@click.option(
    "-a",
    "--apis-folder",
    required=True,
    type=click.Path(file_okay=False, readable=True, path_type=Path),
    help="Folder containing generated API files.",
)
@click.option(
    "-o",
    "--output-file",
    default="apis_index.txt",
    show_default=True,
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help="Output path for the index file.",
)
@click.option("--sync-only", is_flag=True, default=False, help="Only index sync modules.")
@click.option("--async-only", is_flag=True, default=False, help="Only index async modules.")
def generate_index(
    apis_folder: Path,
    output_file: Path,
    sync_only: bool,
    async_only: bool,
) -> None:
    """Generate a compact LLM-readable index of all generated API methods.

    Parses the generated API files using AST (no imports required) and emits
    one line per method with its signature and inferred return type, grouped by
    class. Canopy kwargs (as_user_id, do_not_process, no_data) are collapsed to
    '...' since they are identical on every method and documented in llms.txt.
    """
    api_files = _collect_api_files(apis_folder, sync_only, async_only)

    blocks: list[str] = [
        "# Canopy API Index",
        "# Canopy kwargs omitted from all signatures — see llms.txt"
        " for: as_user_id, do_not_process, no_data",
        "",
    ]

    skipped = 0
    for path in api_files:
        block = _index_file(path)
        if block:
            blocks.append(block)
        else:
            click.echo(f"  ⚠ Skipped {path.name} (parse error)", err=True)
            skipped += 1

    output_file.write_text("\n".join(blocks), encoding="utf-8")
    size_kb = output_file.stat().st_size / 1024
    click.echo(f"✓ Indexed {len(api_files) - skipped} files → {output_file} ({size_kb:.1f} KB)")
    if skipped:
        click.echo(f"  ⚠ {skipped} file(s) skipped due to parse errors")


@cli.command()
@click.option(
    "-o",
    "--output-file",
    default="llms.txt",
    show_default=True,
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help="Output path for llms.txt.",
)
def generate_llms(output_file: Path) -> None:
    """Write a static llms.txt describing the Canopy framework.

    Documents CanvasSession, CanvasClient, CanvasAPIError, Canopy kwargs,
    pagination behaviour, async usage, and common usage patterns.
    """
    output_file.write_text(LLMS_TXT, encoding="utf-8")
    size_kb = output_file.stat().st_size / 1024
    click.echo(f"✓ Written → {output_file} ({size_kb:.1f} KB)")


@cli.command()
@click.option(
    "-a",
    "--apis-folder",
    required=True,
    type=click.Path(file_okay=False, readable=True, path_type=Path),
    help="Folder containing generated API files.",
)
@click.option(
    "-o",
    "--output-folder",
    default=".",
    show_default=True,
    type=click.Path(file_okay=False, writable=True, path_type=Path),
    help="Folder to write llms.txt and apis_index.txt into.",
)
@click.pass_context
def generate_all(
    ctx: click.Context,
    apis_folder: Path,
    output_folder: Path,
) -> None:
    """Run generate-llms and generate-index in one step.

    Always indexes both sync and async modules. Use generate-index directly
    if you need --sync-only or --async-only.
    """
    output_folder.mkdir(parents=True, exist_ok=True)
    ctx.invoke(generate_llms, output_file=output_folder / "llms.txt")
    ctx.invoke(
        generate_index,
        apis_folder=apis_folder,
        output_file=output_folder / "apis_index.txt",
        sync_only=False,
        async_only=False,
    )


if __name__ == "__main__":
    cli()
