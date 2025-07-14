import gradio as gr
try:
    from biomni.agent import A1
    agent = A1(path='./data', llm='claude-sonnet-4-20250514')
except Exception as e:
    agent = None
    agent_error = str(e)

def ask_biomni(question):
    if agent is None:
        return f"Biomni agent 加载失败: {agent_error}"
    try:
        result = agent.go(question)
        return str(result)
    except Exception as e:
        return f"Error: {e}"

demo = gr.Interface(
    fn=ask_biomni,
    inputs=gr.Textbox(label="Your Question"),
    outputs=gr.Textbox(label="Biomni Response"),
    title="Biomni AI Agent Demo",
    description="Ask Biomni to run a biomedical task!"
)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False) 