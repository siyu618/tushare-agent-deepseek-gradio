from dotenv import load_dotenv
load_dotenv()

import gradio as gr
from agent import TushareAgent



agent = TushareAgent()


def run_agent(query):
    res = agent.handle_query(query)
    return res["reasoning"], res["result"]


iface = gr.Interface(
    fn=run_agent,
    inputs=gr.Textbox(label="Enter your trading question"),
    outputs=[gr.Textbox(label="Agent Reasoning"), gr.JSON(label="Matched Stocks")],
    title="📈 DeepSeek + Tushare Trading Agent",
    description="Ask anything about stock trends, volume spikes, or moving average strategies."
)


if __name__ == '__main__':
    iface.launch(server_name="0.0.0.0", server_port=7860)