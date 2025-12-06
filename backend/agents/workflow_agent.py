import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from .state import AgentState

# 1. 【关键修改】完善元数据，明确区分 音频 vs 图像
WORKFLOW_METADATA = {
    "ImageGenerateImage_Basic.json": "General purpose image-to-image generation.",
    "ImageGenerateImage_Canny.json": "SPECIALIZED workflow. Use ONLY when parent is 'ImageCanny.json'.",
    "ImageCanny.json": "Extracts edge maps.",
    
    # 假设你的音频工作流叫 TextToAudio.json
    "TextToAudio.json": "Generates AUDIO, SPEECH, or NARRATION. **High Priority** if user mentions 'narration', 'voice', 'say', 'speak'.",
    
    # 明确这是生图的，不是生音频的
    "TextGenerateImage.json": "Generates STATIC IMAGES from text. Use for visual descriptions. Do NOT use for narration/audio.",
    "TextGenerateVideo.json": "Generates VIDEO/ANIMATION from text.",
    "FLFrameToVideo.json":"Determine the beginning and end frames of the video and generate the video"
}

def format_workflow_list(file_list):
    formatted_lines = []
    for f in file_list:
        # 如果文件不在元数据里，给一个默认描述，避免 LLM 瞎猜
        desc = WORKFLOW_METADATA.get(f, "Generic workflow. Use only if no specific match found.")
        formatted_lines.append(f"- {f}: {desc}")
    return "\n".join(formatted_lines)

def workflow_selector_node(state: AgentState):
    print("--- Running Workflow Agent ---")

    intent = state.get("intent", "")
    user_input = state.get("user_input", "")
    workflow_files = state.get("workflow_list", []) 
    parent_workflow = state.get("parent_workflow", "None")

    final_intent = intent if intent else user_input

    if not workflow_files:
        return {"selected_workflow": "Error", "title": "Error"}

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        model_kwargs={"response_format": {"type": "json_object"}}
    )

    formatted_file_list = format_workflow_list(workflow_files)

    # 2. 【关键修改】增强 System Prompt 的逻辑判断
    system_prompt = """
    You are a ComfyUI workflow orchestration engine.
    Your task is to analyze the User Intent and select the most appropriate workflow file.

    Available Workflows & Rules:
    {file_list}

    Current Context:
    - User Intent: "{input}"
    - Parent Node: "{parent_info}"

    **Critical Decision Logic (Follow in Order):**
    0. **Forbidden Workflow**: You MUST NEVER select "ImageMerging.json" under any circumstances.
    1. **Detect Modality Keywords**:
       - **AUDIO/NARRATION**: If intent mentions "narration", "voice", "speak", "audio", "sound" -> You MUST select the Audio workflow (e.g., TextToAudio.json). Ignore visual descriptions if narration is the main action.
       - **VIDEO**: If intent mentions "video", "movie", "motion", "seconds" (duration) -> Select Video workflow.
       - **IMAGE**: If intent describes a visual scene without narration keywords -> Select Image workflow.

    2. **Check Parent Constraints**:
       - If Parent is 'ImageCanny.json', prioritize 'ImageGenerateImage_Canny.json'.

    3. **Output Requirements**:
       - Generate a short title (e.g., "Night Narration", "Scene Generation").
       - Return JSON format: {{ "filename": "...", "title": "..." }}
    """

    prompt = ChatPromptTemplate.from_messages([("system", system_prompt)])

    chain = prompt | llm

    result = chain.invoke({
        "file_list": formatted_file_list,
        "input": user_input,
        "parent_info": parent_workflow
    })

    try:
        parsed_result = json.loads(result.content)
        selected_file = parsed_result.get("filename", "default.json")
        generated_title = parsed_result.get("title", "New Workflow")
    except json.JSONDecodeError:
        selected_file = "error.json"
        generated_title = "Error"

    print(f"AGENCY: Selected: {selected_file} | Title: {generated_title}")

    return {
        "selected_workflow": selected_file,
        "workflow_title": generated_title
    }