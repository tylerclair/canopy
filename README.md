# Canopy


A helper library for the Instructure Canvas API base on the basic request handling of Py3Canvas and modified API spec files

## Installation

### Runtime Only

**With uv (recommended):**
```bash
uv add git+https://github.com/tylerclair/canopy.git
```

**With pip:**
```bash
pip install git+https://github.com/tylerclair/canopy.git
```

### Optional Dependencies
 
Canopy has three optional dependency groups depending on your use case:
 
#### `builder`
Required for generating API modules from Canvas spec files using `canopy_build`.
 
**With uv:**
```bash
uv add "canopy[builder] @ git+https://github.com/tylerclair/canopy.git"
```
 
**With pip:**
```bash
pip install "canopy[builder] @ git+https://github.com/tylerclair/canopy.git"
```
 
#### `extras`
Optional async rate limiting and environment variable support. Useful if you are managing Canvas API rate limits or loading credentials from a `.env` file.
 
- `aiolimiter` — async rate limiting for high-volume async API calls
- `python-dotenv` — load Canvas credentials from a `.env` file
 
**With uv:**
```bash
uv add "canopy[extras] @ git+https://github.com/tylerclair/canopy.git"
```
 
**With pip:**
```bash
pip install "canopy[extras] @ git+https://github.com/tylerclair/canopy.git"
```
 
#### `dev`
For contributors working on Canopy itself.
 
**With uv:**
```bash
uv add "canopy[dev] @ git+https://github.com/tylerclair/canopy.git"
```
 
**With pip:**
```bash
pip install "canopy[dev] @ git+https://github.com/tylerclair/canopy.git"
```
 
#### Installing multiple extras together
 
**With uv:**
```bash
uv add "canopy[builder,extras] @ git+https://github.com/tylerclair/canopy.git"
```
 
**With pip:**
```bash
pip install "canopy[builder,extras] @ git+https://github.com/tylerclair/canopy.git"
```

## Usage

In your project create two folders: `specs` and `apis`. These will contain the API spec files downloaded from Canvas live documentation which has the openAPI spec files, and the generated API files used for making API calls.

You can use the `canopy_build` script to download the spec files, generate the Canvas API modules in both synchronous and asynchronous versions, and generate the canvas client file that you can use in your own projects. You can use this directly in your project or you can generate them in a separate project, install Canopy, and then move the apis folder and canvas client to your own project if desired.

### Fetching spec files

**Downloading or updating all spec files**

```bash
canopy_build fetch-specs --specs-dir specs/
```

**Download or update an individual spec file**

```bash
canopy_build fetch-specs --specs-dir specs/ --spec accounts.json
```

>**Note:** Instructure has started to timeout the download script after so many downloads, after that you will get 202 errors. It's recommended to either download them individually or use a downloading extension in your browser to download all the spec files.

For more information on using this command run `canopy_build fetch-specs --help`

### Build API from spec file

**Synchronous**
```bash
canopy_build build --spec specs/accounts.json --output-dir apis/
```

**Asynchronous**
```bash
canopy_build build --spec specs/accounts.json --output-dir apis/ --async
```

>**Note:** The API modules are generated using a template. Make sure the code is valid before using it.

For more information on using this command run `canopy_build build --help`

### Build Canvas client file
```bash
canopy_build client --apis-dir apis/
```

### Build all APIs
>**Note**: It is generally not recommended to generate all the APIs at this time. There are many API endpoints that have issues that will cause the loading of the client to fail. Only after you correct *all* the issues within the API files will the client load without issues.

```bash
canopy_build build-all --specs-dir specs/ --output-dir apis/
```

For more information on using this command run `canopy_build build-all --help`

### Rebuild APIs

```bash
canopy_build rebuild --specs-dir specs/ --apis-dir apis/
```

For more information on using this command run `canopy_build rebuild --help`

### Excluding specs from processing

Some Canvas spec files contain malformed parameters that cause code generation to fail or produce invalid Python. You can maintain a local TOML file to exclude these specs from `build-all`, `rebuild`, and `fetch-specs`.

Copy the provided example file to get started:

```bash
cp excluded_specs.toml.example excluded_specs.toml
```

The file format is a single list of spec filenames:

```toml
# excluded_specs.toml
excluded = [
    "quiz_extensions.json",
    "plagiarism_detection.json",
]
```

Pass it to any command that processes multiple specs via `--exclude-file`:

```bash
canopy_build fetch-specs \
    --specs-dir specs/ \
    --exclude-file excluded_specs.toml

canopy_build build-all \
    --specs-dir specs/ \
    --output-dir apis/ \
    --exclude-file excluded_specs.toml

canopy_build rebuild \
    --specs-dir specs/ \
    --apis-dir apis/ \
    --exclude-file excluded_specs.toml
```

>`excluded_specs.toml` is gitignored by default — each user maintains their own list locally.

## Generating LLM documentation

The `canopy_docs` script generates LLM-readable reference files from your project's generated API modules. This is useful for providing context to LLMs when building applications on top of Canopy.

### Generate the Canopy framework reference

```bash
canopy_docs generate-llms
```

Writes a static `llms.txt` describing `CanvasSession`, `CanvasClient`, `CanvasAPIError`, pagination behaviour, async usage, and common usage patterns.

### Generate an index of all API methods

```bash
canopy_docs generate-index --apis-folder apis/
```

Parses your generated API files using AST and emits a compact method index with signatures and inferred return types, grouped by class.

### Generate both in one step

```bash
canopy_docs generate-all --apis-folder apis/
```

### Excluding specs from the index

The same `excluded_specs.toml` file used with `canopy_build` can be passed to `generate-index` and `generate-all` to keep excluded specs out of the generated documentation:

```bash
canopy_docs generate-index \
    --apis-folder apis/ \
    --exclude-file excluded_specs.toml

canopy_docs generate-all \
    --apis-folder apis/ \
    --exclude-file excluded_specs.toml
```

## Usage in your project

```python
from canvas_client import CanvasClient

canvas_url = "https://abc.instructure.com"
token = "your_token_here"

client = CanvasClient(canvas_url, token, max_per_page=100)
user_profile = client.users.get_user_profile("self")
print(user_profile)
```
## Asynchronous usage in your project

Canopy supports fully asynchronous API calls via `httpx.AsyncClient`. All requests including paginated ones are non-blocking, making it well suited for high-volume workloads where many independent requests can be made concurrently.

Here is an example of how we can take a list of student IDs and return their names:
```python
import asyncio
from canvas_client import CanvasClient
from time import perf_counter

canvas_url = "https://abc.instructure.com"
token = "your_token_here"

client = CanvasClient(canvas_url, token, max_per_page=100)

# Abbreviated for space
student_ids = [
    "123",
    "456",
    "789",
]


# asynchronous
async def get_user_details_async(student_id):
    user_details_async = await client.users_async.show_user_details(
        id=student_id
    )
    return user_details_async["name"]


# synchronous
def get_user_details(student_id):
    user_details = client.users.show_user_details(id=student_id)
    return user_details["name"]


async def main():
    # synchronous
    time_before = perf_counter()
    for student_id in student_ids:
        result = get_user_details(student_id)
        print(result)
    print(f"Total time (synchronous): {perf_counter() - time_before}")

    # asynchronous
    time_before = perf_counter()
    tasks = [get_user_details_async(student_id) for student_id in student_ids]
    results = await asyncio.gather(*tasks)
    print(results)
    print(f"Total time (asynchronous): {perf_counter() - time_before}")

    # asynchronous print as completed
    time_before = perf_counter()
    tasks = [get_user_details_async(student_id) for student_id in student_ids]
    for coro in asyncio.as_completed(tasks):
        name = await coro
        print(name)
    print(
        f"Total time (asynchronous print as completed): {perf_counter() - time_before}"
    )

asyncio.run(main())
```

This is the results of the above performance test with a list of 50 student IDs:
```bash
# Results removed for space
Total time (synchronous): 9.39928955299547
# Results removed for space
Total time (asynchronous): 1.3862317899911432
# Results removed for space
Total time (asynchronous print as completed): 0.9531320789974416
```

Now with 295 students:
```bash
Total time (synchronous): 50.22708906700427
Total time (asynchronous): 5.239625043002889
Total time (asynchronous print as completed): 4.629659270998657
```

## Connection management

`CanvasSession` supports context managers for proper connection cleanup. This is recommended for long-running applications or scripts that make many requests:
```python
# Synchronous
from canopy import CanvasSession

with CanvasSession(canvas_url, token) as session:
    # session is automatically closed when the block exits
    pass

# Asynchronous
async with CanvasSession(canvas_url, token) as session:
    # async session is automatically closed when the block exits
    pass
```