Title: Improvements to the Netbox webhook receiver
Date: 2020-12-19 12:36
Author: kirchnerl
Category: Programming
Tags: Celery, FastAPI, Netbox, Python
Slug: improvements-to-the-netbox-webhook-receiver
Status: published

*You can find the the code used in this post [here](https://github.com/Kircheneer/webhook_receiver/tree/v0.1.0).
If you just need a webhook receiver for Netbox follow the instructions in the README.md file in that repository.*

This is a follow-up to my earlier blog post[Netbox webhook receiver with Python, Celery and FastAPI](https://blog.kirchne.red/programming/netbox-webhook-receiver-with-python-celery-and-fastapi/).
Here we see two major improvements over the previous iteration:

- Consolidating webhook configuration on the [Netbox](https://github.com/netbox-community/netbox)
  side into a single webhook
- Implementing a plugin system, which allows users to share their integrations.

## Consolidate webhook configuration

The first implementation of the task registry class from the last blog post looked like this.

```python
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

When receiving a webhook on the [FastAPI](https://fastapi.tiangolo.com/) side, you had to call
`task_registry.execute(request, 'model', 'action')` which is redundant, because the request body already contains the
model and the action. The model and action was also present in the url (e.g. `webhooks.example.local/tenant/create`),
which required specific webhook configuration on the Netbox side for every model/action combination you wanted to
utilize. Furthermore, this registry is celery-unaware, which meant that all the tasks to be run on the webhook triggers
had to be decorated with both the `@celery.task` decorator as well as `@task_registry.register`. The following task
registry implementation solves both of these problems (changes highlighted in bold):

```python
 class TaskRegistry:       
    """       
    Registry for tasks to be executed when model and action conditions are met.        
    """               
    def __init__(self, celery: Celery):
        self.celery = celery
        self.registry: Dict[str, Dict[str, Set[Task]]] = {}       
       
    def register(self, model: str, event: str) -> Callable[[Callable], Callable]:     
        """       
        Decorator to register tasks in the registry.   
        :param model: Model to register the task for.    
        :param event: Event to register the task for.  
        :return: A decorator adding the decorated function to the registry.      
        """       
                
        if model not in self.registry:       
            self.registry[model] = {}      
        if event not in self.registry[model]:       
            self.registry[model][event] = set()       

         def decorator(function: Callable): 
            task = self.celery.register_task(self.celery.task(function))    
            self.registry[model][event].add(task)    
            return function       
                
        return decorator       
  
    async def execute(self, request: Request) -> Optional[List[Any]]:   
        """       
        Execute tasks in the registry that are assigned to the model and the action.     
        :param request: The request to pass into the task.       
        :param model: The model to filter the tasks.      
        :param action: The action to filters the tasks.   
        :return: A (possibly empty) list of task results or None if no tasks ran.  
        """       
                
        data = await request.json()     
        try:       
            tasks_to_run = self.registry[data['model']][data['event']]   
        except KeyError:       
            logger.warning(    
                f"No tasks configured for model {data['model']} and action {data['event']}."   
            )       
            return None   
        return [f.delay(data) for f in tasks_to_run] 
```

## Implement plugin functionality

We now need the following things to achieve the plugin functionality:

- Register plugin tasks without them knowing of the celery instance
- Register plugins with a root registry
- Name plugins to allow for useful logging

First, we abstract common code from the plugin and the root registry into a base class. Because the plugin registry
will hold callables while the root registry holds celery tasks, we also create a typing generic:

```python
# Generic typevar for task registries              
T = TypeVar("T") 

class _TaskRegistryBase(Generic[T]):                
    """                 
    Base class for all plugin and root task registries.                
    """                         
    def __init__(self):                 
        self.registry: Dict[str, Dict[str, Set[T]]] = {}       
     
    def _ensure_present(self, model: str, event: str) -> None:            
        """            
        Ensure the necessary dictionary keys are present                       
        :param model: Model key to be present.                      
        :param event: Event key to be present.                      
        """       
                
        if model not in self.registry:                       
            self.registry[model] = {}                      
        if event not in self.registry[model]:                      
            self.registry[model][event] = set() 
```

From this base we can inherit the root task registry, which is celery-aware and therefore holds celery tasks:

```python
 class RootTaskRegistry(_TaskRegistryBase[Task]):              
    """       
    Registry for tasks to be executed when model and action conditions are met.      
    """
```

Note how the class inherits `_TaskRegistryBase[Task]`, this indicated that the registry holds celery tasks.
The `__init__`, `execute` and `register` methods don't need to be changed for this. Only a new method is added to allow
for the registration of plugin registries. This method iterates over the task registry of the plugin, adds all the
tasks to the root registry and then manually applies the `register` decorator (which in turn also applies the
`celery.task` which then turns the functions into tasks that can be run by celery):

```python
 def register_plugin(self, plugin: PluginTaskRegistry) -> None:   
        """        
        Register the tasks a plugin has collected with the root registry.      
        :param plugin: The plugin.     
        """       
        logger.info(f"Registering plugin with name {plugin.name}.")       
        for model, events in plugin.registry.items():   
            for event, tasks in plugin.registry[model].items():   
                for task in tasks:       
                    # Manually apply decorator   
                    self.register(model, event)(task) 
```

Finally, the plugin registry has to be created. We pass a `name` parameter to the `__init__` method in order to
identify the plugin when logging and then create the register decorator. Since the class is unaware of celery, this
only registers the task in the plugin task registry to later be registered whith the root registry (as evident by the
`Callable` in the inherited class).

```python
 class PluginTaskRegistry(_TaskRegistryBase[Callable]):  
    """       
    Handles plugin task registration.   
       
    Instantiate inside of plugin in order to designate tasks for registration 
    in the task registry.    
    """       
     
    def __init__(self, name: str):   
        """       
        :param name: Name of the plugin   
        """       
                
        self.name = name    
        super(PluginTaskRegistry, self).__init__()       
                
    def register(self, model: str, event: str):   
        self._ensure_present(model, event)       
                
        def decorator(function):       
            self.registry[model][event].add(function)       
            return function       
                    
        return decorator 
```

The FastAPI app now has to import plugins dynamically. The idea for this is taken from the Python [documentation](https://packaging.python.org/guides/creating-and-discovering-plugins/) itself and is similar to the way its handled by [Flask](https://flask.palletsprojects.com). A `plugin_prefix` setting is added to the [Pydantic](https://pydantic-docs.helpmanual.io/) [Settings](https://pydantic-docs.helpmanual.io/usage/settings/) object in order to denote the prefix, plugin modules are then imported as follows. Just like that, all your plugins will run on the correct webhook triggers.

```python
class Settings(BaseSettings):            
    secret: str = ""      
    encoding: str = "utf-8"    
    digestmod: str = "sha512"    
    plugin_prefix: str = "nbintegrate_"     
    celery_broker: str = "redis://redis:6379"
    celery_backend: str = ""       
                      
app = FastAPI(title=__file__)            
settings = Settings() 
celery: Celery = Celery(               
    __file__, broker=settings.celery_broker, backend=settings.celery_backend       
)                  
registry: RootTaskRegistry = RootTaskRegistry(celery=celery) 

[...]

# Discover plugins by name                    
discovered_plugins = {       
    name: importlib.import_module(name)   
    for finder, name, ispkg in pkgutil.iter_modules()   
    if name.startswith(settings.plugin_prefix) 
}       
                      
# Register the plugins in the root registry    
for name, plugin_module in discovered_plugins.items():   
    logger.info(f"Found plugin {name}.")    
    try:       
        registry.register_plugin(plugin_module.plugin_task_registry)     
    except AttributeError:  
        logger.error(      
            f'Plugin {name} does not have a member called "plugin_task_registry". '    
            "Not loading plugin."       
        ) 
```

## Example plugin code

Finally, we want to take a look at an actual plugin. The example task code can be found in the `ngintegrate_example`
[folder](https://github.com/Kircheneer/webhook_receiver/tree/main/nbintegrate_example) in the git repository. Note how
there is now only one decorator on the tasks instead of two, which is much cleaner and less verbose.

```python
import logging       
from typing import Any       
                      
from webhook_receiver.task_registry import PluginTaskRegistry       

logging.basicConfig()              
logger = logging.getLogger(__file__)       
                
    
# An object with this exact name has to be present in every plugin.       
# It is automatically imported     
plugin_task_registry = PluginTaskRegistry(name="Example")       
                
@plugin_task_registry.register(model="tenant", event="created")             
def example_create_tenant(request: Any) -> None:           
    """           
    Example that fires on /tenant/create.         
    :param request: The result of the request.json() call on the original request. 
    """        
    logger.warning(f"Tenant {request['data']['name']} was created.") 
```
