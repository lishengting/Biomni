import gradio as gr
import os
from typing import Optional

# Global agent variable
agent = None
agent_error = None

def create_agent(llm_model: str, source: str, base_url: Optional[str], api_key: Optional[str], data_path: str):
    """Create a new Biomni agent with the specified configuration."""
    global agent, agent_error
    
    try:
        from biomni.agent import A1
        
        # Prepare agent parameters
        agent_params = {
            "path": data_path,
            "llm": llm_model,
        }
        
        # Add source if specified
        if source and source != "Auto-detect":
            agent_params["source"] = source
            
        # Add base_url and api_key if provided
        if base_url and base_url.strip():
            agent_params["base_url"] = base_url.strip()
            
        if api_key and api_key.strip():
            agent_params["api_key"] = api_key.strip()
            
        # Create the agent
        agent = A1(**agent_params)
        agent_error = None
        
        return "✅ Agent created successfully!", f"Current configuration:\n- Model: {llm_model}\n- Source: {source}\n- Base URL: {base_url or 'Default'}\n- Data Path: {data_path}"
        
    except Exception as e:
        agent = None
        agent_error = str(e)
        return f"❌ Failed to create agent: {str(e)}", ""

def ask_biomni(question: str):
    """Ask a question to the Biomni agent."""
    global agent, agent_error
    
    if agent is None:
        return f"❌ Biomni agent not initialized. Please configure and create an agent first.\nError: {agent_error or 'No agent created'}"
    
    if not question.strip():
        return "❌ Please enter a question."
    
    try:
        result = agent.go(question.strip())
        # Extract the final response from the log
        if isinstance(result, tuple) and len(result) == 2:
            log, final_response = result
            return f"🤖 Biomni Response:\n\n{final_response}"
        else:
            return f"🤖 Biomni Response:\n\n{str(result)}"
            
    except Exception as e:
        return f"❌ Error processing question: {str(e)}"

def reset_agent():
    """Reset the agent."""
    global agent, agent_error
    agent = None
    agent_error = None
    return "Agent reset. Please configure and create a new agent.", ""

# Create the Gradio interface
with gr.Blocks(title="Biomni AI Agent Demo", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🧬 Biomni AI Agent Demo")
    gr.Markdown("Configure your LLM settings and ask Biomni to run biomedical tasks!")
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("## ⚙️ Agent Configuration")
            
            # LLM Configuration
            llm_model = gr.Textbox(
                label="Model Name",
                value="gpt-4o",
                placeholder="e.g., gpt-4o, claude-3-5-sonnet-20241022, llama3:8b",
                info="The model name to use"
            )
            
            source = gr.Dropdown(
                label="Source Provider",
                choices=["Auto-detect", "OpenAI", "Anthropic", "Gemini", "Ollama", "Custom"],
                value="Auto-detect",
                info="Choose the model provider (Auto-detect will infer from model name)"
            )
            
            base_url = gr.Textbox(
                label="Base URL (Optional)",
                placeholder="e.g., https://api.openai.com/v1 or http://localhost:8000/v1",
                info="Custom API endpoint URL. Leave empty for default."
            )
            
            api_key = gr.Textbox(
                label="API Key (Optional)",
                placeholder="Enter your API key",
                type="password",
                info="API key for the service. Can also be set via environment variables."
            )
            
            data_path = gr.Textbox(
                label="Data Path",
                value="./data",
                placeholder="./data",
                info="Path where Biomni data will be stored"
            )
            
            # Control buttons
            with gr.Row():
                create_btn = gr.Button("🚀 Create Agent", variant="primary")
                reset_btn = gr.Button("🔄 Reset Agent", variant="secondary")
            
            # Status display
            status_text = gr.Textbox(
                label="Status",
                interactive=False,
                lines=2
            )
            
            config_info = gr.Textbox(
                label="Current Configuration",
                interactive=False,
                lines=4
            )
            
        with gr.Column(scale=2):
            gr.Markdown("## 💬 Chat with Biomni")
            
            # Chat interface
            question = gr.Textbox(
                label="Your Question",
                placeholder="Ask Biomni to run a biomedical task...",
                lines=3
            )
            
            ask_btn = gr.Button("🤖 Ask Biomni", variant="primary")
            
            response = gr.Textbox(
                label="Biomni Response",
                lines=15,
                interactive=False
            )
            
            # Examples
            gr.Markdown("### 📝 Example Questions:")
            gr.Examples(
                examples=[
                    "Plan a CRISPR screen to identify genes that regulate T cell exhaustion",
                    "Predict ADMET properties for this compound: CC(C)CC1=CC=C(C=C1)C(C)C(=O)O",
                    "Analyze the relationship between BRCA1 mutations and breast cancer risk",
                    "Generate a list of potential drug targets for Alzheimer's disease"
                ],
                inputs=question
            )
    
    # Event handlers
    create_btn.click(
        fn=create_agent,
        inputs=[llm_model, source, base_url, api_key, data_path],
        outputs=[status_text, config_info]
    )
    
    reset_btn.click(
        fn=reset_agent,
        outputs=[status_text, config_info]
    )
    
    ask_btn.click(
        fn=ask_biomni,
        inputs=[question],
        outputs=[response]
    )
    
    # Also allow Enter key to submit question
    question.submit(
        fn=ask_biomni,
        inputs=[question],
        outputs=[response]
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False) 