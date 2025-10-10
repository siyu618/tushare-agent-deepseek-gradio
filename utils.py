import io
import matplotlib.pyplot as plt
import pandas as pd

def plot_price(df: pd.DataFrame, title: str = "Price") -> bytes:
    fig, ax = plt.subplots(figsize=(8,4))
    ax.plot(df['trade_date'], df['close'], marker='o')
    ax.set_title(title)
    ax.set_xlabel('Date')
    ax.set_ylabel('Close')
    fig.autofmt_xdate()
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    return buf