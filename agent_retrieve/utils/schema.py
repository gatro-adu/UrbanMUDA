from pydantic import BaseModel, Field
from typing import Annotated

# Data model
class code(BaseModel):
    """Schema for code solutions to questions about LCEL."""

    prefix: Annotated[str, Field(description="Description of the problem and approach")]
    imports: Annotated[str, Field(description="Code block import statements")]
    code: Annotated[str, Field(description="Code block not including import statements")]