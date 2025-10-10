# agent.py
import json
from deepseek_client import DeepSeekClient
from tushare_tools import (
    get_stock_match_days,
    get_all_live_stocks,
    get_stock_data
)

SAFE_FUNCTIONS = {
    "get_stock_match_days": get_stock_match_days,
    "get_all_live_stocks": get_all_live_stocks,
    "get_stock_data": get_stock_data
}

class TushareAgent:
    def __init__(self):
        self.llm = DeepSeekClient()

    def interpret_query(self, query: str) -> dict:
        """
        Use DeepSeek to interpret user's query and output a structured plan.
        """
        system_prompt = (
            "You are a Tushare expert agent. "
            "Given a user query about stock data or trading trends, "
            "decide which Tushare function to call and what parameters to use. "
            "Return a JSON object with fields: {function, params, reasoning}."
            "Allowed functions: get_stock_match_days, get_stock_data, get_all_live_stocks."
            "Examples:\n"
            "- 'List all live stocks' → {function:'get_all_live_stocks', params:{}, reasoning:'User wants all listed stocks'}\n"
            "- 'Get stock data for 600519.SH this month' → {function:'get_stock_data', params:{'ts_code':'600519.SH','start_date':'20250901','end_date':'20250930'}, reasoning:'User asked for historical data.'}\n"
            "- 'Find strong uptrend stocks recently' → {function:'get_stock_match_days', params:{'start_date':'20240101','end_date':'20241010'}, reasoning:'User asked for trend-based analysis.'}\n"
        )

        response = self.llm.chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ])

        # Try parsing JSON result
        try:
            decision = json.loads(response)
        except json.JSONDecodeError:
            decision = {
                "function": "get_stock_match_days",
                "params": {},
                "reasoning": f"Failed to parse DeepSeek output, fallback used. Raw response: {response}"
            }

        return decision

    def handle_query(self, query: str) -> dict:
        """
        Interpret query → route to correct Tushare function → return results.
        """
        decision = self.interpret_query(query)
        func_name = decision.get("function")
        params = decision.get("params", {})
        reasoning = decision.get("reasoning", "")
        print("get choice")
        if func_name not in SAFE_FUNCTIONS:
            return {
                "error": f"Unsafe or unknown function '{func_name}'",
                "reasoning": reasoning
            }

        try:
            print("=== invoke:", func_name)
            result = SAFE_FUNCTIONS[func_name](**params)
            print("=== result", result)
        except Exception as e:
            result = f"❌ Error while executing {func_name}: {e}"

        return {
            "function_called": func_name,
            "params_used": params,
            "reasoning": reasoning,
            "result": result
        }
