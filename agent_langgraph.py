# agent_langgraph.py
from langchain.agents import Tool, AgentExecutor, create_openai_functions_agent
from langchain.chat_models import ChatOpenAI
from tushare_tools import get_stock_data, get_stock_match_days, get_all_live_stocks

# 1️⃣ 定义工具（Tools）
tools = [
    Tool(
        name="GetStockData",
        func=lambda ts_code, start_date, end_date: get_stock_data(ts_code, start_date, end_date).to_dict(orient="records"),
        description="Get historical stock data for a given stock code between start_date and end_date. Arguments: ts_code, start_date, end_date"
    ),
    Tool(
        name="GetStockMatchDays",
        func=lambda start_date, end_date: get_stock_match_days(start_date=start_date, end_date=end_date),
        description="Get stocks with strong uptrend based on predefined strategy. Arguments: start_date, end_date"
    ),
    Tool(
        name="GetAllLiveStocks",
        func=lambda: [s.__dict__ for s in get_all_live_stocks()],
        description="List all currently listed stocks. No arguments required."
    )
]

# 2️⃣ 初始化 LLM
llm = ChatOpenAI(
    model_name="gpt-4",
    temperature=0
)

# 3️⃣ 创建 LangGraph Agent
agent = create_openai_functions_agent(
    llm=llm,
    tools=tools,
    verbose=True
)

# 4️⃣ 封装执行方法
class TushareLangGraphAgent:
    def __init__(self, agent):
        self.agent = agent

    def handle_query(self, query: str):
        """
        使用 LangGraph Agent 处理用户输入
        """
        try:
            result = self.agent.run(query)
            return {"query": query, "result": result}
        except Exception as e:
            return {"query": query, "error": str(e)}

# 5️⃣ 简单测试
if __name__ == "__main__":
    tg_agent = TushareLangGraphAgent(agent)
    query = "List all live stocks"
    print(tg_agent.handle_query(query))

    query2 = "Get stock data for 600519.SH from 2025-09-01 to 2025-09-10"
    print(tg_agent.handle_query(query2))

