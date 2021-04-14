Title: Netbox webhook receiver with Python, Celery and FastAPI
Date: 2020-11-21 13:47
Author: kirchnerl
Category: Programming
Tags: Celery, FastAPI, Netbox, Python
Slug: netbox-webhook-receiver-with-python-celery-and-fastapi
Status: published

*You can find the the code used in this post* [*here*](https://github.com/Kircheneer/webhook_receiver)*. If you just
need a webhook receiver for Netbox follow the instructions in the README.md file in that repository.*

The [Netbox](https://github.com/netbox-community/netbox) IPAM and DCIM tool provides [webhooks](https://netbox.readthedocs.io/en/stable/additional-features/webhooks/) as a means of integrating with other software. External software you might want to notify of changes in Netbox might be network monitoring software (NMS) or a configuration management database (CMDB). While Netbox supports [Jinja2](https://jinja.palletsprojects.com) templating for the body of the webhook HTTP request you sometimes want to issue multiple requests in a particular sequence with some state on a single trigger event (such as a single device changing). You might also just want to run arbitrary code. In order to accomplish this it is necessary to implement a webhook receiver which is capable of execute such sequences. Faced with this challenge I decided to implement such an application using the [FastAPI](https://fastapi.tiangolo.com/) Python web framework and the [Celery](https://github.com/celery/celery) task queue.

### Setting up Celery and FastAPI

*If you're following along I recommend running the web app, redis database and the celery worker with Docker using
the* [*Dockerfile*](https://github.com/Kircheneer/webhook_receiver/blob/main/Dockerfile) *and*
[*docker-compose.yml*](https://github.com/Kircheneer/webhook_receiver/blob/main/docker-compose.yml) *from the GitHub
repository for ease of use and to optionally use* [*netbox-docker*](https://github.com/netbox-community/netbox-docker)
*in order to quickly spin up a Netbox testing instance.*

First we need to set up our FastAPI application and task queue. Getting FastAPI set up to trigger a Celery task is done
rather quickly as evident in the following code example. Point any webhook from Netbox at this and perform a
corresponding action in Netbox - this will already trigger the Celery task and subsequently log to the console of the
Celery worker.

```python
import logging

from celery import Celery
from fastapi import FastAPI, Request, HTTPException

logging.basicConfig()
logger = logging.getLogger(__file__)

app = FastAPI(title=__file__)
celery: Celery = Celery(
    __file__, broker="redis://redis:6379"
)

@celery.task
def task(request):
    logger.warning(f"I was triggered by a {request}.")

@app.post("/")
async def receive(request: Request) -> None:
    body = await request.json()
    task.delay(body)

```

### Authenticating the webhook

Netbox allows for the configuration of a secret for each webhook. The secret is then used to compute a HMAC digest
over the body of the webhook (in addition to the TLS already performed). This secret is passed as a HTTP Header
"X-Hook-Signature". The following code excerpt demonstrates the verify_hmac function, which handles this authentication
process, in conjunction with the corresponding FastAPI view. Notice how we call .body() on the Starlette
[Request](https://www.starlette.io/requests/#body) object in order to get a binary representation of the request
because this is how Netbox does it.

```python
import hmac

from fastapi import HTTPException

[...]

def verify_hmac(
    body: bytes,
    hexdigest: str,
    secret: str = "secret",
    encoding: str = "utf-8",
    digestmod: str = "sha512",
) -> bool:
    computed_hexdigest = hmac.new(
        secret.encode(encoding), body, digestmod=digestmod
    ).hexdigest()
    return hexdigest == computed_hexdigest


@app.post("/")
async def receive(request: Request) -> None: 
    body = await request.body()
    hexdigest = request.headers["X-Hook-Signature"]
    if not verify_hmac(body, hexdigest):
        raise HTTPException(status_code=403, detail="Shared secret mismatch.")
    body = await request.json()
    task.delay(body) 
```

### Registering tasks to specific endpoints

The goal for the following sections is to allow URLs such as `/tenant/create` for the webhook triggered when tenants
are created and then run tasks corresponding to this webhook whenever that endpoint is triggered. First of all we will
allow path parameters in the task:

```python
@app.post("/{model}/{action}")
async def receive(model: str, action: str, request: Request) -> None:
    body = await request.body()
    hexdigest = request.headers["X-Hook-Signature"]
    if not verify_hmac(body, hexdigest):
        raise HTTPException(status_code=403, detail="Shared secret mismatch.")
    body = await request.json()
    task.delay(body) 
```

Now we need to create a task registry to store the tasks. It needs to do the following things:

- Provide a mechanism for registration of devices
- Bulk-execute applicable tasks whenever an endpoint is called

The below class TaskRegistry provides a decorator `register`, which registers the decorated function as a task in the
registry.

```python
import logging
from typing import Callable, Any, List, Dict, Set, Optional

from celery import Task
from fastapi import Request

logging.basicConfig()
logger = logging.getLogger(__file__)


class TaskRegistry:
    def __init__(self):
        self.registry: Dict[str, Dict[str, Set[Task]]] = {}

    def register(self, model: str, action: str) -> Callable[[Callable], Callable]:
        if model not in self.registry:
            self.registry[model] = {}
        if action not in self.registry[model]:
            self.registry[model][action] = set()

        def decorator(function):
            self.registry[model][action].add(function)
            return function

        return decorator

    async def execute(self, request: Request, model: str, action: str) -> Optional[List[Any]]:
        try:
            tasks_to_run = self.registry[model][action]
        except KeyError:
            logger.warning(
                f"No tasks configured for model {model} and action {action}."
            )
            return None
        return [f.delay(await request.json()) for f in tasks_to_run]
```

This allows us to then define tasks like this:

```python
from task_registry import TaskRegistry

[...]

registry: TaskRegistry = TaskRegistry() 

@registry.register(model="tenant", action="create")
@celery.task
def task(request: Any) -> None:
    logger.warning(f"I was triggered by a {request}.") 
```

From the FastAPI view we can then call `execute` on the registry in order to run all the applicable tasks:

```python
[...]

@app.post("/{model}/{action}")
async def receive(model: str, action: str, request: Request) -> None:
    body = await request.body()
    hexdigest = request.headers["X-Hook-Signature"]
    if not verify_hmac(body, hexdigest):
        raise HTTPException(status_code=403, detail="Shared secret mismatch.")
    await registry.execute(request, model, action)
```

If you find that your tasks are not executing make sure that they are actually being imported. IDEs might remove the
import of the tasks if they are in seperate files and/or modules, because they don't pick up on either Celery tasks or
tasks registered in our own TaskRegistry.
