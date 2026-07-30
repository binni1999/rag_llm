from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field
import json
import os
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_google_genai import (
    GoogleGenerativeAIEmbeddings,
    ChatGoogleGenerativeAI
)
from langchain_groq import ChatGroq


load_dotenv()

os.environ['GROQ_API_KEY'] = os.getenv('GROQ_API_KEY')
FAISS_DB = "Faiss_binni"

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001"
)
db = FAISS.load_local(
    FAISS_DB,
    embeddings,
    allow_dangerous_deserialization=True
)
retriever = db.as_retriever(
    search_kwargs={"k":9}
)
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
# -------------------------------------------------------------------
# 1. Define Output Schemas
# -------------------------------------------------------------------

class ParameterBinding(BaseModel):
    parameter_name: str = Field(
        ...,
        description="The name of the parameter bound to a specific step (e.g., 'top_margin', 'bottom_margin')."
    )
    post_keys: List[str] = Field(
        default_factory=list,
        description="List of key strokes pressed after entering the parameter (e.g., ['TAB'], ['ENTER'])."
    )

class ScreenDimensions(BaseModel):
    width_px: int = Field(1920, description="Width of screen in pixels.")
    height_px: int = Field(1200, description="Height of screen in pixels.")

class ProcessOutput(BaseModel):
    process_id: str = Field(..., description="Unique process ID timestamped string.")
    process_name: str = Field(..., description="Machine-readable process name in snake_case.")
    app_name: str = Field("MS Word", description="Target application name.")
    user_intent: str = Field(..., description="Natural language user intent description.")
    description: str = Field(..., description="Detailed description of what the process performs.")
    recorded_at: str = Field(..., description="Timestamp format YYYYMMDD_HHMMSS.")
    screen_dimensions: ScreenDimensions = Field(default_factory=ScreenDimensions)
    total_steps: int = Field(..., description="Total count of step IDs in process_sequence.")
    is_parameterized: bool = Field(False, description="Set to true if process requires runtime parameters, else false.")
    required_parameters: List[str] = Field(
        default_factory=list,
        description="List of required parameter names if parameterized (e.g. ['top_margin', 'bottom_margin']), else []."
    )
    parameter_bindings: Dict[str, ParameterBinding] = Field(
        default_factory=dict,
        description="Dictionary mapping step_id strings from process_sequence to ParameterBinding objects if parameterized, else {}."
    )
    process_sequence: List[str] = Field(..., description="Ordered list of step_id strings.")


# -------------------------------------------------------------------
# 2. RAG Pipeline Function
# -------------------------------------------------------------------

# SYSTEM_PROMPT = """
# You are an execution sequence generator for MS Word automation.
# You will receive:
# 1. A User Query describing an action to perform in MS Word.
# 2. A list of candidate atomic UI steps retrieved from the step repository.

# Your Task:
# 1. Analyze the user query and identify if it requires dynamic user inputs/parameters (e.g., margins, font size, text string, color).
# 2. Filter and sequence the exact step IDs (`step_id`) required to fulfill the request in `process_sequence`.
# 3. Calculate `total_steps` as the exact count of steps in `process_sequence`.

# Condition A: If the user query contains dynamic parameters (e.g., "set margin to 1.5"):
# - Set `is_parameterized` to true.
# - Populate `required_parameters` with parameter names (e.g., ["top_margin", "bottom_margin"]).
# - Map specific step_id strings from `process_sequence` as keys in `parameter_bindings`.
#   Each key MUST be a step_id string from `process_sequence`, and each value MUST be a ParameterBinding object containing `parameter_name` and `post_keys`.
#   Example structure for parameter_bindings:
#   {
#     "msword_step_003": {
#       "parameter_name": "top_margin",
#       "post_keys": ["TAB"]
#     },
#     "msword_step_004": {
#       "parameter_name": "bottom_margin",
#       "post_keys": ["ENTER"]
#     }
#   }

# Condition B: If NO parameters are passed (e.g., "add page break", "bold text"):
# - Set `is_parameterized` to false.
# - Keep `required_parameters` as an empty list `[]`.
# - Keep `parameter_bindings` as an empty object `{}`.
# """


SYSTEM_PROMPT = """
You are an expert Microsoft Word RPA Process Planner.

Your responsibility is to generate an executable automation process from a user's natural language request.

You will receive two inputs:

1. USER QUERY
   A natural language instruction describing the task to perform in Microsoft Word.

2. RETRIEVED ATOMIC STEP JSONS
   A collection of candidate atomic UI automation steps retrieved from the RAG knowledge base.
   Each step contains metadata such as:
   - step_id
   - step_name
   - step_description
   - action_type
   - target_control
   - parameters (if any)
   

Your job is to analyze the user request and construct an executable process using ONLY the retrieved atomic steps.

===========================================================
REASONING PROCESS
===========================================================

Follow these steps in order.

STEP 1 — Understand the User Intent

Determine exactly what operation the user wants to perform.

Examples:

• "Bold the selected text"
      → Bold Text

• "Insert page break"
      → Insert Page Break

• "Change font size to 12"
      → Change Font Size

• "Set all margins to 1 inch"
      → Custom Margins

• "Insert picture from C:\\Images\\cat.png"
      → Insert Picture

• "Insert a table with 5 rows and 4 columns"
      → Insert Table

Do not combine multiple operations into one process unless explicitly requested.

===========================================================

STEP 2 — Identify Required Atomic Steps

Review every retrieved atomic step.

Determine whether the step contributes directly to accomplishing the user's request.

Include a step ONLY if:

• it is required to complete the requested operation

Exclude a step if:

• it belongs to another feature
• it is unrelated
• it performs unnecessary navigation

Never invent a step.

Never modify a step_id.

Only use retrieved steps.

===========================================================

STEP 3 — Build the Execution Sequence

Create process_sequence.

Rules:

• Include ONLY selected step_ids.

• Preserve the original order of execution.

• Never reorder the retrieved workflow.

• Never skip mandatory intermediate steps.

Example

Retrieved

step001
step002
step003
step004

If all are required

process_sequence

[
step001,
step002,
step003,
step004
]

If only first two are required

[
step001,
step002
]

===========================================================

STEP 4 — Calculate Total Steps

total_steps

must always equal

len(process_sequence)

===========================================================

STEP 5 — Detect Runtime Parameters

Determine whether the user supplied values that must be entered during execution.

Examples

Query

"Bold selected text"

Runtime Parameters

None

------------------------------------------------

Query

"Insert page break"

Runtime Parameters

None

------------------------------------------------

Query

"Set font size to 12"

Runtime Parameters

font_size = 12

------------------------------------------------

Query

"Set custom margins to 1"

Runtime Parameters

top_margin = 1
bottom_margin = 1
left_margin = 1
right_margin = 1

------------------------------------------------

Query

"Insert picture from C:\\Images\\cat.png"

Runtime Parameters

image_path

------------------------------------------------

Query

"Insert table with 5 rows and 4 columns"

Runtime Parameters

rows = 5
columns = 4

===========================================================

STEP 6 — Parameterized Process

If runtime parameters exist:

Set

is_parameterized = true

Populate

required_parameters

using ONLY parameter names found in the retrieved step JSONs.

Populate

parameter_bindings

using ONLY bindings found in the retrieved step JSONs.

Each key inside parameter_bindings MUST be a valid step_id present inside process_sequence.

Each value MUST contain

{
    "parameter_name": "...",
    "post_keys": [...]
}

Never invent parameter names.

Never invent parameter bindings.

Never create bindings for steps that are not in process_sequence.

===========================================================

STEP 7 — Non-Parameterized Process

If no runtime values are required:

Return

"is_parameterized": false

required_parameters = []

parameter_bindings = {}

===========================================================

STEP 8 — Metadata Generation

Generate

process_name

process_id

user_intent

description

Copy

app_name

from the selected steps.

recorded_at

Generate using

YYYYMMDD_HHMMSS

screen_dimensions

{
    "width_px": 1920,
    "height_px": 1200
}

===========================================================

FAILURE CASE

If none of the retrieved atomic steps can satisfy the request:

Return

total_steps = 0

process_sequence = []

required_parameters = []

parameter_bindings = {}

description

"The required automation steps were not found."

===========================================================

STRICT RULES

✓ Use ONLY retrieved atomic steps.

✓ Never invent UI actions.

✓ Never invent step_ids.

✓ Never modify step_ids.

✓ Never reorder mandatory steps.

✓ total_steps MUST equal the number of selected step_ids.

✓ Every step_id inside parameter_bindings MUST exist inside process_sequence.

✓ Return exactly ONE valid ProcessSchema object.

✓ Return JSON only.

Do NOT explain your reasoning.

Do NOT return markdown.

Do NOT return code blocks.

Do NOT return any text outside the JSON object.
"""

def generate_process_sequence(user_query: str, retrieved_atomic_steps: list) -> ProcessOutput:
    
    structured_llm = llm.with_structured_output(ProcessOutput)
    messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {
        "role": "user",
        "content": f"User Query: {user_query}\n\nRetrieved Atomic Steps:\n{retrieved_atomic_steps}"
    }
    ]

# 4. Invoke the structured LLM directly
    response = structured_llm.invoke(messages)

    # 'response' is already an instance of your Pydantic model (ParameterizedProcess or NonParameterizedProcess)
    return response

def build_context(user_query):

    docs = retriever.invoke(user_query)

    step_jsons = []

    for doc in docs:
        step_jsons.append(json.loads(doc.page_content))

    return step_jsons


def save_to_json(data: ProcessOutput, filepath: Optional[str] = None) -> str:
    """
    Saves a Pydantic ProcessOutput object to a formatted JSON file.
    If no filepath is provided, uses the data's process_id as the filename.
    """
    # If no custom filepath provided, name file after process_id
    if not filepath:
        filepath = f"{data.process_id}.json"

    # Convert Pydantic object directly to JSON string with pretty printing
    json_data = data.model_dump_json(indent=4)

    # Write to file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(json_data)

    print(f"[SUCCESS] Successfully saved output to '{filepath}'")
    return filepath
if __name__ == "__main__":
    query = "set the custom margin to 1.5"
    sample_retrieved_steps = build_context(query)
    output = generate_process_sequence(query, sample_retrieved_steps)
    save_to_json(output,'llm_output.json')
    