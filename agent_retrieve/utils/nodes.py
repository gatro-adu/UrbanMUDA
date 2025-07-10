import json
import os
import subprocess
import sys

from pathlib import Path
from bs4 import BeautifulSoup as Soup
from langchain_community.document_loaders.recursive_url_loader import RecursiveUrlLoader
from agent_retrieve.utils.state import GraphState
from agent_retrieve.utils.chain import code_gen_chain
from langchain_core.messages import ToolMessage, HumanMessage, AIMessage

# LCEL docs
url = "https://python.langchain.com/docs/concepts/lcel/"
loader = RecursiveUrlLoader(
    url=url, max_depth=20, extractor=lambda x: Soup(x, "html.parser").text
)
docs = loader.load()

# Sort the list based on the URLs and get the text
d_sorted = sorted(docs, key=lambda x: x.metadata["source"])
d_reversed = list(reversed(d_sorted))
concatenated_content = "\n\n\n --- \n\n\n".join(
    [doc.page_content for doc in d_reversed]
)


### Nodes

async def generate(state: GraphState):
    """
    Generate a code solution

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, generation
    """

    print("---GENERATING CODE SOLUTION---")

    # State
    messages = state["messages"]
    iterations = state["iterations"]
    error = state["error"]

    # We have been routed back to generation with an error
    if error == "yes":
        messages.append(HumanMessage(content="Now, try again. Invoke the code tool to structure the output with a prefix, imports, and code block:"))

    # Solution
    code_solution = await code_gen_chain.ainvoke(
        {"context": concatenated_content, "messages": messages}
    )
    if not isinstance(code_solution, dict):
        code_solution = json.loads(code_solution.model_dump_json())

    # Increment
    iterations = iterations + 1
    return {"generation": code_solution, "messages": [
        AIMessage(content=f"{code_solution['prefix']} \n Imports: {code_solution['imports']} \n Code: {code_solution['code']}"),
    ], "iterations": iterations}





async def reflect(state: GraphState):
    """
    Reflect on errors

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, generation
    """

    print("---GENERATING CODE SOLUTION---")

    # State
    messages = state["messages"]
    iterations = state["iterations"]
    code_solution = state["generation"]

    # Prompt reflection

    # Add reflection
    reflections = await code_gen_chain.ainvoke(
        {"context": concatenated_content, "messages": messages}
    )
    if not isinstance(reflections, dict):
        reflections = json.loads(reflections.model_dump_json())
    message = AIMessage(content=f"Here are reflections on the error: {reflections}")
    return {"generation": code_solution, "messages": [message], "iterations": iterations}



