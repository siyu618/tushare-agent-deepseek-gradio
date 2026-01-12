import asyncio
import operator
from typing import List, TypedDict, Annotated
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
# from langchain_core.messages import HumanMessage
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langchain.callbacks.base import AsyncCallbackHandler

class UsageCallback(AsyncCallbackHandler):
    async def on_llm_end(self, response, **kwargs):
        usage = response.llm_output.get("token_usage", {})
        print("[callback]", usage)

from dotenv import load_dotenv
import os
load_dotenv()
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")


def log_llm_usage(tag: str, response):
    metadata = getattr(response, "response_metadata", {}) or {}
    usage = metadata.get("token_usage", {}) or {}

    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    total_tokens = usage.get("total_tokens")
    cache_hit = usage.get("prompt_cache_hit_tokens")

    print(
        f"[{tag}] "
        f"prompt={prompt_tokens}, "
        f"completion={completion_tokens}, "
        f"total={total_tokens}, "
        f"cache_hit={cache_hit}"
    )


# --- 1. 定义状态和数据结构 ---

class Plan(BaseModel):
    """计划的任务列表，每个步骤可以包含多个可并行的任务"""
    steps: List[List[str]] = Field(description="有序的步骤列表。每个内部列表包含可以并行执行的任务（如查询不同币种）。")

class PlanExecuteState(TypedDict):
    input: str
    plan: List[List[str]]
    past_steps: Annotated[List[str], operator.add]
    response: str

# --- 2. 配置模型与工具 ---
llm = ChatOpenAI(model='deepseek-chat',
                 openai_api_key=DEEPSEEK_API_KEY,
                 openai_api_base='https://api.deepseek.com',
                 callbacks=[UsageCallback()],)

@tool
async def get_market_data(pair: str):
    """查询交易对行情数据（如 BTC_USDT）。"""
    await asyncio.sleep(0.5)  # 模拟网络延迟
    data = {"BTC_USDT": "96500", "GT_USDT": "9.5"}
    price = data.get(pair.upper(), "Unknown")
    return f"{pair}: {price} USDT"

# --- 3. 节点逻辑 ---
# --- 定义静态的 System Prompt ---
PLANNER_SYSTEM_PROMPT = """你是一个专业的金融任务规划专家。
你的职责是根据用户需求拆解执行计划。

规则（请严格遵守以触发缓存）：
1. 识别所有需要查询的资产（如 BTC_USDT, GT_USDT）。
2. 将互不依赖的任务放在同一个子列表中进行【并行执行】。
3. 即使只有一个任务，也请嵌套在两层列表内，例如：[['BTC_USDT']]。
4. 仅输出计划，不要有任何多余的解释。
"""

REPLANNER_SYSTEM_PROMPT = """你是一个任务总结专家。
请根据提供的执行历史，为用户提供简洁、准确的最终回复。
如果信息不全，请指出缺失的部分。
"""
async def planner(state: PlanExecuteState):
    """计划者：利用前缀匹配触发 DeepSeek 缓存"""
    planner_llm = llm.with_structured_output(Plan, method="function_calling")

    # 构造消息：SystemMessage 在前（静态），HumanMessage 在后（动态）
    messages = [
        SystemMessage(content=PLANNER_SYSTEM_PROMPT),
        HumanMessage(content=f"用户需求：{state['input']}")
    ]

    response = await planner_llm.ainvoke(messages)
    # ⭐ 关键：打印 prompt cache
    # log_llm_usage("planner", response)
    return {"plan": response.steps}

async def executor(state: PlanExecuteState):
    """执行者：负责并行处理当前步骤中的所有任务"""
    current_step_tasks = state["plan"][0]

    # 核心并行逻辑：使用 asyncio.gather 同时执行当前步骤的所有工具调用
    tasks = [get_market_data.ainvoke({"pair": task}) for task in current_step_tasks]
    results = await asyncio.gather(*tasks)

    step_output = f"执行步骤 {current_step_tasks} 的结果: {results}"
    return {"past_steps": [step_output], "plan": state["plan"][1:]}

async def replanner(state: PlanExecuteState):
    """再计划者：同样遵循静态在前原则"""
    if not state["plan"]:
        messages = [
            SystemMessage(content=REPLANNER_SYSTEM_PROMPT),
            HumanMessage(content=f"执行历史：{state['past_steps']}\n原始需求：{state['input']}")
        ]
        response = await llm.ainvoke(messages)
        # ⭐ cache 打印
        # log_llm_usage("replanner", response)
        return {"response": response.content}
    return {}

# --- 4. 构建图 ---

workflow = StateGraph(PlanExecuteState)
workflow.add_node("planner", planner)
workflow.add_node("executor", executor)
workflow.add_node("re_planner", replanner)

workflow.set_entry_point("planner")
workflow.add_edge("planner", "executor")
workflow.add_edge("executor", "re_planner")

def should_continue(state: PlanExecuteState):
    if state.get("response"): return END
    return "executor"

workflow.add_conditional_edges("re_planner", should_continue)

app = workflow.compile()

# --- 5. 测试运行 ---
async def main():
    config = {"recursion_limit": 20,
              "run_name": "BTC_GT_Parallel_Test_001" # 在 LangSmith 中显示的名称
              }
    inputs = {"input": "帮我查一下 BTC_USDT 和 GT_USDT 的价格", "past_steps": []}
    async for event in app.astream(inputs, config):
        print(event)
        for node_name, output in event.items():
            # 尝试从消息中获取 usage 统计
            if "messages" in output and output["messages"]:
                last_msg = output["messages"][-1]
                if hasattr(last_msg, 'response_metadata'):
                    usage = last_msg.response_metadata.get("token_usage", {})
                    # 关键字段：prompt_cache_hit_tokens
                    cached_tokens = usage.get("prompt_cache_hit_tokens", 0)
                    total_tokens = usage.get("total_tokens", 0)
                    print(f"[{node_name}] 缓存命中: {cached_tokens} / 提示词总数: {usage.get('prompt_tokens')}")

if __name__ == "__main__":
    asyncio.run(main())