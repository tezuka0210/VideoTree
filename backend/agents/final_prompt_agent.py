import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from .state import AgentState

def final_prompt_agent_node(state: AgentState):
    print("--- Running Prompt Agent (Updated for Sentence Prompts) ---")

    # 1. 从状态中获取上下文（修复：变量名与模板引用一致，补充缺失变量）
    user_input = state.get("user_positive_input", "")  # 原逻辑：用户输入从 user_positive_input 获取
    intent = state.get("intent", "")
    style = state.get("style", "")  # 模板需要，补充获取（默认空字符串）
    #image_caption = state.get("image_caption", "")
    knowledge = state.get("knowledge_context", "")
    selected_workflow = state.get("selected_workflow", "")
    global_context = state.get("global_context", "")  # 模板需要，补充获取（默认空字符串）

    # 2. 初始化 LLM（保持原有配置）
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.4,
        model_kwargs={"response_format": {"type": "json_object"}}
    )

    # 3. 提示词模板（保持原有逻辑，仅确保变量引用一致）
    system_prompt = """
    You are an expert ComfyUI Prompt Engineer.
    Your goal is to construct a descriptive English sentence that strictly follows specific logic based on input weights.

    ### INPUT DATA
    - User Input: {user_input}
    - Global Context: {global_context}
    - Style: {style}
    - Knowledge: {knowledge}

    ### CORE LOGIC: THE "WEIGHT THRESHOLD" RULE (CRITICAL)
    You must parse every `(keyword:weight)` in the User Input and handle it differently based on the number:

    **CASE A: High Weight (>= 1.0)** -> **LOCKED MODE**
    - Logic: The user is certain.
    - Action: You MUST keep the string `(keyword:weight)` EXACTLY as is.
    - Rule: Do not change the word. Do not remove the brackets. Embed it verbatim into the sentence.
    
    **CASE B: Low Weight (< 1.0)** -> **DYNAMIC EXPANSION MODE**
    - Logic: The user is uncertain or wants variation.
    - Action: You MUST convert this into ComfyUI dynamic syntax `{{opt1|opt2|opt3}}`.
    - Rule:
      - If weight is close to 0 (0.1-0.3): Generate 3 DISTINCTLY DIFFERENT options (e.g., different colors/types).
      - If weight is close to 1 (0.8-0.9): Generate 3 SIMILAR/RELATED options.
    - **Outcome:** The original `(key:0.x)` is REMOVED and replaced by `{{opt1|opt2|opt3}}`.

    ### OUTPUT FORMAT
    - Return ONLY a raw JSON string. Do not wrap in markdown ```json ... ```.
    - Structure:
    {{
      "positive": "Full sentence...",
      "negative": "Full sentence..."
    }}

    ### FEW-SHOT EXAMPLES (Study the Logic)

    **Example 1 (High Weights)**
    Input: "(red sports car:1.5), (highway:1.2)"
    Output:
    {{
      "positive": "A sleek (red sports car:1.5) speeds down the wide (highway:1.2) under the bright sun.",
      "negative": "bad quality, blurry"
    }}

    **Example 2 (Low Weights - Expansion)**
    Input: "(weather:0.2), (structure:1.5)"
    Explanation: 'weather' is 0.2 (Low), so it becomes distinct options. 'structure' is 1.5 (High), so it stays.
    Output:
    {{
      "positive": "Under the {{stormy sky|bright sunny sky|starry night}}, a massive (structure:1.5) stands tall.",
      "negative": "bad quality"
    }}

    **Example 3 (Mixed)**
    Input: "(blue eyes:1.4), (hair color:0.8)"
    Explanation: 'blue eyes' is High -> Keep. 'hair color' is 0.8 (High-ish but <1) -> Similar options.
    Output:
    {{
      "positive": "The portrait features a woman with piercing (blue eyes:1.4) and flowing {{blonde hair|light brown hair|golden hair}}.",
      "negative": "bad anatomy"
    }}
    """
    # 4. 创建 Prompt 模板 + 定义 chain（修复：确保模板变量与传递参数一致）
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        # 修复：模板中的 {input} 改为 {user_input}（与传递的变量名一致，避免额外未定义变量）
        ("user", "User Request: {user_input} | Intent: {intent}")
    ])
    chain = prompt | llm

    # 5. 执行 LLM 调用（核心修复：补充缺失的 3 个变量，确保与模板引用完全一致）
    result = chain.invoke({
        #"image_caption": image_caption,
        "user_input": user_input,  # 对应模板中的 {user_input}（包括 system 和 user 消息）
        "intent": intent,
        "knowledge": knowledge,
        "style": style,  # 补充：模板中引用了 {style}
        "global_context": global_context,  # 补充：模板中引用了 {global_context}
    })

    # 6. 解析结果（保持原有异常处理逻辑）
    try:
        final_prompts = json.loads(result.content)
        # 验证输出格式是否符合要求（增强鲁棒性）
        if not isinstance(final_prompts.get("positive"), str) or not isinstance(final_prompts.get("negative"), str):
            raise ValueError("Prompt values must be strings")
    except (json.JSONDecodeError, ValueError):
        # 回退到默认值
        final_prompts = {
            "positive": user_input,
            "negative": "bad quality, low res"
        }

    print("AGENCY: Prompt Agent Generated Sentence-Based Prompts.")
    return {"final_prompt": final_prompts}

# ==========================
# 测试代码（修复变量名和缺失参数）
# ==========================
if __name__ == "__main__":
    # 1. 准备测试用的 AgentState（补充缺失的默认变量，避免获取为空时模板报错）
    test_state = AgentState({
        "user_positive_input": "(sandy beach:1.5), (running puppy:1.6), (bright sun:0.2), (soft fur:1.3), (joyful motion:1.7)",
        "image_caption": "",
        "intent": "generate a vivid beach scene with a playful puppy",
        "style": "",  # 补充：测试时默认空（可根据需要设置具体风格，如 "photorealistic"）
        "global_context": "",  # 补充：测试时默认空（可根据需要设置全局上下文）
        "knowledge_context": ""  # 补充：对应代码中的 knowledge 来源
    })

    # 2. 运行 Agent（修复：函数名拼写错误，原 prompt_agent_node → 正确 final_prompt_agent_node）
    result = final_prompt_agent_node(test_state)

    # 3. 打印结果
    print("\n" + "="*50)
    print("Test Result:")
    print("="*50)
    print(f"Final Prompt:\n{json.dumps(result['final_prompt'], indent=2, ensure_ascii=False)}")

    # 4. 验证结果格式
    positive = result["final_prompt"]["positive"]
    negative = result["final_prompt"]["negative"]
    print("\n" + "-"*30)
    print("Validation:")
    print(f"- Positive Prompt is a sentence: {len(positive.strip().split('.')) >= 1 and positive.strip().endswith('.')}")
    print(f"- Positive contains weights: {'(' in positive and ':' in positive and ')' in positive}")
    print(f"- Positive contains random options: '{{' in positive and '}}' in positive")
    print(f"- Negative Prompt is a sentence: {len(negative.strip().split('.')) >= 1 and negative.strip().endswith('.')}")