import json
import os

from typing import List, Dict
from pydantic import BaseModel, Field
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
    search_kwargs={"k":5}
)

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

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

    parameter_bindings: Dict[str, Dict] = Field(
        default_factory=dict,
        description="Mapping between parameter names and their assigned values or placeholders. Example: {'file_path': '{input_file}'}"
    )

    process_sequence: List[str] = Field(
        ...,
        description="Ordered list of step IDs representing the execution sequence of the automation process."
    )





llm_structured = llm.with_structured_output(ProcessSchema)

def build_context(user_query):

    docs = retriever.invoke(user_query)

    step_jsons = []

    for doc in docs:
        step_jsons.append(json.loads(doc.page_content))

    return step_jsons


def generate_process_json(user_query):

    steps = build_context(user_query)

    
    prompt = f"""
 You are an expert Microsoft Word RPA Process Planner.

Your task is to build a ProcessSchema object from the retrieved automation steps.

You MUST determine whether the user's request contains runtime parameters and populate the output accordingly.

==================================================
USER REQUEST
==================================================

{user_query}

==================================================
RETRIEVED STEP JSONS
==================================================

{json.dumps(steps, indent=2)}

==================================================
RULES
==================================================

STEP SELECTION

1. Carefully understand the user's request.

2. Select ONLY the retrieved steps required to complete the task.

3. Ignore unrelated retrieved steps.

4. Preserve the original execution order.

5. Never invent a new step.

6. Never modify any step_id.

7. If multiple step groups perform the same action, choose the most relevant one.

--------------------------------------------------

PROCESS METADATA

Infer

- process_name
- process_id
- user_intent
- description
- total_steps
- process_sequence

Copy

- app_name

Set screen size to 1920 x 1200.

--------------------------------------------------

PARAMETER DETECTION

Determine whether the user has supplied runtime values.

Examples

"Bold text"

→ no runtime values

"Insert page break"

→ no runtime values

"Change page orientation"

→ no runtime values

"Set font size to 10"

→ runtime value = 10

"Set custom margins to 1"

→ runtime value = 1

"Insert picture from C:\\Images\\cat.png"

→ runtime value = image path

--------------------------------------------------

IF THERE ARE NO RUNTIME VALUES

Return

"is_parameterized": false

"required_parameters": []

"parameter_bindings": {{}}

--------------------------------------------------

IF THERE ARE RUNTIME VALUES

Return

"is_parameterized": true

Populate

required_parameters

using the parameter names from the retrieved step JSON.

Populate

parameter_bindings

using the parameter mapping present inside the retrieved steps.

DO NOT invent parameter names.

DO NOT invent bindings.

Only use the bindings that already exist inside the retrieved JSON.

--------------------------------------------------

FAILURE

If no suitable retrieved steps exist

Return

total_steps = 0

process_sequence = []

description = "Required automation steps were not found."

==================================================

OUTPUT

Return ONLY a valid ProcessSchema object.

Do NOT return markdown.

Do NOT explain anything.

Do NOT output code blocks.
"""

    response = llm_structured.invoke(prompt)

    return response



if __name__ == "__main__":

    query = input("Enter User Query : ")

    intent = intent_llm.invoke(
        prompt=f"""
        Extract the automation intent and runtime parameters.

        User:
        {query}
        """
    )

    process = generate_process_json(query)

    print(process)