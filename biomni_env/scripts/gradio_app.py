import gradio as gr
import os
import threading
import time
import re
import json
from typing import Optional

# Global agent variable
agent = None
agent_error = None
current_task = None  # Track current running task
stop_flag = False  # Flag to stop execution

def parse_advanced_content(content: str) -> str:
    """
    高级内容解析函数，将不同格式的内容转换为HTML显示
    - 普通内容按markdown格式解析
    - <execute></execute>中的内容用深色代码窗显示
    - <observation></observation>和<solution></solution>中的内容，如果是JSON就用JSON美化显示，否则按markdown格式解析
    """
    if not content:
        return ""
    
    # 定义不同标签的处理函数
    def process_execute_tag(match):
        """处理<execute>标签，用深色代码窗显示"""
        inner_content = match.group(1)
        # 转义HTML特殊字符
        inner_content = inner_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return f'<div class="execute-block"><strong>🔧 Execute:</strong><br><pre>{inner_content}</pre></div>'
    
    def process_observation_tag(match):
        """处理<observation>标签，判断是否为JSON格式"""
        inner_content = match.group(1).strip()
        try:
            # 尝试解析为JSON
            json_data = json.loads(inner_content)
            # 美化JSON显示
            formatted_json = json.dumps(json_data, indent=2, ensure_ascii=False)
            return f'<div class="observation-block"><strong>👁️ Observation:</strong><br><pre>{formatted_json}</pre></div>'
        except (json.JSONDecodeError, ValueError):
            # 不是JSON，按markdown格式处理
            # 简单的markdown转HTML处理
            processed_content = inner_content.replace('**', '<strong>').replace('**', '</strong>')
            processed_content = processed_content.replace('`', '<code>').replace('`', '</code>')
            return f'<div class="observation-block"><strong>👁️ Observation:</strong><br>{processed_content}</div>'
    
    def process_solution_tag(match):
        """处理<solution>标签，判断是否为JSON格式"""
        inner_content = match.group(1).strip()
        try:
            # 尝试解析为JSON
            json_data = json.loads(inner_content)
            # 美化JSON显示
            formatted_json = json.dumps(json_data, indent=2, ensure_ascii=False)
            return f'<div class="solution-block"><strong>💡 Solution:</strong><br><pre>{formatted_json}</pre></div>'
        except (json.JSONDecodeError, ValueError):
            # 不是JSON，按markdown格式处理
            # 简单的markdown转HTML处理
            processed_content = inner_content.replace('**', '<strong>').replace('**', '</strong>')
            processed_content = processed_content.replace('`', '<code>').replace('`', '</code>')
            return f'<div class="solution-block"><strong>💡 Solution:</strong><br>{processed_content}</div>'
    
    # 先处理特殊标签
    content = re.sub(r'<execute>(.*?)</execute>', process_execute_tag, content, flags=re.DOTALL)
    content = re.sub(r'<observation>(.*?)</observation>', process_observation_tag, content, flags=re.DOTALL)
    content = re.sub(r'<solution>(.*?)</solution>', process_solution_tag, content, flags=re.DOTALL)
    
    # 处理其他markdown格式
    # 处理标题
    content = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', content, flags=re.MULTILINE)
    content = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)
    content = re.sub(r'^\*\* (.*?) \*\*$', r'<h4>\1</h4>', content, flags=re.MULTILINE)
    
    # 处理粗体
    content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
    
    # 处理代码块
    content = re.sub(r'```(.*?)```', r'<pre>\1</pre>', content, flags=re.DOTALL)
    
    # 处理行内代码
    content = re.sub(r'`(.*?)`', r'<code>\1</code>', content)
    
    # 处理列表
    content = re.sub(r'^- (.*?)$', r'<li>\1</li>', content, flags=re.MULTILINE)
    content = re.sub(r'(\n<li.*?</li>\n)+', r'<ul>\g<0></ul>', content)
    
    # 处理换行
    content = content.replace('\n', '<br>')
    
    return f'<div class="content-wrapper">{content}</div>'

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
                
                # Format intermediate results with advanced parsing
                intermediate_text = ""
                if intermediate_outputs:
                    intermediate_text = f"**Execution Steps ({len(intermediate_outputs)} total):**\n\n"
                    # Show all intermediate outputs without truncation
                    for output in intermediate_outputs:
                        step_header = f"**Step {output['step']} ({output['message_type']})** - {output['timestamp']}"
                        step_content = output['content']
                        # 使用高级解析函数处理内容
                        parsed_content = parse_advanced_content(step_content)
                        intermediate_text += f"{step_header}\n{parsed_content}\n\n"
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
                
                # Also include intermediate outputs with advanced parsing
                intermediate_text = ""
                if intermediate_results:
                    intermediate_text += "**Execution Log:**\n\n" + "\n".join(intermediate_results)
                
                intermediate_outputs = agent.get_intermediate_outputs()
                if intermediate_outputs:
                    intermediate_text += f"\n\n**Detailed Steps ({len(intermediate_outputs)} total):**\n\n"
                    for output in intermediate_outputs:
                        step_header = f"**Step {output['step']} ({output['message_type']})** - {output['timestamp']}"
                        step_content = output['content']
                        # 使用高级解析函数处理内容
                        parsed_content = parse_advanced_content(step_content)
                        intermediate_text += f"{step_header}\n{parsed_content}\n\n"
                
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
with gr.Blocks(title="Biomni AI Agent Demo", theme=gr.themes.Soft(), css="""
    .intermediate-results {
        max-height: 800px;
        overflow-y: auto;
        padding: 20px;
        background-color: #ffffff;
        border-radius: 8px;
        border: 1px solid #e1e5e9;
    }
    
    .intermediate-results::-webkit-scrollbar {
        width: 8px;
    }
    
    .intermediate-results::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 4px;
    }
    
    .intermediate-results::-webkit-scrollbar-thumb {
        background: #c1c1c1;
        border-radius: 4px;
    }
    
    .intermediate-results::-webkit-scrollbar-thumb:hover {
        background: #a8a8a8;
    }
    
    /* 自定义代码块样式 */
    .intermediate-results pre {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 6px;
        padding: 12px;
        margin: 10px 0;
        overflow-x: auto;
        font-family: 'Courier New', monospace;
        font-size: 14px;
        line-height: 1.4;
    }
    
    /* 自定义标签样式 */
    .intermediate-results .execute-block {
        background-color: #1e1e1e;
        color: #d4d4d4;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
        font-family: 'Courier New', monospace;
        white-space: pre-wrap;
        border-left: 4px solid #007acc;
    }
    
    .intermediate-results .observation-block {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    
    .intermediate-results .solution-block {
        background-color: #e8f5e8;
        border: 1px solid #c3e6c3;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    
    /* 内容包装器样式 */
    .intermediate-results .content-wrapper {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        line-height: 1.6;
        color: #333;
    }
    
    .intermediate-results h2 {
        color: #34495e;
        margin: 25px 0 15px 0;
        border-bottom: 2px solid #ecf0f1;
        padding-bottom: 5px;
    }
    
    .intermediate-results h3 {
        color: #2c3e50;
        margin: 20px 0 10px 0;
    }
    
    .intermediate-results h4 {
        color: #7f8c8d;
        margin: 15px 0 8px 0;
    }
    
    .intermediate-results code {
        background-color: #f4f4f4;
        padding: 2px 4px;
        border-radius: 3px;
        font-family: monospace;
    }
    
    .intermediate-results li {
        margin: 5px 0;
    }
    
    .intermediate-results ul {
        margin: 10px 0;
        padding-left: 20px;
    }
""") as demo:
    gr.Markdown("# 🧬 Biomni AI Agent Demo")
    gr.Markdown("Configure your LLM settings and ask Biomni to run biomedical tasks!")
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("## ⚙️ Agent Configuration")
            
            # LLM Configuration
            llm_model = gr.Textbox(
                label="Model Name",
                value="QWQ-32B",
                placeholder="e.g., gpt-4o, claude-3-5-sonnet-20241022, llama3:8b",
                info="The model name to use"
            )
            
            source = gr.Dropdown(
                label="Source Provider",
                choices=["Auto-detect", "OpenAI", "Anthropic", "Gemini", "Ollama", "Custom"],
                value="OpenAI",
                info="Choose the model provider (Auto-detect will infer from model name)"
            )
            
            base_url = gr.Textbox(
                label="Base URL (Optional)",
                value="http://10.49.60.23:8684/v1",
                placeholder="e.g., https://api.openai.com/v1 or http://localhost:8000/v1",
                info="Custom API endpoint URL. Leave empty for default."
            )
            
            api_key = gr.Textbox(
                label="API Key (Optional)",
                value="token-abc123",
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
                value=True,
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
            
        with gr.Column(scale=3):
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
                    lines=20,
                    interactive=False
                )
            
            with gr.Tab("Intermediate Results"):
                intermediate_results = gr.HTML(
                    label="Intermediate Results & Execution Steps",
                    value="<div style='text-align: center; color: #666; padding: 20px;'>Intermediate results will appear here...</div>",
                    elem_classes=["intermediate-results"]
                )
            
            with gr.Tab("Execution Log"):
                execution_log = gr.Textbox(
                    label="Detailed Execution Log",
                    lines=30,
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