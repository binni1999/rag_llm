

    
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
