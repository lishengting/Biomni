import gradio as gr
import os
import threading
import time
import re
import json
from typing import Optional

# Session management for multiple users
import uuid
from datetime import datetime
from typing import Dict, Optional

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
        self.lock = threading.Lock()
    
    def create_session(self, session_id: str) -> Dict:
        """创建新的用户会话"""
        with self.lock:
            session = {
                'id': session_id,
                'agent': None,
                'agent_error': None,
                'current_task': None,
                'stop_flag': False,
                'created_at': datetime.now(),
                'last_activity': datetime.now()
            }
            self.sessions[session_id] = session
            return session
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """获取用户会话"""
        with self.lock:
            return self.sessions.get(session_id)
    
    def update_session(self, session_id: str, **kwargs):
        """更新会话信息"""
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id].update(kwargs)
                self.sessions[session_id]['last_activity'] = datetime.now()
    
    def remove_session(self, session_id: str):
        """移除用户会话"""
        with self.lock:
            if session_id in self.sessions:
                # 清理agent资源
                session = self.sessions[session_id]
                if session['agent']:
                    try:
                        session['agent'].stop()
                    except:
                        pass
                del self.sessions[session_id]

# 全局会话管理器
session_manager = SessionManager()

# 兼容性变量（用于向后兼容）
agent = None
agent_error = None
current_task = None
stop_flag = False

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
    
    def process_think_tag(match):
        """处理<think>标签，用灰色小号字体显示"""
        inner_content = match.group(1).strip()
        # 转义HTML特殊字符
        inner_content = inner_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return f'<div class="think-block"><strong>💭 Thinking:</strong><br><span class="think-content">{inner_content}</span></div>'
    
    # 先处理特殊标签
    content = re.sub(r'<execute>(.*?)</execute>', process_execute_tag, content, flags=re.DOTALL)
    content = re.sub(r'<observation>(.*?)</observation>', process_observation_tag, content, flags=re.DOTALL)
    content = re.sub(r'<solution>(.*?)</solution>', process_solution_tag, content, flags=re.DOTALL)
    content = re.sub(r'<think>(.*?)</think>', process_think_tag, content, flags=re.DOTALL)
    
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

def create_agent(llm_model: str, source: str, base_url: Optional[str], api_key: Optional[str], data_path: str, verbose: bool, session_id: str = ""):
    """Create a new Biomni agent with the specified configuration."""
    global agent, agent_error
    
    print(f"[LOG] 创建agent，session_id: {session_id}")  # 添加日志
    
    # 生成会话ID（如果未提供）
    if not session_id or session_id == "":
        session_id = str(uuid.uuid4())
        print(f"[LOG] 生成新session_id: {session_id}")  # 添加日志
    
    # 创建或获取会话
    session = session_manager.get_session(session_id)
    if not session:
        session = session_manager.create_session(session_id)
        print(f"[LOG] 创建新会话: {session_id}")  # 添加日志
    else:
        print(f"[LOG] 使用现有会话: {session_id}")  # 添加日志
    
    # 打印当前所有会话信息
    print(f"[LOG] 当前活跃会话数量: {len(session_manager.sessions)}")
    for sid, sess in session_manager.sessions.items():
        print(f"[LOG] 会话 {sid}: agent={sess['agent'] is not None}, error={sess['agent_error']}")
    
    # 打印全局agent状态
    print(f"[LOG] 全局agent状态: agent={agent is not None}, error={agent_error}")
    
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
        session_agent = A1(**agent_params)
        session_manager.update_session(session_id, agent=session_agent, agent_error=None)
        
        # 不再更新全局变量，保持会话独立性
        # agent = session_agent  # 注释掉，避免共享
        # agent_error = None     # 注释掉，避免共享
        
        verbose_status = "enabled" if verbose else "disabled"
        return "✅ Agent created successfully!", f"Current configuration:\n- Model: {llm_model}\n- Source: {source}\n- Base URL: {base_url or 'Default'}\n- Data Path: {data_path}\n- Verbose logging: {verbose_status}\n- Session ID: {session_id}"
        
    except Exception as e:
        session_manager.update_session(session_id, agent=None, agent_error=str(e))
        # 不再更新全局变量，保持会话独立性
        # agent = None  # 注释掉，避免共享
        # agent_error = str(e)  # 注释掉，避免共享
        return f"❌ Failed to create agent: {str(e)}", ""

def stop_execution(session_id: str = ""):
    """Stop the current execution."""
    global stop_flag, agent
    
    # 如果没有提供session_id，停止所有会话
    if not session_id or session_id == "":
        stop_flag = True
        if agent:
            agent.stop()
        return "⏹️ Stopping execution...", "Execution stopped."
    
    # 停止特定会话
    session = session_manager.get_session(session_id)
    if session:
        session_manager.update_session(session_id, stop_flag=True)
        if session['agent']:
            session['agent'].stop()
        return "⏹️ Stopping execution...", "Execution stopped."
    
    return "⏹️ No active session found.", "No session to stop."

def ask_biomni_stream(question: str, session_id: str = ""):
    """Ask a question to the Biomni agent with streaming output."""
    global agent, agent_error, current_task, stop_flag
    
    print(f"[LOG] 提问，session_id: {session_id}, question: {question[:50]}...")  # 添加日志
    
    # 检查是否有有效的会话ID
    if not session_id or session_id == "" or session_id == "No session assigned":
        print(f"[LOG] 没有有效的session_id，提示用户先创建agent")  # 添加日志
        yield f"❌ No session assigned. Please click '🚀 Create Agent' button first to create a session.", ""
        return
    
    print(f"[LOG] 使用传入的session_id: {session_id}")  # 添加日志
    
    # 清理旧会话
    cleanup_old_sessions()
    
    # 打印会话状态报告
    print_session_status()
    
    # 获取会话
    session = session_manager.get_session(session_id)
    if not session:
        # 如果没有会话，创建一个默认会话
        session = session_manager.create_session(session_id)
        print(f"[LOG] 创建新会话: {session_id}")  # 添加日志
    else:
        print(f"[LOG] 使用现有会话: {session_id}")  # 添加日志
    
    session_agent = session['agent']
    session_error = session['agent_error']
    
    print(f"[LOG] 提问时会话状态: agent={session_agent is not None}, error={session_error}")  # 添加日志
    
    # 如果当前会话没有agent，提示用户先创建agent
    if session_agent is None:
        print(f"[LOG] 会话 {session_id} 没有agent，提示用户先创建")  # 添加日志
        yield f"❌ Biomni agent not initialized for session {session_id}.\n\n请先点击'🚀 Create Agent'按钮创建agent，然后再提问。\n\n注意：每个会话都需要独立创建agent。", ""
        return
    
    if not question.strip():
        yield "❌ Please enter a question.", ""
        return
    
    session_manager.update_session(session_id, stop_flag=False)
    
    try:
        # Clear previous execution logs
        session_agent.clear_execution_logs()
        
        # Start execution in a separate thread
        result_container = {}
        
        def execute_task():
            try:
                result_container['result'] = session_agent.go(question.strip())
                result_container['completed'] = True
            except Exception as e:
                result_container['error'] = str(e)
                result_container['completed'] = True
        
        # Start the execution thread
        session_task = threading.Thread(target=execute_task)
        session_manager.update_session(session_id, current_task=session_task)
        session_task.start()
        
        # Stream updates while task is running
        last_step_count = 0
        last_intermediate_count = 0
        
        while session_task.is_alive():
            # 检查停止标志
            session = session_manager.get_session(session_id)
            if session and session['stop_flag']:
                # Call agent's stop method to actually stop execution
                if session_agent:
                    session_agent.stop()
                # Stop showing updates
                yield "⏹️ **Stopping execution...**", "\n".join([entry["formatted"] for entry in session_agent.get_execution_logs()])
                session_task.join(timeout=1)  # Give it a moment to finish
                return
            
            # Get current logs
            logs = session_agent.get_execution_logs()
            execution_log = "\n".join([entry["formatted"] for entry in logs])
            
            # Get intermediate outputs
            intermediate_outputs = session_agent.get_intermediate_outputs()
            current_step = session_agent.get_current_step()
            
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
                    intermediate_text = f"<div style='margin: 30px 0; padding: 20px; background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; border-radius: 10px; text-align: center;'><h2 style='margin: 0; font-size: 1.5em;'>⚙️ Execution Steps ({len(intermediate_outputs)} total)</h2></div>\n\n"
                    # Show all intermediate outputs without truncation
                    for output in intermediate_outputs:
                        step_header = f"<div style='margin: 40px 0 20px 0; border-top: 3px solid #007acc; padding-top: 20px;'><h3><strong>📝 Step {output['step']} ({output['message_type']}) - {output['timestamp']}</strong></h3></div>"
                        step_content = output['content']
                        # 使用高级解析函数处理内容
                        parsed_content = parse_advanced_content(step_content)
                        intermediate_text += f"{step_header}\n{parsed_content}\n\n"
                else:
                    intermediate_text = "⏳ Processing... Please wait for intermediate results."
                
                yield intermediate_text, execution_log
            
            time.sleep(0.5)  # Update every 0.5 seconds for better responsiveness
        
        # Wait for task to complete
        session_task.join()
        
        # Handle results
        if 'error' in result_container:
            execution_log = "\n".join([entry["formatted"] for entry in session_agent.get_execution_logs()])
            yield f"❌ **Error:** {result_container['error']}", execution_log
            return
        
        if 'result' in result_container:
            result = result_container['result']
            
            # Format the full execution log
            execution_log = "\n".join([entry["formatted"] for entry in session_agent.get_execution_logs()])
            
            # Format the final output with advanced parsing
            intermediate_text = ""
            
            # Add intermediate outputs with advanced parsing
            intermediate_outputs = session_agent.get_intermediate_outputs()
            if intermediate_outputs:
                intermediate_text += f"<div style='margin: 30px 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px; text-align: center;'><h2 style='margin: 0; font-size: 1.5em;'>📊 Detailed Steps ({len(intermediate_outputs)} total)</h2></div>\n\n"
                for output in intermediate_outputs:
                    step_header = f"<div style='margin: 40px 0 20px 0; border-top: 3px solid #007acc; padding-top: 20px;'><h3><strong>📝 Step {output['step']} ({output['message_type']}) - {output['timestamp']}</strong></h3></div>"
                    step_content = output['content']
                    # 使用高级解析函数处理内容
                    parsed_content = parse_advanced_content(step_content)
                    intermediate_text += f"{step_header}\n{parsed_content}\n\n"
            
            if not intermediate_outputs:
                intermediate_text += "No intermediate results available."
            
            yield intermediate_text, execution_log
        else:
            yield "❌ No result received.", "\n".join([entry["formatted"] for entry in session_agent.get_execution_logs()])
            
    except Exception as e:
        execution_log = "\n".join([entry["formatted"] for entry in session_agent.get_execution_logs()]) if session_agent else ""
        yield f"❌ Error processing question: {str(e)}", execution_log

def ask_biomni(question: str):
    """Non-streaming version for backward compatibility."""
    for result in ask_biomni_stream(question):
        final_result = result
    return final_result

def reset_agent(session_id: str = ""):
    """Reset the agent."""
    global agent, agent_error
    
    # 如果没有提供session_id，重置全局agent
    if not session_id or session_id == "":
        agent = None
        agent_error = None
        return "Agent reset. Please configure and create a new agent.", ""
    
    # 重置特定会话
    session_manager.remove_session(session_id)
    return "Agent reset. Please configure and create a new agent.", ""

# 生成唯一的会话ID
def generate_session_id():
    """生成唯一的会话ID"""
    return str(uuid.uuid4())

# 获取当前时间戳作为会话ID的一部分
def get_timestamp_session_id():
    """使用时间戳生成会话ID，确保每个页面加载都有不同的ID"""
    import time
    return f"session_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"

def refresh_session_id():
    """刷新会话ID，确保每次调用都生成新的ID"""
    return get_timestamp_session_id()

def cleanup_old_sessions():
    """清理旧的会话，只保留最近的几个"""
    print(f"[LOG] 清理前会话数量: {len(session_manager.sessions)}")  # 添加日志
    if len(session_manager.sessions) > 10:  # 如果会话数量超过10个，清理旧的
        # 按最后活动时间排序，保留最新的5个
        sorted_sessions = sorted(session_manager.sessions.items(), 
                               key=lambda x: x[1]['last_activity'], 
                               reverse=True)
        sessions_to_keep = sorted_sessions[:5]
        sessions_to_remove = sorted_sessions[5:]
        
        for session_id, _ in sessions_to_remove:
            session_manager.remove_session(session_id)
            print(f"[LOG] 清理旧会话: {session_id}")  # 添加日志
        
        print(f"[LOG] 清理后会话数量: {len(session_manager.sessions)}")  # 添加日志

def print_session_status():
    """打印所有会话状态，用于调试"""
    print(f"[LOG] === 会话状态报告 ===")
    print(f"[LOG] 全局agent: {agent is not None}")
    print(f"[LOG] 活跃会话数量: {len(session_manager.sessions)}")
    for sid, sess in session_manager.sessions.items():
        print(f"[LOG] 会话 {sid}: agent={sess['agent'] is not None}, error={sess['agent_error']}")
    print(f"[LOG] ===================")

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
    
    .intermediate-results .think-block {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 10px;
        border-radius: 6px;
        margin: 8px 0;
    }
    
    .intermediate-results .think-content {
        color: #6c757d;
        font-size: 0.9em;
        font-style: italic;
        line-height: 1.4;
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
    
    # 显示当前会话ID（用于调试）
    session_display = gr.Textbox(
        label="Session ID (Debug)",
        value="No session assigned",
        interactive=False,
        visible=True  # 临时设为可见，用于调试
    )
    
    # 显示会话状态
    session_status = gr.Textbox(
        label="Session Status",
        value="No agent created",
        interactive=False,
        visible=True
    )
    
    # 隐藏的会话ID组件 - 初始为空
    session_id_state = gr.State(value="")
    
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
            with gr.Tab("Output"):
                intermediate_results = gr.HTML(
                    label="Output & Execution Steps",
                    value="<div style='text-align: center; color: #666; padding: 20px;'>Output will appear here...</div>",
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
    # 创建agent时分配新的会话ID
    def create_agent_with_new_session(llm_model, source, base_url, api_key, data_path, verbose, session_id):
        """创建agent时分配新的会话ID"""
        # 总是生成新的会话ID
        new_session_id = get_timestamp_session_id()
        print(f"[LOG] 创建agent时分配新会话ID: {new_session_id}")  # 添加日志
        result = create_agent(llm_model, source, base_url, api_key, data_path, verbose, new_session_id)
        # 更新会话状态
        session_status_text = f"Agent created for session: {new_session_id}"
        return result[0], result[1], new_session_id, session_status_text
    
    create_btn.click(
        fn=create_agent_with_new_session,
        inputs=[llm_model, source, base_url, api_key, data_path, verbose, session_display],
        outputs=[status_text, config_info, session_display, session_status]
    )
    
    reset_btn.click(
        fn=reset_agent,
        inputs=[session_display],
        outputs=[status_text, config_info]
    )
    
    # Stop button
    stop_btn.click(
        fn=stop_execution,
        inputs=[session_display],
        outputs=[intermediate_results, execution_log]
    )
    
    # Streaming ask function
    ask_btn.click(
        fn=ask_biomni_stream,
        inputs=[question, session_display],
        outputs=[intermediate_results, execution_log]
    )
    
    # Also allow Enter key to submit question
    question.submit(
        fn=ask_biomni_stream,
        inputs=[question, session_display],
        outputs=[intermediate_results, execution_log]
    )

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=5, max_size=20)
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False) 