from typing import List, Dict
from pydantic import BaseModel, Field


class ScreenDimensions(BaseModel):
    width_px: int = Field(
        ...,
        description="Width of the application window or screen in pixels."
    )

    height_px: int = Field(
        ...,
        description="Height of the application window or screen in pixels."
    )


class ProcessSchema(BaseModel):

    process_id: str = Field(
        ...,
        description="Unique identifier for the automation process. Usually consists of process name and timestamp. Example: msword_insert_pagebreak_20260728_114500"
    )

    process_name: str = Field(
        ...,
        description="Unique machine-readable name of the automation process using snake_case. Example: msword_insert_pagebreak."
    )

    app_name: str = Field(
        ...,
        description="Name of the target application where the automation will be executed. Example: MS Word, Excel, Chrome."
    )

    user_intent: str = Field(
        ...,
        description="Natural language description of what the user wants to accomplish. Example: 'Insert a page break into the document.'"
    )

    description: str = Field(
        ...,
        description="A concise explanation of what the automation process performs from start to finish."
    )

    recorded_at: str = Field(
        ...,
        description="Timestamp when the automation process was recorded. Format: YYYYMMDD_HHMMSS."
    )

    screen_dimensions: ScreenDimensions = Field(
        ...,
        description="Screen resolution used while recording the automation process."
    )

    total_steps: int = Field(
        ...,
        description="Total number of individual automation steps contained in this process."
    )

    is_parameterized: bool = Field(
        ...,
        description="Indicates whether the process requires user-supplied parameters at runtime. True if parameters are required, otherwise False."
    )

    required_parameters: List[str] = Field(
        default_factory=list,
        description="List of parameter names required to execute the automation. Leave empty if no parameters are needed. Example: ['file_path', 'search_text']"
    )

    parameter_bindings: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping between parameter names and their assigned values or placeholders. Example: {'file_path': '{input_file}'}"
    )

    process_sequence: List[str] = Field(
        ...,
        description="Ordered list of step IDs representing the execution sequence of the automation process."
    )