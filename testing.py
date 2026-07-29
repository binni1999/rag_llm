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

    parameter_bindings: Dict[str, str] = Field(
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
You are an expert RPA Process Planner responsible for creating executable automation workflows.

You are given:

1. A user's automation request.
2. A collection of retrieved step JSONs from a vector database.

Your task is to determine which steps are actually required to accomplish the user's request.

-------------------------
USER REQUEST
-------------------------

{user_query}

-------------------------
RETRIEVED STEP JSONS
-------------------------

{steps}

-------------------------
INSTRUCTIONS
-------------------------

1. Carefully analyze the user's request.

2. Review every retrieved step.

3. Select ONLY the steps that directly contribute to completing the requested task.

4. Ignore unrelated or unnecessary steps, even if they appear in the retrieved context.

5. Preserve the original execution order of the selected steps.

6. Do NOT invent new steps.

7. Do NOT modify existing step_ids.

8. If multiple retrieved steps perform the same action, choose the most appropriate one.

9. If the retrieved context does not contain enough information to complete the task, return an empty process with:
   - total_steps = 0
   - process_sequence = []
   - description explaining that the required steps were not found.

10. Infer the following fields from the selected steps:
    - process_name
    - process_id
    - user_intent
    - description
    - total_steps
    - process_sequence

11. Copy app_name from the selected steps.

12. Set is_parameterized to true only if execution requires runtime input.

13. Populate required_parameters and parameter_bindings only when applicable.

14. Return ONLY a valid object that matches the ProcessSchema.

Do not return explanations, markdown, or any additional text.
"""

#     prompt = f"""
# You are an expert RPA Process Generator.

# Below are the retrieved individual automation steps.

# {json.dumps(steps, indent=4)}

# Your task:

# Generate ONE process.

# Rules

# 1. Infer process_name.

# 2. Infer process_id.

# 3. Infer user_intent.

# 4. Infer description.

# 5. total_steps = number of steps.

# 6. process_sequence must contain all step_ids.

# 7. Copy app_name.

# 8. Screen size is 1920x1200.

# 9. If parameters are required, populate them.

# 10. Return ONLY the structured object.
# """

    response = llm_structured.invoke(prompt)

    return response



if __name__ == "__main__":

    query = input("Enter User Query : ")

    process = generate_process_json(query)

    print(process)