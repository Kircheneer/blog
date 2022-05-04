Title:Functional Programming Concepts in Network Automation
Date: 2022-04-20 21:40
Author: kirchnerl
Category: Programming
Tags: Python
Slug: functional-programming-concepts-in-network-automation
Status: draft

In this blog post I will map a couple of concepts from functional programming to network automation. In order to achieve this, I first have to lay out a couple of concepts:

## Side effects

A side effect in functional programming is any mutation of state.

One prominent example of a side effect is any input/output (IO).

```python
import json

# Reading a file from disk
with open("file.json", "r") as f:
    content = json.load(f)

# Outputting the file contents to the terminal
print(f)
```

Another example is mutation of any variables that don't purely reside in the scope of the function. Take the following Python snippet as an example:

```python
messages_shortened = 0  # Global state

def shorten_message(message: str) -> str:
    """Truncate the message to 8 characters."""
    messages_shortened += 1  # Mutate global state
    return message[:8]
```

If you only take the input and output of this function into account, it might appear pure, but the state mutation can be unexpected and therefore dangerous.

## How side effects affect the programmer

Now you might ask what the point of programming is supposed to be if we can never have any side effects - and you would be correct. Without side effects you couldn't do any useful things such as signalling output back to the user. Being aware of the concept however and using side effects carefully can in my opinion greatly improve the readability of your code. 

Joel Spolsky made a good (but also debated) [point](https://www.joelonsoftware.com/2000/04/06/things-you-should-never-do-part-i/) when he said that 
> It's harder to read code than to write it.

You however don't have to fully agree to this in order to recognize that reading code is in fact quite hard, since writing it is definitely a hard thing in general. The point I'm trying to make is that the task of keeping everything that is happening inside a code base in your head can be quite difficult, which can make you appreciate the simplicity of a function that does not depend on or change any external state, but rather is self-contained, i.e. a pure function in the sense of functional programming.

## Applying this to network automation

In the examples I gave above I used python. Python itself is an object oriented programming language, in fact everything in Python is an object. It is however not only possible to write functional code in Python, but also very much possible to apply some of these concepts to Python programming in order to simplify your programs.

By keeping a functional core of the program where all logic is kept and then using that functional core inside of impure wrappers with desired side effects, you can keep your code quite testable while still having all the useful side effects you need.

The following are some examples of desirable side effects in network automation:
- Calling an external HTTP API
- Executing some command over SSH/NETCONF/etc.
- Reading from a JSON/YAML configuration file
- Signalling CLI messages to the end user

On the other hand, here are some tasks you might have to do in network automation that can easily
be implemented as pure, side-effect free functions:
- Transforming data from one schema to another such as to use data from a source of truth to configure
  a network device
- Generating configuration files (but not writing them to disk or applying them to a network device)
- Parsing CLI output from network devices into structured data