Title: Adding type hint support to NAPALM
Date: 2022-02-12 
Author: kirchnerl
Category: Programming
Tags: Mypy, NAPALM, Python
Slug: type-hinting-napalm
Status: published

Over the past year I have been working on adding type hinting (see
[PEP484](https://www.python.org/dev/peps/pep-0484/ "https://www.python.org/dev/peps/pep-0484/")) to the Network
Automation and Programmability Abstraction Layer with Multivendor support python library
([NAPALM](https://napalm.readthedocs.io/en/latest/ "https://napalm.readthedocs.io/en/latest/")). Type hinting is still
only used in a subset of all python libraries, so I thought it might be interesting to elaborate on the process.
Type hints in combination with a type checker such as [Mypy](http://mypy-lang.org/ "http://mypy-lang.org/") allow for
static analysis of Python programs. The following code is a example of a type hinted function:

```python
def sum_and_multiply(a: typing.List[int], b: int) -> int:
    """Sum the integers in a and multiply them by b."""
    return sum(a) * b
```

To start off I decided to only tackle the `NXOS` driver and the base `NetworkDriver` class. Type hinting all
the available drivers seemed like too big of a problem to tackle right of the bat.

## Prerequisites

Running Mypy against the submodule `napalm.base` with the `disallow-untyped-defs` flag yielded more than 600 errors
before I added any type annotations.

```python
$ mypy -p napalm.base --disallow-untyped-defs
[...]
Found 655 errors in 34 files (checked 25 source files)
```

These mostly consist of untyped function or method definitions. Another common error is an import that doesn't implement
type hints. At the time of writing, not a lot of dependencies of NAPALM implement type hints.

The `--disallow-untyped-defs` flag for `mypy`

> "reports an error whenever it encounters a function definition without type annotations"

(see [here](https://mypy.readthedocs.io/en/stable/command_line.html#untyped-definitions-and-calls)).
This allows for pretty good type checking coverage because all affected functions and methods from the checked modules
have to have type annotations.

## Getting started with type annotations

I found my starting point in type hinting the codebase in the models used for testing the
[getter methods](https://napalm.readthedocs.io/en/latest/support/index.html#getters-support-matrix "https://napalm.readthedocs.io/en/latest/support/index.html#getters-support-matrix"),
which are NAPALMs way of (vendor-independently) getting data from network devices in a common form. The following is an
excerpt from `napalm.base.test.models` showing the model that `get_facts` is tested against before any work towards
type hints was done.

```python
facts = {
    "os_version": str,
    "uptime": int,
    "interface_list": list,
    "vendor": str,
    "serial_number": str,
    "model": str,
    "hostname": str,
    "fqdn": str,
}
```

All the models were present in this format, which allows the unit tests to check, if the getter output data conforms to
this format. The following, however, isn't possible with this format:

```python
class ExampleDriver:
    def get_facts(self) -> facts:
        pass
```

This is because the dictionary doesn't have the field `__annotations__`, which is what Mypy evaluates.
The `typing` module (or the `typing_extensions` module before Python 3.7) provides a Type called
`TypedDict` (see [PEP589](https://www.python.org/dev/peps/pep-0589/)) to solve this. This type also allows for more
granularity than the standard `Dict` annotation. A `TypedDict` for the above model could look like this (using the
alternative syntax for ease of migration).

```python
from typing import TypedDict, List

FactsDict = TypedDict(
    "FactsDict",
    {
        "os_version": str,
        "uptime": int,
        "interface_list": List,
        "vendor": str,
        "serial_number": str,
        "model": str,
        "hostname": str,
        "fqdn": str,
    },
)
```

Note that not much has actually changed here, but it's now possible to use this type in type hints for the `get_facts` 
function from earlier.

```python
class ExampleDriver:
    def get_facts(self) -> Facts:
        pass
```

## Type hinting the NetworkDriver

With most of the data modeling out of the way, the next step was putting in the actual type hints. Any NAPALM driver (in
the core module or a 3rd party one) has to inherit the `NetworkDriver` class from `napalm.base.base`. This therefore
looked like a great starting point for adding type hints. After all the models were converted to `TypedDict` instances,
I was able to annotate a lot of the methods with just those models. While type hinting the code base further I found I
had made a lot of errors with the models I made in the first step. I gradually iterated on those until they worked for
both the NXOS SSH and NXAPI drivers.

## Bugs found

Over the course of the [NANOG 84 Hackathon](https://www.nanog.org/events/nanog-84-hackathon/) I added the last couple of
finishing touches to the [Pull Request](https://github.com/napalm-automation/napalm/pull/1476) corresponding to this
blog post. While going through that I did find the only straight-up bug in NAPALM that Mypy was able to uncover over the
course of this process. This was a broken import in an if-branch that the unit tests didn't cover. While this (probably)
never caused any problems in the wild, it's still good to know that the bug is fixed with the next release.

More importantly though any bugs of the same nature will be detected by the CI pipeline, which now runs Mypy on every
commit that's added to the NAPALM repository.

## Conclusion

Finally, I can say that this was a fantastic learning experience not only for Python type hinting, but also for the
NAPALM library itself. Adding all the relevant type hints lead me to parts of the codebase I hadn't seen yet and
therefore improved my understanding of the software. If you are looking for a Python project to do: Take a
look whether your favorite or most-used Python libraries have implemented type hinting and volunteer to do so if they
don't. You can check this by just type hinting your own code - Mypy will complain whenever you import code without type
hints. Maybe you are even interested in adding type hints to NAPALM itself, as of Feb 12 2022 only the NXOS driver and
the Base driver have type hints in them.

Fun-fact: The [Nornir](https://github.com/nornir-automation/nornir) framework had type hints everywhere but
didn't have a `py.typed` file at the module root. This meant that even though type hints were there, Mypy didn't pick up
upon those until said file was added - this is included in release `v3.1.0`. 