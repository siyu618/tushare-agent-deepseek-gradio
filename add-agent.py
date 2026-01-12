import asyncio
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph

builder = StateGraph(int)
builder.add_node("add_one", lambda x: x + 1)
builder.add_node("double", lambda x: x * 2)
builder.set_entry_point("add_one")
builder.set_finish_point("double")

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)
thread_id = "session-1"

async def run():
    # 执行图
    result = await graph.ainvoke(15, {"configurable": {"thread_id": thread_id}})
    print("Result:", result)

    config = {"configurable": {"thread_id": thread_id}}
    ckpts = checkpointer.list(config)

    # ✅ 实际用途示例
    for ckpt in ckpts:
        checkpoint = getattr(ckpt, "checkpoint", ckpt)
        state = getattr(checkpoint, "channel_values", checkpoint)

        # 1️⃣ 条件分支：根据之前节点值决定下一步
        if "add_one" in state and state["add_one"] > 10:
            print("State indicates add_one > 10, call special tool")
        else:
            print("Normal execution path")

        # 2️⃣ 调试 / 可视化
        print("Current checkpoint state:", state)

asyncio.run(run())
