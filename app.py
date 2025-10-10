from dotenv import load_dotenv
import os
# 加载环境变量
from dotenv import load_dotenv
load_dotenv()
import gradio as gr
from agent import TushareAgent



# 创建 TushareAgent 实例
agent = TushareAgent()

def run_agent(query):
    try:
        # 调用 Agent 执行查询
        res = agent.handle_query(query)
        # 返回 reasoning 和 result
        return res["reasoning"], res["result"]

    except Exception as e:
        # 捕获所有异常并在 Gradio 页面显示错误信息
        return f"An error occurred: {str(e)}", {}

# 定义 Gradio 界面
iface = gr.Interface(
    fn=run_agent,
    inputs=gr.Textbox(label="Enter your trading question", placeholder="Ask about stock trends, volume spikes, etc."),
    outputs=[gr.Textbox(label="Agent Reasoning"), gr.JSON(label="Matched Stocks")],
    title="📈 DeepSeek + Tushare Trading Agent",
    description="Ask anything about stock trends, volume spikes, or moving average strategies.",
    article="""
    ## Supported Functionalities

    **Example Queries:**
    - "What is the stock data for 600519.SH this month?"
    - "Show me strong uptrend stocks"
    - "List all live stocks"
    
    ### Troubleshooting:
    If you encounter any issues, ensure:
    - Your Tushare API key is correctly set.
    - The DeepSeek API is working properly.
    """
)

if __name__ == '__main__':
    # 启动 Gradio 界面
    iface.launch(server_name="0.0.0.0", server_port=7860, debug=True)
