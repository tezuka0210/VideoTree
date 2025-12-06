import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from .state import AgentState

# --- 1. 定义两套完全独立的 System Prompt ---

# A. 视觉模式提示词 (用于生图/生视频)
VISUAL_SYSTEM_PROMPT = """
You are an expert Stable Diffusion/FLUX Prompt Engineer for ComfyUI.
Your goal is to generate a list of weighted tags for visual generation based on the inputs.

Context Inputs:
- Global Context (Base): {global_context}
- Local Instruction (Edit): {user_input}
- Visual Style: {style}
- Entity Knowledge: {knowledge}

Instructions:
1. **Context Fusion:** Merge User Input > Global Context > Knowledge.
2. **Weighting Logic:**
   - High (1.3-1.6) for User Input keywords.
   - Standard (1.0-1.2) for Global Context/Knowledge.
   - Format: `(keyword:weight)`.
3. **Formatting Rules:**
   - **Positive:** Comma-separated phrases (≤5 words each). Focus on lighting, texture, composition.
   - **Negative:** Standard quality artifacts (e.g., "bad anatomy, blurry").
   - Output ONLY valid JSON.

**Example Output:**
{{
    "positive": "(hold teacup:1.5), (Song Dynasty scholar:1.2), (celadon teacup:1.1), (warm glaze:1.0), (soft natural light:1.0)",
    "negative": "(bad anatomy:1.2), (blurry:1.3), (worst quality:1.4)"
}}
"""

# B. 音频模式提示词 (用于生旁白/TTS)
AUDIO_SYSTEM_PROMPT = """
You are an expert Scriptwriter for AI Text-to-Speech (TTS) narration.
Your goal is to write a fluent, engaging speech script based on the inputs.

Context Inputs:
- Narrative Context: {global_context}
- Specific Request: {user_input} (May contain duration info, e.g., "5 seconds")
- Tone/Style: {style}
- Detailed Info: {knowledge}

Instructions:
1. **Goal:** Write a natural narrative sentence or paragraph that describes the scene or tells the story.
2. **Duration Control (CRITICAL):**
   - Analyze '{user_input}' for duration constraints.
   - Estimate length: Approx. 2.5 words per second.
   - If user asks for 5 seconds, write about 10-15 words.
3. **Formatting Rules:**
   - **text:** Full, grammatically correct English sentences.
   - **NO weighting syntax** (e.g., NO `(word:1.2)`).
   - **NO lists of keywords**. Write like a novelist or documentary narrator.
   - Output ONLY valid JSON.

**Example Output:**
{{
    "text": "Under the vast starry sky, the ancient stone ruins whisper secrets of the past to the cool night breeze."
}}
"""

def prompt_agent_node(state: AgentState):
    print("--- Running Prompt Agent ---")

    # 1. Gather all context
    user_input = state.get("user_input", "")
    intent = state.get("intent", "")
    style = state.get("style", "")
    image_caption = state.get("image_caption", "")
    knowledge = state.get("knowledge_context", "")
    selected_workflow = state.get("selected_workflow", "")
    global_context = state.get("global_context","")
    print("global_context_prompt",global_context)

    # 2. Initialize LLM
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.7,
        model_kwargs={"response_format": {"type": "json_object"}}
    )

    # 3. 【核心修改】在 Python 层进行逻辑分发
    # 根据 workflow 文件名选择不同的 System Prompt
    if "Audio" in selected_workflow or "TextToAudio" in selected_workflow:
        print("  - Mode: AUDIO Scripting")
        system_prompt = AUDIO_SYSTEM_PROMPT
    else:
        print("  - Mode: VISUAL Prompting")
        system_prompt = VISUAL_SYSTEM_PROMPT

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "User Request: {user_input}")
    ])

    # 4. Execute
    chain = prompt | llm

    result = chain.invoke({
        "style": style,
        "knowledge": knowledge,
        # image_caption 在音频模式下可能不重要，但在视觉模式下有用
        # 你可以根据需要决定是否传入，或者在 Prompt 里统一留个占位符
        "global_context": global_context,
        "user_input": user_input
    })

    # 5. Parse and Return
    try:
        final_prompts = json.loads(result.content)
    except json.JSONDecodeError:
        print("Error: JSON Decode Failed")
        final_prompts = {"error": "failed"}

    print(f"AGENCY: Prompt Agent Generated: {final_prompts}")

    return {"final_prompt": final_prompts}