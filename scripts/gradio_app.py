import gradio as gr
import os
import threading
import time
from typing import Optional

# Global agent variable
agent = None
agent_error = None
current_task = None  # Track current running task
stop_flag = False  # Flag to stop execution

def create_agent(llm_model: str, source: str, base_url: Optional[str], api_key: Optional[str], data_path: str, verbose: bool):
    """Create a new Biomni agent with the specified configuration."""
    global agent, agent_error
    
    try:
        from biomni.agent import A1
        
        # Prepare agent parameters
        agent_params = {
            "path": data_path,
            "llm": llm_model,
            "verbose": verbose,
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
        
        verbose_status = "enabled" if verbose else "disabled"
        return "✅ Agent created successfully!", f"Current configuration:\n- Model: {llm_model}\n- Source: {source}\n- Base URL: {base_url or 'Default'}\n- Data Path: {data_path}\n- Verbose logging: {verbose_status}"
        
    except Exception as e:
        agent = None
        agent_error = str(e)
        return f"❌ Failed to create agent: {str(e)}", ""

def stop_execution():
    """Stop the current execution."""
    global stop_flag, agent
    stop_flag = True
    
    # Also call agent's stop method if agent exists
    if agent:
        agent.stop()
    
    return "⏹️ Stopping execution...", "Execution stopped by user.", "Execution stopped."

def ask_biomni_stream(question: str):
    """Ask a question to the Biomni agent with streaming output."""
    global agent, agent_error, current_task, stop_flag
    
    if agent is None:
        yield f"❌ Biomni agent not initialized. Please configure and create an agent first.\nError: {agent_error or 'No agent created'}", "", ""
        return
    
    if not question.strip():
        yield "❌ Please enter a question.", "", ""
        return
    
    stop_flag = False
    
    try:
        # Clear previous execution logs
        agent.clear_execution_logs()
        
        # Start execution in a separate thread
        result_container = {}
        
        def execute_task():
            try:
                result_container['result'] = agent.go(question.strip())
                result_container['completed'] = True
            except Exception as e:
                result_container['error'] = str(e)
                result_container['completed'] = True
        
        # Start the execution thread
        current_task = threading.Thread(target=execute_task)
        current_task.start()
        
        # Stream updates while task is running
        last_step_count = 0
        last_intermediate_count = 0
        
        while current_task.is_alive():
            if stop_flag:
                # Call agent's stop method to actually stop execution
                if agent:
                    agent.stop()
                # Stop showing updates
                yield "⏹️ **Stopping execution...**", "Execution interrupted by user.", "\n".join([entry["formatted"] for entry in agent.get_execution_logs()])
                current_task.join(timeout=1)  # Give it a moment to finish
                return
            
            # Get current logs
            logs = agent.get_execution_logs()
            execution_log = "\n".join([entry["formatted"] for entry in logs])
            
            # Get intermediate outputs
            intermediate_outputs = agent.get_intermediate_outputs()
            current_step = agent.get_current_step()
            
            # Check if we have new steps or intermediate results
            if len(logs) > last_step_count or len(intermediate_outputs) > last_intermediate_count:
                last_step_count = len(logs)
                last_intermediate_count = len(intermediate_outputs)
                
                # Format progress message
                latest_logs = logs[-min(3, len(logs)):]  # Show last 3 log entries
                progress = f"🔄 **Running...** (Step {current_step})\n\n**Recent Activity:**\n" + "\n".join([log["formatted"] for log in latest_logs])
                
                # Format intermediate results
                intermediate_text = ""
                if intermediate_outputs:
                    intermediate_text = f"**Execution Steps ({len(intermediate_outputs)} total):**\n\n"
                    # Show last 5 intermediate outputs
                    for output in intermediate_outputs[-5:]:
                        intermediate_text += f"**Step {output['step']} ({output['message_type']})** - {output['timestamp']}\n"
                        # Show a preview of the content
                        content_preview = output['content'][:500] + "..." if len(output['content']) > 500 else output['content']
                        intermediate_text += f"{content_preview}\n\n"
                else:
                    intermediate_text = "⏳ Processing... Please wait for intermediate results."
                
                yield progress, intermediate_text, execution_log
            
            time.sleep(0.5)  # Update every 0.5 seconds for better responsiveness
        
        # Wait for task to complete
        current_task.join()
        
        # Handle results
        if 'error' in result_container:
            execution_log = "\n".join([entry["formatted"] for entry in agent.get_execution_logs()])
            yield f"❌ **Error:** {result_container['error']}", "", execution_log
            return
        
        if 'result' in result_container:
            result = result_container['result']
            
            # Extract the final response from the log
            if isinstance(result, tuple) and len(result) == 2:
                log, final_response = result
                
                # Format the full execution log
                execution_log = "\n".join([entry["formatted"] for entry in agent.get_execution_logs()])
                
                # Extract intermediate results from the log
                intermediate_results = []
                for entry in log:
                    if isinstance(entry, str):
                        # Look for specific patterns in the log entries
                        if "================================" in entry:
                            intermediate_results.append(entry)
                        elif "<execute>" in entry or "<observation>" in entry:
                            intermediate_results.append(entry)
                        elif "Human Message" in entry or "Ai Message" in entry:
                            intermediate_results.append(entry)
                
                # Also include intermediate outputs
                intermediate_text = ""
                if intermediate_results:
                    intermediate_text += "**Execution Log:**\n\n" + "\n".join(intermediate_results)
                
                intermediate_outputs = agent.get_intermediate_outputs()
                if intermediate_outputs:
                    intermediate_text += f"\n\n**Detailed Steps ({len(intermediate_outputs)} total):**\n\n"
                    for output in intermediate_outputs:
                        intermediate_text += f"**Step {output['step']} ({output['message_type']})** - {output['timestamp']}\n{output['content']}\n\n"
                
                if not intermediate_text:
                    intermediate_text = "No intermediate results available."
                
                yield f"✅ **Final Response:**\n\n{final_response}", intermediate_text, execution_log
            else:
                execution_log = "\n".join([entry["formatted"] for entry in agent.get_execution_logs()])
                yield f"✅ **Biomni Response:**\n\n{str(result)}", "No intermediate results available.", execution_log
        else:
            yield "❌ No result received.", "", "\n".join([entry["formatted"] for entry in agent.get_execution_logs()])
            
    except Exception as e:
        execution_log = "\n".join([entry["formatted"] for entry in agent.get_execution_logs()]) if agent else ""
        yield f"❌ Error processing question: {str(e)}", "", execution_log

def ask_biomni(question: str):
    """Non-streaming version for backward compatibility."""
    for result in ask_biomni_stream(question):
        final_result = result
    return final_result

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
            
            verbose = gr.Checkbox(
                label="Enable Verbose Logging",
                value=False,
                info="Show detailed progress logs during execution (recommended for debugging)"
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
            
            # Control buttons
            with gr.Row():
                ask_btn = gr.Button("🤖 Ask Biomni", variant="primary", scale=2)
                stop_btn = gr.Button("⏹️ Stop", variant="stop", scale=1)
            
            # Status indicator
            status = gr.Textbox(
                label="Status",
                value="Ready",
                interactive=False,
                lines=1
            )
            
            # Multiple output areas
            with gr.Tab("Final Response"):
                response = gr.Textbox(
                    label="Final Response",
                    lines=10,
                    interactive=False
                )
            
            with gr.Tab("Intermediate Results"):
                intermediate_results = gr.Textbox(
                    label="Intermediate Results & Execution Steps",
                    lines=15,
                    interactive=False,
                    placeholder="Intermediate results will appear here..."
                )
            
            with gr.Tab("Execution Log"):
                execution_log = gr.Textbox(
                    label="Detailed Execution Log",
                    lines=15,
                    interactive=False,
                    placeholder="Detailed execution logs will appear here..."
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
        inputs=[llm_model, source, base_url, api_key, data_path, verbose],
        outputs=[status_text, config_info]
    )
    
    reset_btn.click(
        fn=reset_agent,
        outputs=[status_text, config_info]
    )
    
    # Stop button
    stop_btn.click(
        fn=stop_execution,
        outputs=[response, intermediate_results, execution_log]
    )
    
    # Streaming ask function
    ask_btn.click(
        fn=ask_biomni_stream,
        inputs=[question],
        outputs=[response, intermediate_results, execution_log]
    )
    
    # Also allow Enter key to submit question
    question.submit(
        fn=ask_biomni_stream,
        inputs=[question],
        outputs=[response, intermediate_results, execution_log]
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False) 