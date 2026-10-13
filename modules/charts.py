"""Interactive Plotly charts for collected real metric history."""
import pandas as pd
import plotly.graph_objects as go

def metric_chart(history, keys, labels, title, suffix="%"):
    if not history: return None
    df=pd.DataFrame(history)
    fig=go.Figure()
    for key,label in zip(keys,labels):
        if key in df and df[key].notna().any(): fig.add_trace(go.Scatter(x=df["time_label"],y=df[key],mode="lines+markers",name=label,line={"width":2},connectgaps=False))
    if not fig.data: return None
    fig.update_layout(title=title,height=300,margin={"l":8,"r":8,"t":45,"b":8},paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font={"color":"#d8e4ec"},legend={"orientation":"h","y":1.18},yaxis={"ticksuffix":suffix,"gridcolor":"#233344"},xaxis={"title":"Collection time","gridcolor":"#182635"},hovermode="x unified")
    return fig
