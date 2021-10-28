import click
import json
from jinja2 import Environment, FileSystemLoader
import os
import requests

blacklist = []


def fix_param_name(name):
    if name[-1:] == "]":
        return name.replace("[", "_").replace("]", "")
    else:
        return name


def service_param_string(params):
    """Takes a param section from a metadata class and returns a param string for the service method"""
    p = []
    k = []
    for param in params:
        name = fix_param_name(param["name"])
        if "required" in param and param["required"] is True:
            p.append(name)
        else:
            if "default" in param:
                k.append("{name}={default}".format(name=name, default=param["default"]))
            else:
                k.append("{name}=None".format(name=name))
    p.sort()
    k.sort()
    a = p + k
    return ", ".join(a)


def get_jinja_env():
    loader = FileSystemLoader(
        os.path.join(os.path.abspath(os.path.dirname(__file__)), "templates")
    )
    env = Environment(loader=loader, trim_blocks=True, lstrip_blocks=True)
    env.filters["fix_param_name"] = fix_param_name
    env.filters["service_param_string"] = service_param_string
    return env


# Build Single API file


@click.command()
@click.option(
    "--specfile", required=True, type=click.File(mode="r"), help="The json specfile."
)
@click.option("--api-name", type=str, help="The name of the api class. Defaults to ")
@click.option(
    "--output-folder",
    required=True,
    type=click.Path(file_okay=False, writable=True),
    help="Path to output the API file to.",
)
def build_api_from_specfile(specfile, api_name, output_folder):
    base_name = os.path.basename(specfile.name)

    click.echo(f"Generating code for specfile: {base_name}")

    output_file_name = base_name.replace(".json", ".py")

    if api_name is None:
        raw_api_name = list(base_name[: base_name.find(".")])
        api_name = ""
        capitalize = True
        for i in raw_api_name:
            if i == "_":
                capitalize = True
                continue
            if capitalize is True:
                api_name += i.capitalize()
                capitalize = False
            else:
                api_name += i

    spec = json.load(specfile)

    env = get_jinja_env()
    api_template = env.get_template("canopy_api.py.jinja2")
    with open(os.path.join(output_folder, output_file_name), "w") as api:
        api.write(
            api_template.render(
                spec=spec,
                api_name=api_name,
                base_name=base_name,
            )
        )


# Build All APIs


@click.command()
@click.option(
    "--specfile-path",
    required=True,
    type=click.Path(file_okay=False, readable=True),
    help="Path for specfiles",
)
@click.option(
    "--output-folder",
    required=True,
    type=click.Path(file_okay=False, writable=True),
    help="Path to output the API file to.",
)
@click.pass_context
def build_all_apis(ctx, specfile_path, output_folder):
    specs = os.listdir(specfile_path)
    for spec in specs:
        if not spec in blacklist:
            specfile = os.path.join(specfile_path, spec)
            with open(specfile, "r") as f:
                ctx.invoke(
                    build_api_from_specfile,
                    specfile=f,
                    api_name=None,
                    output_folder=output_folder,
                )
        else:
            continue


# Update spec files


@click.command()
@click.option(
    "--specfile-path",
    required=True,
    type=click.Path(file_okay=False, readable=True),
    help="Path for specfiles",
)
def update_spec_files(specfile_path):
    """Update spec files from Instructure API docs"""
    # specs = os.listdir(specfile_path)
    docsFile = "api-docs.json"
    baseUrl = "https://canvas.instructure.com/doc/api/"
    specs = requests.get(f"{baseUrl}{docsFile}").json()
    for spec in specs["apis"]:
        specName = spec["path"][1:]
        r = requests.get(f"{baseUrl}{specName}")
        if r.status_code == 200:
            specFile = os.path.join(specfile_path, specName)
            with open(specFile, "wb") as f:
                f.write(r.content)
                click.echo(f"Updated {specFile}")
        else:
            click.echo(
                f"Something went wrong trying to retrieve {specName}. Status Code: {r.status_code}"
            )


@click.group()
def cli():
    pass


cli.add_command(build_api_from_specfile)
cli.add_command(build_all_apis)
cli.add_command(update_spec_files)

if __name__ == "__main__":
    cli()
