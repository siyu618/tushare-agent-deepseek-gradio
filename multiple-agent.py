import asyncio
import operator
import os
from typing import Annotated, List, TypedDict

# 使用 OpenAI 兼容库即可，DeepSeek 官方推荐
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END

from dotenv import load_dotenv
load_dotenv()

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
# --- 1. 定义状态 (State) ---
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    error_count: int

# --- 2. 配置 DeepSeek 模型 ---
# 注意：DeepSeek API 基础 URL 为 https://api.deepseek.com
llm = ChatOpenAI(
    model='deepseek-chat',  # 或者使用 'deepseek-reasoner' (R1)
    openai_api_key=DEEPSEEK_API_KEY,
    openai_api_base='https://api.deepseek.com', # 指向 DeepSeek 端点
    max_tokens=4096,
    temperature=0.7 # 金融场景通常建议较低的 temperature 以保证确定性
)

# --- 3. 定义异步工具 ---
@tool
async def get_market_data(pair: str):
    """查询 Gate.io 上的交易对行情数据（如 BTC_USDT）。"""
    await asyncio.sleep(0.3) # 模拟网络延迟
    # 模拟返回
    market_data = {"BTC_USDT": "96500", "ETH_USDT": "2700", "GT_USDT": "9.5"}
    price = market_data.get(pair.upper(), "Price not found")
    return f"The current price of {pair} is {price} USDT."

tools = [get_market_data]
# 将工具绑定到 DeepSeek 模型
model_with_tools = llm.bind_tools(tools)

# --- 4. 节点逻辑 (保持异步，支持千万级流量调度) ---

# async def call_deepseek(state: AgentState):
#     """调度 DeepSeek 模型进行决策"""
#     response = await model_with_tools.ainvoke(state["messages"])
#     print("call_deepseek", response)
#     return {"messages": [response]}
async def call_deepseek(state: AgentState):
    """调度 DeepSeek 模型进行决策，并强制引导其并行思考"""

    # 引导模型一次性识别所有需求，不要分步执行
    prompt_guidance = (
        "你是一个极其高效的金融分析助手。"
        "当用户要求查询多个信息（如多个交易对的价格）时，请务必在【单次回复】中"
        "生成【所有的工具调用指令】，以便系统能够并行处理。"
        "不要一个一个地查，效率对我们非常重要。"
    )

    # 构造带引导的消息序列
    messages = [
                   {"role": "system", "content": prompt_guidance}
               ] + state["messages"]

    # 调用模型
    response = await model_with_tools.ainvoke(messages)
    print("call_deepseek", response)

    # 打印一下，看看它这次是不是一口气调用了多个工具
    if response.tool_calls:
        print(f"--- 模型单次决策生成的工具调用数量: {len(response.tool_calls)} ---")
        for call in response.tool_calls:
            print(f"调用工具: {call['name']} 参数: {call['args']}")

    return {"messages": [response]}

async def execute_tools_parallel(state: AgentState):
    """
    高性能并行执行：面试官最看重的工程细节
    """
    last_message = state["messages"][-1]
    tool_calls = last_message.tool_calls

    # 构建并发任务池
    tasks = []
    for call in tool_calls:
        # 通过工具名映射并异步执行
        # 在实际生产中，这里可以接入 MCP 协议驱动的远程工具服务器
        tasks.append(get_market_data.ainvoke(call["args"]))
    print("execute_tools_parallel", state, tasks)
    # 并行等待所有结果
    results = await asyncio.gather(*tasks, return_exceptions=True)

    tool_messages = []
    for i, result in enumerate(results):
        call_id = tool_calls[i]["id"]
        content = f"Error: {str(result)}" if isinstance(result, Exception) else str(result)
        tool_messages.append(ToolMessage(tool_call_id=call_id, content=content))

    return {"messages": tool_messages}

# --- 5. 构建状态机图 ---

workflow = StateGraph(AgentState)
workflow.add_node("agent", call_deepseek)
workflow.add_node("tools", execute_tools_parallel)

workflow.set_entry_point("agent")

def router(state: AgentState):
    print("router: ", state)
    if state["messages"][-1].tool_calls:
        return "tools"
    return END

workflow.add_conditional_edges("agent", router)
workflow.add_edge("tools", "agent")

app = workflow.compile()

# --- 6. 运行测试 ---
async def main():
    inputs = {"messages": [HumanMessage(content="帮我查一下 BTC_USDT 和 GT_USDT 的价格，两个都需要")]}
    async for output in app.astream(inputs, config={"recursion_limit": 15}):
        print(output)

if __name__ == "__main__":
    asyncio.run(main())