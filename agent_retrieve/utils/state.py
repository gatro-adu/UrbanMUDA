from typing import List
from typing_extensions import TypedDict
from langgraph.graph import MessagesState

class GraphState(MessagesState):
    """
    Represents the state of our graph.

    Attributes:
        error : Binary flag for control flow to indicate whether test error was tripped
        messages : With user question, error messages, reasoning
        generation : Code solution
        iterations : Number of tries
    """

    error: str
    generation: str
    iterations: int