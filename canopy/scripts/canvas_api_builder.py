import json
import keyword
import random
import time
from operator import itemgetter
from pathlib import Path
from typing import IO

import click
import httpx
from jinja2 import Environment, FileSystemLoader, PackageLoader

blacklist: list[str] = []


def fix_param_name(name: str) -> str:
    if name[-1:] == "]":
        return name.replace("[", "_").replace("]", "").replace("<", "").replace(">", "")
    elif keyword.iskeyword(name) or keyword.issoftkeyword(name):
        return f"_{name}"
    else:
        return name


def service_param_string(params: list[dict]) -> str:
    """Build a param string for the service method from a metadata class param section."""
    p = []
    k = []
    for param in params:
        name = fix_param_name(param["name"])
        if "required" in param and param["required"] is True:
            p.append(name)
        else:
            if "default" in param:
                k.append(f"{name}={param['default']}")
            else:
                k.append(f"{name}=None")
    p.sort()
    k.sort()
    return ", ".join(p + k)


def get_jinja_env() -> Environment:
    try:
        loader: PackageLoader | FileSystemLoader = PackageLoader("canopy", "templates")
    except ModuleNotFoundError:
        loader = FileSystemLoader(Path(__file__).parent.parent / "templates")
    env = Environment(loader=loader, trim_blocks=True, lstrip_blocks=True)
    env.filters["fix_param_name"] = fix_param_name
    env.filters["service_param_string"] = service_param_string
    return env


def _snake_to_pascal(name: str) -> str:
    """Convert a snake_case filename stem to PascalCase class name."""
    return "".join(part.capitalize() for part in name.split("_"))


# Build Single API file
@click.command()
@click.option(
    "-s",
    "--specfile",
    required=True,
    type=click.File(mode="r", encoding="utf-8"),
    help="The json specfile.",
)
@click.option(
    "-a",
    "--api-name",
    type=str,
    help="The name of the api class. Defaults to specfile base name",
)
@click.option(
    "-o",
    "--output-folder",
    required=True,
    type=click.Path(file_okay=False, writable=True, path_type=Path),
    help="Path to output the API file to.",
)
@click.option("--generate-async", is_flag=True, default=False, help="Generate async version")
def build_api_from_specfile(
    specfile: IO[str],
    api_name: str | None,
    output_folder: Path,
    generate_async: bool,
) -> None:
    """Build the specified API from the given spec file."""
    spec_path = Path(specfile.name)
    base_name = spec_path.name
    api_file_name = spec_path.stem

    if api_name is None:
        api_name = _snake_to_pascal(api_file_name)

    spec = json.load(specfile)
    env = get_jinja_env()

    if not generate_async:
        click.echo(f"Generating code for specfile: {base_name}")
        output_path = output_folder / f"{api_file_name}.py"
        api_template = env.get_template("canopy_api.py.jinja2")
        output_path.write_text(
            api_template.render(spec=spec, api_name=api_name, api_file_name=api_file_name)
        )
    else:
        click.echo(f"Generating async code for specfile: {base_name}")
        async_file_name = f"{api_file_name}_async"
        output_path = output_folder / f"{async_file_name}.py"
        api_template = env.get_template("canopy_api_async.py.jinja2")
        output_path.write_text(
            api_template.render(spec=spec, api_name=api_name, api_file_name=async_file_name)
        )


# Build Canvas Client file
@click.command()
@click.option(
    "-a",
    "--apis-folder",
    required=True,
    type=click.Path(file_okay=False, readable=True, path_type=Path),
    help="Folder with API files",
)
def build_canvas_client_file(apis_folder: Path) -> None:
    """Build the Canvas client file based on the generated APIs."""
    excluded_files = {"canvas_client.py", "__init__.py"}
    click.echo(f"Generating canvas_client.py file in {apis_folder.resolve()}")

    api_module_path = str(apis_folder).rstrip("/").replace("/", ".") + "."

    generated_api_files = []
    for api_path in apis_folder.iterdir():
        if api_path.name not in excluded_files and api_path.suffix == ".py":
            generated_api_files.append(
                {
                    "base_name": api_path.stem,
                    "class_name": _snake_to_pascal(api_path.stem),
                }
            )

    env = get_jinja_env()
    client_template = env.get_template("canvas_client.py.jinja2")
    Path("canvas_client.py").write_text(
        client_template.render(
            api_module_path=api_module_path,
            generated_api_files=sorted(generated_api_files, key=itemgetter("base_name")),
        )
    )


# Build All APIs
@click.command()
@click.option(
    "-s",
    "--specs-folder",
    required=True,
    type=click.Path(file_okay=False, readable=True, path_type=Path),
    help="Path for specfiles",
)
@click.option(
    "-o",
    "--output-folder",
    required=True,
    type=click.Path(file_okay=False, writable=True, path_type=Path),
    help="Path to output the API file to.",
)
@click.pass_context
def build_all_apis(ctx: click.Context, specs_folder: Path, output_folder: Path) -> None:
    """Build all APIs from downloaded specfiles."""
    for spec_path in specs_folder.iterdir():
        if spec_path.name not in blacklist:
            with spec_path.open() as f:
                ctx.invoke(
                    build_api_from_specfile,
                    specfile=f,
                    api_name=None,
                    output_folder=output_folder,
                )


# Rebuild APIs
@click.command()
@click.option(
    "-s",
    "--specs-folder",
    required=True,
    type=click.Path(file_okay=False, readable=True, path_type=Path),
    help="Path for specfiles",
)
@click.option(
    "-a",
    "--apifolder-path",
    required=True,
    type=click.Path(file_okay=False, writable=True, path_type=Path),
    help="Path for API files",
)
@click.pass_context
def rebuild_apis(ctx: click.Context, specs_folder: Path, apifolder_path: Path) -> None:
    """Rebuild all APIs from downloaded specfiles."""
    excluded_files = {"canvas_client.py", "__init__.py"}
    for api_path in apifolder_path.iterdir():
        if not api_path.is_file() or api_path.name in excluded_files:
            continue
        is_async = "async" in api_path.stem
        base_stem = api_path.stem.replace("_async", "") if is_async else api_path.stem
        spec_path = specs_folder / f"{base_stem}.json"
        with spec_path.open() as f:
            ctx.invoke(
                build_api_from_specfile,
                specfile=f,
                api_name=None,
                output_folder=apifolder_path,
                generate_async=is_async,
            )


# Update spec files
@click.command()
@click.option(
    "-s",
    "--specs-folder",
    required=True,
    type=click.Path(file_okay=False, readable=True, path_type=Path),
    help="Path for specfiles",
)
@click.option(
    "-n",
    "--spec-name",
    default=None,
    help="Download a single spec file by name (e.g. assignments.json)",
)
def update_spec_files(specs_folder: Path, spec_name: str | None) -> None:
    """Update spec files from Instructure API docs."""
    base_url = "https://canvas.instructure.com/doc/api/"

    if spec_name:
        spec_names = [spec_name]
    else:
        spec_names = [
            spec["path"][1:] for spec in httpx.get(f"{base_url}api-docs.json").json()["apis"]
        ]

    total = len(spec_names)
    for i, name in enumerate(spec_names, 1):
        click.echo(f"Fetching {name} ({i}/{total})...")

        retries = 3
        for attempt in range(1, retries + 1):
            r = httpx.get(f"{base_url}{name}")

            if r.status_code == 200:
                spec_path = specs_folder / name
                spec_path.write_bytes(r.content)
                click.echo(f"  ✓ Updated {spec_path}")
                break
            elif r.status_code == 202:
                wait = 30 * attempt  # 30s, 60s, 90s backoff
                click.echo(
                    f"  ⚠ Rate limited (202) on attempt {attempt}/{retries}. Waiting {wait}s..."
                )
                time.sleep(wait)
            else:
                click.echo(f"  ✗ Failed to retrieve {name}. Status Code: {r.status_code}")
                break
        else:
            click.echo(f"  ✗ Gave up on {name} after {retries} attempts.")

        if i < total:
            delay = random.uniform(2.0, 5.0)
            click.echo(f"  Sleeping {delay:.1f}s before next request...")
            time.sleep(delay)


@click.group()
def cli() -> None:
    pass


cli.add_command(build_api_from_specfile)
cli.add_command(build_canvas_client_file)
cli.add_command(build_all_apis)
cli.add_command(update_spec_files)
cli.add_command(rebuild_apis)

if __name__ == "__main__":
    cli()
