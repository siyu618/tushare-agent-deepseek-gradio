import asyncio
import operator
from typing import List, TypedDict, Annotated
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END


from dotenv import load_dotenv
import os
load_dotenv()
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

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
llm = ChatOpenAI(model='deepseek-chat', openai_api_key=DEEPSEEK_API_KEY, openai_api_base='https://api.deepseek.com')

@tool
async def get_market_data(pair: str):
    """查询交易对行情数据（如 BTC_USDT）。"""
    await asyncio.sleep(0.5)  # 模拟网络延迟
    data = {"BTC_USDT": "96500", "GT_USDT": "9.5"}
    price = data.get(pair.upper(), "Unknown")
    return f"{pair}: {price} USDT"

# --- 3. 节点逻辑 ---

async def planner(state: PlanExecuteState):
    """计划者：负责任务拆解"""
    # 核心修复点：强制使用 function_calling 模式
    planner_llm = llm.with_structured_output(Plan, method="function_calling")

    prompt = f"""你是一个任务规划专家。
    针对用户需求：{state['input']}
    请拆解执行计划。
    
    规则：
    1. 如果多个查询任务（如查询不同币种价格）互不依赖，请将它们放在同一个子列表中，以便系统【并行】执行。
    2. 结果必须符合 Plan 结构。
    
    示例：
    用户说“查 BTC 和 GT”，你的计划应该是：[['BTC_USDT', 'GT_USDT']]
    """

    response = await planner_llm.ainvoke(prompt)
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
    """再计划者：汇总或决定是否继续"""
    if not state["plan"]:
        # 如果计划跑完了，进行最终总结
        prompt = f"基于以下执行历史，给出最终回答：{state['past_steps']}"
        response = await llm.ainvoke(prompt)
        return {"response": response.content}
    return {} # 继续循环

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

if __name__ == "__main__":
    asyncio.run(main())