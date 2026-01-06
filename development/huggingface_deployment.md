Context: Huggingface deployment sheet. 



Sheet with the non-negotiables for HF deployment: 
– HF space creation function 
– HF file upload function with deployment parameters 
– work in /app directory
– create a private space except and if one need to connect to the space via api, choose gradio sdk 




Interaction: 


Build:
Dockerfile/start.sh clones repo and then builds the application within the HF space. 
May change with different sdk
Log communication must always be enabled
Fast API communication should be enabled except noted otherwise
User needs to be informed about which secrets to deploy (e.g. token: bool = Depends(api_auth) & hf_api = HfApi(token=token)


)
README File needs to follow these rules depending on SDK 
e.g. ---
title: Basic Docker SDK Space
emoji: 🐳
colorFrom: purple
colorTo: gray
sdk: docker
app_port: 7860
---

templates and dependencies for SDKs:
Add the dependencies
For the Hot Dog Classifier we’ll be using a 🤗 Transformers pipeline to use the model, so we need to start by installing a few dependencies. This can be done by creating a requirements.txt file in our repository, and adding the following dependencies to it:
transformers
torch
The Spaces runtime will handle installing the dependencies!
Create the Gradio interface
To create the Gradio app, make a new file in the repository called app.py, and add the following code:
import gradio as gr
from transformers import pipeline

pipeline = pipeline(task="image-classification", model="julien-c/hotdog-not-hotdog")

def predict(input_img):
    predictions = pipeline(input_img)
    return input_img, {p["label"]: p["score"] for p in predictions} 

gradio_app = gr.Interface(
    predict,
    inputs=gr.Image(label="Select hot dog candidate", sources=['upload', 'webcam'], type="pil"),
    outputs=[gr.Image(label="Processed Image"), gr.Label(label="Result", num_top_classes=2)],
    title="Hot Dog? Or Not?",
)

if __name__ == "__main__":
    gradio_app.launch()


# Docker Spaces

Spaces accommodate custom [Docker containers](https://docs.docker.com/get-started/) for apps outside the scope of Streamlit and Gradio. Docker Spaces allow users to go beyond the limits of what was previously possible with the standard SDKs. From FastAPI and Go endpoints to Phoenix apps and ML Ops tools, Docker Spaces can help in many different setups.

## Setting up Docker Spaces

Selecting **Docker** as the SDK when [creating a new Space](https://huggingface.co/new-space) will initialize your Space by setting the `sdk` property to `docker` in your `README.md` file's YAML block. Alternatively, given an existing Space repository, set `sdk: docker` inside the `YAML` block at the top of your Spaces **README.md** file. You can also change the default exposed port `7860` by setting `app_port: 7860`. Afterwards, you can create a usual `Dockerfile`.

```Yaml
---
title: Basic Docker SDK Space
emoji: 🐳
colorFrom: purple
colorTo: gray
sdk: docker
app_port: 7860
---
```

Internally you could have as many open ports as you want. For instance, you can install Elasticsearch inside your Space and call it internally on its default port 9200.

If you want to expose apps served on multiple ports to the outside world, a workaround is to use a reverse proxy like Nginx to dispatch requests from the broader internet (on a single port) to different internal ports.

## Secrets and Variables Management
 

You can manage a Space's environment variables in the Space Settings. Read more [here](./spaces-overview#managing-secrets).

### Variables

#### Buildtime

Variables are passed as `build-arg`s when building your Docker Space. Read [Docker's dedicated documentation](https://docs.docker.com/engine/reference/builder/#arg) for a complete guide on how to use this in the Dockerfile.

```Dockerfile
    # Declare your environment variables with the ARG directive
    ARG MODEL_REPO_NAME

    FROM python:latest
    # [...]
    # You can use them like environment variables
    RUN predict.py $MODEL_REPO_NAME
```

#### Runtime

Variables are injected in the container's environment at runtime. 

### Secrets

#### Buildtime

In Docker Spaces, the secrets management is different for security reasons. Once you create a secret in the [Settings tab](./spaces-overview#managing-secrets), you can expose the secret by adding the following line in your Dockerfile:

For example, if `SECRET_EXAMPLE` is the name of the secret you created in the Settings tab, you can read it at build time by mounting it to a file, then reading it with `$(cat /run/secrets/SECRET_EXAMPLE)`.

See an example below:
```Dockerfile
# Expose the secret SECRET_EXAMPLE at buildtime and use its value as git remote URL
RUN --mount=type=secret,id=SECRET_EXAMPLE,mode=0444,required=true \
 git init && \
 git remote add origin $(cat /run/secrets/SECRET_EXAMPLE)
```

```Dockerfile
# Expose the secret SECRET_EXAMPLE at buildtime and use its value as a Bearer token for a curl request
RUN --mount=type=secret,id=SECRET_EXAMPLE,mode=0444,required=true \
    curl test -H 'Authorization: Bearer $(cat /run/secrets/SECRET_EXAMPLE)'
```

#### Runtime

Same as for public Variables, at runtime, you can access the secrets as environment variables. For example, in Python you would use `os.environ.get("SECRET_EXAMPLE")`. Check out this [example](https://huggingface.co/spaces/DockerTemplates/secret-example) of a Docker Space that uses secrets.

## Permissions

The container runs with user ID 1000. To avoid permission issues you should create a user and set its `WORKDIR` before any `COPY` or download.

```Dockerfile
# Set up a new user named "user" with user ID 1000
RUN useradd -m -u 1000 user

# Switch to the "user" user
USER user

# Set home to the user's home directory
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Set the working directory to the user's home directory
WORKDIR $HOME/app

# Try and run pip command after setting the user with `USER user` to avoid permission issues with Python
RUN pip install --no-cache-dir --upgrade pip

# Copy the current directory contents into the container at $HOME/app setting the owner to the user
COPY --chown=user . $HOME/app

# Download a checkpoint
RUN mkdir content
ADD --chown=user https:// content/
```

Always specify the `--chown=user` with `ADD` and `COPY` to ensure the new files are owned by your user.

If you still face permission issues, you might need to use `chmod` or `chown` in your `Dockerfile` to grant the right permissions. For example, if you want to use the directory `/data`, you can do:

```Dockerfile
RUN mkdir -p /data
RUN chmod 777 /data
```

You should always avoid superfluous chowns.
> [!WARNING]
> Updating metadata for a file creates a new copy stored in the new layer. Therefore, a recursive chown can result in a very large image due to the duplication of all affected files.

Rather than fixing permission by running `chown`:
```
COPY checkpoint .
RUN chown -R user checkpoint
```
you should always do:
```
COPY --chown=user checkpoint .
```
(same goes for `ADD` command)

## Data Persistence

The data written on disk is lost whenever your Docker Space restarts, unless you opt-in for a [persistent storage](./spaces-storage) upgrade.

If you opt-in for a persistent storage upgrade, you can use the `/data` directory to store data. This directory is mounted on a persistent volume, which means that the data written in this directory will be persisted across restarts.

At the moment, `/data` volume is only available at runtime, i.e. you cannot use `/data` during the build step of your Dockerfile.

You can also use our Datasets Hub for specific cases, where you can store state and data in a git LFS repository. You can find an example of persistence [here](https://huggingface.co/spaces/Wauplin/space_to_dataset_saver), which uses the [`huggingface_hub` library](https://huggingface.co/docs/huggingface_hub/index) for programmatically uploading files to a dataset repository. This Space example along with [this guide](https://huggingface.co/docs/huggingface_hub/main/en/guides/upload#scheduled-uploads) will help you define which solution fits best your data type.

Finally, in some cases, you might want to use an external storage solution from your Space's code like an external hosted DB, S3, etc.

### Docker container with GPU

You can run Docker containers with GPU support by using one of our GPU-flavored [Spaces Hardware](./spaces-gpus).

We recommend using the [`nvidia/cuda`](https://hub.docker.com/r/nvidia/cuda) from Docker Hub as a base image, which comes with CUDA and cuDNN pre-installed.

During Docker buildtime, you don't have access to a GPU hardware. Therefore, you should not try to run any GPU-related command during the build step of your Dockerfile. For example, you can't run `nvidia-smi` or `torch.cuda.is_available()` building an image. Read more [here](https://github.com/NVIDIA/nvidia-docker/wiki/nvidia-docker#description).

## Read More

- [Full Docker demo example](spaces-sdks-docker-first-demo)
- [List of Docker Spaces examples](spaces-sdks-docker-examples)
- [Spaces Examples](https://huggingface.co/SpacesExamples)


Users need to stream Space logs from the UI. We could introduce a method to do that as well from a script using requests with stream=True. Note: authentication is done using a jwt instead of an user auth token. Retrieving a jwt token and streaming logs are 2 completely different topics but we need the first to implement the later. Here is a draft of how to do that:


import json
from typing import Literal

from huggingface_hub import constants
from huggingface_hub.utils import build_hf_headers, get_session, hf_raise_for_status


def get_space_logs_sse(space_id: str, level: Literal["build", "run"] = "run"):
    # fetch a JWT token to access the API
    jwt_url = f"{constants.ENDPOINT}/api/spaces/{space_id}/jwt"
    response = get_session().get(jwt_url, headers=build_hf_headers())
    hf_raise_for_status(response)
    jwt_token = response.json()["token"]  # works for 24h (see "exp" field)

    # fetch the logs
    logs_url = f"https://api.hf.space/v1/{space_id}/logs/{level}"

    with get_session().get(logs_url, headers=build_hf_headers(token=jwt_token), stream=True) as response:
        hf_raise_for_status(response)
        for line in response.iter_lines():
            if not line.startswith(b"data: "):
                continue
            line_data = line[len(b"data: "):]
            try:
                event = json.loads(line_data.decode())
            except json.JSONDecodeError as e:
                print(e)
                continue # ignore (for example, empty lines or `b': keep-alive'`)
            print(event["timestamp"], event["data"])

get_space_logs_sse("Wauplin/space_to_dataset_saver")


Not sure though we want to officially support this. I'm putting this snippet here in case it helps people. Let's implement it if we see enough interest around that feature. Generating a jwt and streaming logs can be done in 2 separate PRs.

@api_router.post("/create_project", response_class=JSONResponse)
async def api_create_project(project: APICreateProjectModel, token: bool = Depends(api_auth)):
    """
    Creates a new project.

    NOTE: This endpoint currently contains:
    - task routing logic
    - parameter merging
    - hardware selection
    - job creation
    - direct backend calls

    These should be delegated to internal FastAPI microservices in the future.
    """

    # -------------------------------
    # 🔧 1. PARAMETER EXTRACTION
    # -------------------------------
    # This is fine, but consider moving validation/normalization to a shared service.
    provided_params = project.params.model_dump()

    # -------------------------------
    # 🔧 2. HARDWARE RESOLUTION
    # -------------------------------
    # RECOMMENDATION:
    # Replace this with a call to a "hardware-resolver" microservice.
    # Example future call:
    # hardware = hardware_service.resolve(project.hardware)
    if project.hardware == "local":
        hardware = "local-ui"
    else:
        hardware = project.hardware

    logger.info(provided_params)
    logger.info(project.column_mapping)

    # -------------------------------
    # 🔧 3. TASK ROUTING
    # -------------------------------
    # RECOMMENDATION:
    # This block should be extracted into a "task-router" microservice or module.
    # The API should not know how tasks map to PARAMS or trainers.
    task = project.task
    if task.startswith("llm"):
        params = PARAMS["llm"].copy()  # copy() prevents global mutation
        trainer = task.split(":")[1]
        params.update({"trainer": trainer})
    elif task.startswith("st:"):
        params = PARAMS["st"].copy()
        trainer = task.split(":")[1]
        params.update({"trainer": trainer})
    elif task.startswith("vlm:"):
        params = PARAMS["vlm"].copy()
        trainer = task.split(":")[1]
        params.update({"trainer": trainer})
    elif task.startswith("tabular"):
        params = PARAMS["tabular"].copy()
    else:
        params = PARAMS[task].copy()

    # -------------------------------
    # 🔧 4. PARAMETER MERGING
    # -------------------------------
    # RECOMMENDATION:
    # Move this into a "project-params-service" so that merging rules are centralized.
    params.update(provided_params)

    # -------------------------------
    # 🔧 5. PARAM OBJECT CONSTRUCTION
    # -------------------------------
    # RECOMMENDATION:
    # This should be delegated to a "project-service" microservice.
    # The API layer should not construct AppParams directly.
    app_params = AppParams(
        job_params_json=json.dumps(params),
        token=token,
        project_name=project.project_name,
        username=project.username,
        task=task,
        data_path=project.hub_dataset,
        base_model=project.base_model,
        column_mapping=project.column_mapping.model_dump() if project.column_mapping else None,
        using_hub_dataset=True,
        train_split=project.train_split,
        valid_split=project.valid_split,
        api=True,
    )

    # -------------------------------
    # 🔧 6. PARAM MUNGING
    # -------------------------------
    # RECOMMENDATION:
    # Move this into the project-service as well.
    params = app_params.munge()

    # -------------------------------
    # 🔧 7. JOB CREATION
    # -------------------------------
    # RECOMMENDATION:
    # Replace this with a call to a "job-service" FastAPI.
    # Example future call:
    # job_id = job_service.create_project(params, hardware)
    project = AutoTrainProject(params=params, backend=hardware)
    job_id = project.create()

    return {"message": "Project created", "job_id": job_id, "success": True}


@api_router.get("/version", response_class=JSONResponse)
async def api_version():
    """
    Simple endpoint — no changes needed.
    """
    return {"version": __version__}


@api_router.post("/stop_training", response_class=JSONResponse)
async def api_stop_training(job: JobIDModel, token: bool = Depends(api_auth)):
    """
    Stops a training job.

    NOTE:
    - Direct Hugging Face API calls should be moved to an internal "training-control-service".
    """
    hf_api = HfApi(token=token)
    job_id = job.jid
    try:
        # RECOMMENDATION:
        # Replace with: training_service.stop(job_id)
        hf_api.pause_space(repo_id=job_id)
    except Exception as e:
        logger.error(f"Failed to stop training: {e}")
        return {"message": f"Failed to stop training for {job_id}: {e}", "success": False}
    return {"message": f"Training stopped for {job_id}", "success": True}


@api_router.post("/logs", response_class=JSONResponse)
async def api_logs(job: JobIDModel, token: bool = Depends(api_auth)):
    """
    Fetch logs for a job.

    NOTE:
    - This entire block should be moved to a "logging-service" FastAPI.
    - The current API should simply forward the request.
    """
    job_id = job.jid

    # RECOMMENDATION:
    # Replace with: jwt_token = logging_service.get_jwt(job_id)
    jwt_url = f"{constants.ENDPOINT}/api/spaces/{job_id}/jwt"
    response = get_session().get(jwt_url, headers=build_hf_headers(token=token))
    hf_raise_for_status(response)
    jwt_token = response.json()["token"]

    logs_url = f"https://api.hf.space/v1/{job_id}/logs/run"

    _logs = []
    try:
        # RECOMMENDATION:
        # Replace with: logs = logging_service.stream_logs(job_id)
        with get_session().get(
            logs_url, headers=build_hf_headers(token=jwt_token), stream=True, timeout=3
        ) as response:
            hf_raise_for_status(response)
            for line in response.iter_lines():
                if not line.startswith(b"data: "):
                    continue
                line_data = line[len(b"data: ") :]
                try:
                    event = json.loads(line_data.decode())
                except json.JSONDecodeError:
                    continue
                _logs.append((event["timestamp"], event["data"]))

        _logs = "\n".join([f"{timestamp}: {data}" for timestamp, data in _logs])
        return {"logs": _logs, "success": True, "message": "Logs fetched successfully"}
    except Exception as e:
        if "Read timed out" in str(e):
            _logs = "\n".join([f"{timestamp}: {data}" for timestamp, data in _logs])
            return {"logs": _logs, "success": True, "message": "Logs fetched successfully"}
        return {"logs": str(e), "success": False, "message": "Failed to fetch logs"}



Adaption to internal FastAPI services
Identify jobs of the app that are fundamental
Identify use cases of interactions with the outside
Categorise entry points. 

Now you are ready to adapt the code according to these recommendations: 
Below is a **cleanly annotated version of your code**, with **inline comments** showing *exactly where and how* to modularize the logic so that this API can later connect to **internal FastAPI microservices** (task router, job service, logging service, hardware resolver, etc.).

After the code, you’ll find a **succinct bullet‑point summary** describing how internal FastAPIs can plug into these endpoints 

## **1. Introduce a Service Layer Between Routes and Logic**
Each route should call a service instead of doing the work itself.

Example:

```
job_id = job_service.create_project(params, hardware)
```

This makes it trivial to replace the service with a remote FastAPI later.

---

## **2. Split Responsibilities Into Microservices**

| Microservice | Responsibilities |
|-------------|------------------|
| **task-router-service** | Resolve task → trainer → default params |
| **hardware-service** | Map hardware names to backend runners |
| **project-service** | Build AppParams, validate inputs, merge params |
| **job-service** | Create, start, stop jobs |
| **logging-service** | Stream logs, fetch JWT tokens |
| **auth-service** | Validate tokens, issue tokens |

---

## **3. Replace Direct Class Instantiation With HTTP Calls**
Instead of:

```python
AutoTrainProject(params=params, backend=hardware).create()
```

Use:

```python
requests.post("http://job-service/create", json={...})
```

---

## **4. Use Dependency Injection for Service Clients**
Example:

```python
def get_job_service():
    return JobServiceClient(base_url="http://job-service")

@router.post("/create_project")
async def create_project(..., job_service=Depends(get_job_service)):
    job_service.create(...)
```

---

## **5. Standardize Error Models Across All Services**
Define a shared schema:

```json
{
  "success": false,
  "error_code": "TASK_NOT_FOUND",
  "message": "..."
}
```

---

## **6. Use a Shared Configuration Layer**
Move:

- PARAMS
- hardware mappings
- endpoint URLs

…into a config file or config service.

---

## **7. Use Async HTTP Clients for Internal Calls**
Use `httpx.AsyncClient` to communicate between FastAPIs efficiently.

---

## **8. Keep This API as a “Gateway API”**




