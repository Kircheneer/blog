Title:Functional Programming Concepts in Network Automation
Date: 2022-04-20 21:40
Author: kirchnerl
Category: Programming
Tags: Python
Slug: functional-programming-concepts-in-network-automation
Status: draft

In this blog post I will map a couple of concepts from functional programming to network automation.
In order to achieve this, I first have to lay out a couple of concepts:

## Side effects

A side effect in functional programming is any mutation of state.

One prominent example of a side effect is any input/output (IO).
<!-- TODO: Give Example -->

Another example is mutation of any variables that don't purely reside in the scope of the function.
Take the following Python snippet as an example:

```python
messages_shortened = 0  # Global state

def shorten_message(message: str) -> str:
    """Truncate the message to 8 characters."""
    messages_shortened += 1  # Mutate global state
    return message[:8]
```

If you only take the input and output of this function into account, it might appear pure, but the state mutation can be
unexpected and therefore dangerous.