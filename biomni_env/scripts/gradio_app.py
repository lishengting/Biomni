import gradio as gr
import json
import os
import threading
import time
import re
import json
from typing import Optional
import shutil
from pathlib import Path

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

# 全局变量用于跟踪保存和下载状态
save_download_state = {
    'last_save_hash': None,  # 保存只能一次，内容没变就不保存
    'last_saved_file': None  # 保存的文件路径，用于重复下载
}

def get_content_hash(intermediate_results: str, execution_log: str, question: str) -> str:
    """生成内容哈希值，用于检测内容是否变化"""
    import hashlib
    content = f"{intermediate_results}{execution_log}{question}"
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def reset_save_download_state():
    """重置保存/下载状态"""
    global save_download_state
    save_download_state['last_save_hash'] = None
    save_download_state['last_saved_file'] = None
    print("[LOG] 重置保存/下载状态")
    return gr.Button(interactive=False), gr.File(visible=False), ""  # 禁用按钮、隐藏文件链接、清空状态文本

# 会话结果目录管理
def get_session_results_dir(session_id: str) -> Optional[str]:
    """获取会话的结果保存目录路径"""
    print(f"[LOG] 获取会话结果目录，session_id: {session_id}")
    
    if not session_id:
        print(f"[LOG] 无效的session_id，返回None")
        return None  # 删除原因：没有session_id时应该返回None而不是默认目录
    
    # 创建基于日期和会话ID的目录
    date_str = datetime.now().strftime("%Y%m%d")
    session_dir = f"./results/{date_str}_{session_id}"
    
    # 确保目录存在
    Path(session_dir).mkdir(parents=True, exist_ok=True)
    print(f"[LOG] 会话结果目录: {session_dir}")
    return session_dir

def setup_session_workspace(session_id: str, data_path: str) -> tuple:
    """设置会话工作空间，包括创建目录和链接数据"""
    session_dir = get_session_results_dir(session_id)
    if session_dir is None:
        return False, f"❌ 错误：无效的会话ID '{session_id}'，无法设置工作空间"
    
    original_dir = os.getcwd()
    
    try:
        # 先解析数据路径（在切换目录之前）
        target_data_path = Path(data_path).resolve()
        if not target_data_path.is_absolute():
            target_data_path = Path(original_dir) / data_path
            target_data_path = target_data_path.resolve()
        
        # 清空并重新创建会话目录
        if os.path.exists(session_dir):
            print(f"[LOG] 清空会话目录: {session_dir}")
            import shutil
            
            # 安全检查：确保不会删除数据目录
            session_path = Path(session_dir)
            if session_path.exists():
                # 检查是否有data符号链接，如果有先删除它
                data_link = session_path / "data"
                if data_link.exists() and data_link.is_symlink():
                    print(f"[LOG] 删除数据目录符号链接: {data_link}")
                    data_link.unlink()  # 只删除符号链接，不删除实际数据
                
                # 检查是否有save_folder符号链接，如果有先删除它
                save_folder_link = session_path / "save_folder"
                if save_folder_link.exists() and save_folder_link.is_symlink():
                    print(f"[LOG] 删除save_folder目录符号链接: {save_folder_link}")
                    save_folder_link.unlink()  # 只删除符号链接，不删除实际数据
            
            # 删除整个session目录
            shutil.rmtree(session_dir)
            print(f"[LOG] 会话目录已删除: {session_dir}")
        
        # 创建会话目录
        Path(session_dir).mkdir(parents=True, exist_ok=True)
        print(f"[LOG] 重新创建会话目录: {session_dir}")
        
        # 切换工作目录
        os.chdir(session_dir)
        print(f"[LOG] 工作目录已更改为: {os.getcwd()}")
        
        # 链接数据目录
        local_data_path = Path("./data")
        
        print(f"[LOG] 开始设置数据目录链接...")
        print(f"[LOG] 原始工作目录: {original_dir}")
        print(f"[LOG] 目标数据路径: {target_data_path}")
        print(f"[LOG] 本地数据路径: {local_data_path}")
        #print(f"[LOG] 目标路径是否存在: {target_data_path.exists()}")
        #print(f"[LOG] 本地路径是否存在: {local_data_path.exists()}")
        
        if target_data_path.exists() and not local_data_path.exists():
            try:
                # 创建符号链接（Unix/Linux）或目录连接（Windows）
                if hasattr(os, 'symlink'):
                    os.symlink(str(target_data_path), str(local_data_path))
                    print(f"[LOG] 已创建数据目录符号链接: {local_data_path} -> {target_data_path}")
                else:
                    # Windows下使用目录连接
                    import subprocess
                    subprocess.run(['mklink', '/J', str(local_data_path), str(target_data_path)], shell=True)
                    print(f"[LOG] 已创建数据目录连接: {local_data_path} -> {target_data_path}")
            except Exception as e:
                # 如果符号链接失败，则复制数据
                print(f"[LOG] 符号链接创建失败: {e}")
                # shutil.copytree(str(target_data_path), str(local_data_path), dirs_exist_ok=True)
                # print(f"[LOG] 已复制数据目录到: {local_data_path}")
        elif local_data_path.exists():
            print(f"[LOG] 本地数据路径已存在，跳过链接创建")
        else:
            print(f"[LOG] 目标数据路径不存在: {target_data_path}")
        
        # 链接save_folder目录
        target_save_folder = target_data_path / "save_folder"
        local_save_folder = Path("./save_folder")
        
        print(f"[LOG] 开始设置save_folder目录链接...")
        print(f"[LOG] 目标save_folder路径: {target_save_folder}")
        print(f"[LOG] 本地save_folder路径: {local_save_folder}")
        
        if target_save_folder.exists() and not local_save_folder.exists():
            try:
                # 创建符号链接（Unix/Linux）或目录连接（Windows）
                if hasattr(os, 'symlink'):
                    os.symlink(str(target_save_folder), str(local_save_folder))
                    print(f"[LOG] 已创建save_folder目录符号链接: {local_save_folder} -> {target_save_folder}")
                else:
                    # Windows下使用目录连接
                    import subprocess
                    subprocess.run(['mklink', '/J', str(local_save_folder), str(target_save_folder)], shell=True)
                    print(f"[LOG] 已创建save_folder目录连接: {local_save_folder} -> {target_save_folder}")
            except Exception as e:
                # 如果符号链接失败，则复制数据
                print(f"[LOG] save_folder符号链接创建失败: {e}")
                # shutil.copytree(str(target_save_folder), str(local_save_folder), dirs_exist_ok=True)
                # print(f"[LOG] 已复制save_folder目录到: {local_save_folder}")
        elif local_save_folder.exists():
            print(f"[LOG] 本地save_folder路径已存在，跳过链接创建")
        else:
            print(f"[LOG] 目标save_folder路径不存在: {target_save_folder}")
        
        return session_dir, original_dir
        
    except Exception as e:
        print(f"[LOG] 设置会话工作空间失败: {e}")
        return session_dir, original_dir

def cleanup_session_workspace(original_dir: str):
    """清理并恢复原始工作目录"""
    try:
        os.chdir(original_dir)
        print(f"[LOG] 工作目录已恢复为: {os.getcwd()}")
    except Exception as e:
        print(f"[LOG] 恢复工作目录失败: {e}")

def scan_session_files(session_dir: str) -> list:
    """扫描会话目录中所有新生成的文件"""
    if not session_dir or not os.path.exists(session_dir):
        print(f"[LOG] 会话目录不存在或为空: {session_dir}")
        return []
    
    session_path = Path(session_dir)
    generated_files = []
    
    # 扫描会话目录中的所有文件（排除特定目录）
    exclude_dirs = {'data', '.git', '__pycache__', '.ipynb_checkpoints'}
    
    print(f"[LOG] 开始扫描会话目录: {session_dir}")
    print(f"[LOG] 当前工作目录: {os.getcwd()}")
    
    try:
        for file_path in session_path.rglob('*'):
            if file_path.is_file():
                # 排除数据目录和隐藏文件
                if any(exclude in str(file_path).split(os.sep) for exclude in exclude_dirs):
                    continue
                if file_path.name.startswith('.'):
                    continue
                
                # 获取相对路径用于显示
                relative_path = file_path.relative_to(session_path)
                generated_files.append(str(file_path))
                print(f"[LOG] 发现文件: {file_path} (相对路径: {relative_path})")
                
    except Exception as e:
        print(f"[LOG] 扫描文件时出错: {e}")
    
    print(f"[LOG] 扫描完成，共发现 {len(generated_files)} 个文件")
    return generated_files

def generate_file_links_html(saved_files: list, session_dir: str) -> str:
    """生成保存文件的HTML下载链接"""
    if not saved_files:
        print(f"[LOG] 没有文件需要生成HTML链接")
        return ""
    
    print(f"[LOG] 开始生成文件HTML链接，共 {len(saved_files)} 个文件")
    html_parts = []
    html_parts.append("<div style='margin: 20px 0; padding: 15px; background: linear-gradient(135deg, #007bff 0%, #0056b3 100%); color: white; border-radius: 8px;'><h3 style='margin: 0 0 10px 0;'>📁 Generated Files</h3></div>")
    
    for file_path in saved_files:
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        file_size_str = format_file_size(file_size)
        
        print(f"[LOG] 处理文件: {file_name} ({file_size_str})")
        
        # 检查文件类型并决定展示方式
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # 定义不同类型的文件扩展名
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.tiff', '.webp'}
        text_extensions = {'.txt', '.log', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.yaml', '.yml', '.csv', '.tsv'}
        code_extensions = {'.py', '.js', '.html', '.css', '.json', '.xml', '.yaml', '.yml', '.sql', '.r', '.sh', '.bat'}
        
        if file_ext in image_extensions:
            print(f"[LOG] 检测到图片文件: {file_name} (扩展名: {file_ext})")
            # 图片直接展示 - 使用base64编码
            try:
                import base64
                with open(file_path, 'rb') as f:
                    img_data = f.read()
                    img_base64 = base64.b64encode(img_data).decode('utf-8')
                    mime_type = 'image/png' if file_ext == '.png' else 'image/jpeg' if file_ext in ['.jpg', '.jpeg'] else 'image/gif' if file_ext == '.gif' else 'image/svg+xml' if file_ext == '.svg' else 'image/bmp' if file_ext == '.bmp' else 'image/tiff' if file_ext == '.tiff' else 'image/webp'
                
                print(f"[LOG] 成功编码图片: {file_name} (MIME类型: {mime_type})")
                html_parts.append(f"""
                <div style='margin: 15px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px;'>
                    <h4 style='color: #333 !important;'>📸 {file_name}</h4>
                    <img src="data:{mime_type};base64,{img_base64}" style="max-width: 100%; height: auto; border: 1px solid #ccc; border-radius: 4px;" alt="{file_name}">
                    <br><br>
                    <a href="data:{mime_type};base64,{img_base64}" download="{file_name}" style="background: #28a745; color: white; padding: 8px 15px; text-decoration: none; border-radius: 4px; font-size: 14px;">⬇️ Download {file_name}</a>
                    <span style='color: #666; margin-left: 10px;'>({file_size_str})</span>
                </div>
                """)
            except Exception as e:
                print(f"[LOG] 图片编码失败: {file_name}, 错误: {e}")
                # 如果base64编码失败，尝试读取文件并重新编码
                try:
                    import base64
                    with open(file_path, 'rb') as f:
                        img_data = f.read()
                        img_base64 = base64.b64encode(img_data).decode('utf-8')
                        mime_type = 'image/png' if file_ext == '.png' else 'image/jpeg' if file_ext in ['.jpg', '.jpeg'] else 'image/gif' if file_ext == '.gif' else 'image/svg+xml' if file_ext == '.svg' else 'image/bmp' if file_ext == '.bmp' else 'image/tiff' if file_ext == '.tiff' else 'image/webp'
                    
                    html_parts.append(f"""
                    <div style='margin: 15px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px;'>
                        <h4 style='color: #333 !important;'>📸 {file_name}</h4>
                        <p style='color: #666;'>图片文件: {file_name}</p>
                        <a href="data:{mime_type};base64,{img_base64}" download="{file_name}" style="background: #28a745; color: white; padding: 8px 15px; text-decoration: none; border-radius: 4px; font-size: 14px;">⬇️ Download {file_name}</a>
                        <span style='color: #666; margin-left: 10px;'>({file_size_str})</span>
                    </div>
                    """)
                except Exception as e2:
                    print(f"[LOG] 图片文件处理完全失败: {file_name}, 错误: {e2}")
                    html_parts.append(f"""
                    <div style='margin: 15px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px;'>
                        <h4 style='color: #333 !important;'>📸 {file_name}</h4>
                        <p style='color: #666;'>图片文件: {file_name}</p>
                        <p style='color: #dc3545;'>⚠️ 文件下载失败，请检查文件权限</p>
                        <span style='color: #666; margin-left: 10px;'>({file_size_str})</span>
                    </div>
                    """)
                
        elif file_ext in text_extensions:
            print(f"[LOG] 检测到文本文件: {file_name} (扩展名: {file_ext})")
            # 文本文件直接展示内容
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 限制显示长度，避免页面过长
                    if len(content) > 5000:
                        display_content = content[:5000] + "\n\n... (内容过长，已截断，请下载完整文件查看)"
                        truncated = True
                    else:
                        display_content = content
                        truncated = False
                    
                    # 转义HTML特殊字符
                    display_content = display_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    
                    # 根据文件类型选择图标和样式
                    if file_ext in code_extensions:
                        #icon = "💻"
                        title = "代码文件"
                        bg_color = "#f8f9fa"
                        border_color = "#007acc"
                    elif file_ext in ['.md']:
                        #icon = "📝"
                        title = "Markdown文件"
                        bg_color = "#f0f8ff"
                        border_color = "#4169e1"
                    elif file_ext in ['.json']:
                        #icon = "🔧"
                        title = "JSON文件"
                        bg_color = "#fff8dc"
                        border_color = "#ffa500"
                    elif file_ext in ['.csv', '.tsv']:
                        #icon = "📊"
                        title = "数据文件"
                        bg_color = "#f0fff0"
                        border_color = "#32cd32"
                    else:
                        #icon = "📄"
                        title = "文本文件"
                        bg_color = "#f8f9fa"
                        border_color = "#6c757d"
                    icon = get_file_icon(file_ext)
                
                print(f"[LOG] 成功读取文本文件: {file_name} ({'截断' if truncated else '完整'})")
                html_parts.append(f"""
                <div style='margin: 15px 0; padding: 10px; border: 2px solid {border_color}; border-radius: 5px; background: {bg_color};'>
                    <h4 style='color: #333 !important;'>{icon} {file_name} <span style='color: #666; font-size: 0.8em;'>({title})</span></h4>
                    <div style='max-height: 400px; overflow-y: auto; background: white; padding: 15px; border-radius: 4px; border: 1px solid #ddd; font-family: monospace; font-size: 13px; line-height: 1.4; white-space: pre-wrap; color: #333 !important;'>{display_content}</div>
                    <br>
                    <a href="data:text/plain;charset=utf-8;base64,{__import__('base64').b64encode(content.encode('utf-8')).decode('utf-8')}" download="{file_name}" style="background: #28a745; color: white; padding: 8px 15px; text-decoration: none; border-radius: 4px; font-size: 14px;">⬇️ Download {file_name}</a>
                    <span style='color: #666; margin-left: 10px;'>({file_size_str})</span>
                </div>
                """)
            except UnicodeDecodeError:
                print(f"[LOG] 文本文件编码错误: {file_name}, 尝试其他编码")
                # 尝试其他编码
                try:
                    with open(file_path, 'r', encoding='gbk') as f:
                        content = f.read()
                        if len(content) > 5000:
                            display_content = content[:5000] + "\n\n... (内容过长，已截断，请下载完整文件查看)"
                        else:
                            display_content = content
                        display_content = display_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        
                    print(f"[LOG] 使用GBK编码成功读取: {file_name}")
                    html_parts.append(f"""
                    <div style='margin: 15px 0; padding: 10px; border: 2px solid #6c757d; border-radius: 5px; background: #f8f9fa;'>
                        <h4 style='color: #333 !important;'>📄 {file_name} <span style='color: #666; font-size: 0.8em;'>(文本文件 - GBK编码)</span></h4>
                        <div style='max-height: 400px; overflow-y: auto; background: white; padding: 15px; border-radius: 4px; border: 1px solid #ddd; font-family: monospace; font-size: 13px; line-height: 1.4; white-space: pre-wrap; color: #333 !important;'>{display_content}</div>
                        <br>
                        <a href="data:text/plain;charset=gbk;base64,{__import__('base64').b64encode(content.encode('gbk')).decode('utf-8')}" download="{file_name}" style="background: #28a745; color: white; padding: 8px 15px; text-decoration: none; border-radius: 4px; font-size: 14px;">⬇️ Download {file_name}</a>
                        <span style='color: #666; margin-left: 10px;'>({file_size_str})</span>
                    </div>
                    """)
                except Exception as e:
                    print(f"[LOG] 文本文件读取失败: {file_name}, 错误: {e}")
                    # 作为二进制文件处理
                    try:
                        import base64
                        with open(file_path, 'rb') as f:
                            binary_data = f.read()
                            binary_base64 = base64.b64encode(binary_data).decode('utf-8')
                        
                        html_parts.append(f"""
                        <div style='margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 5px;'>
                            <strong style='color: #333 !important;'>📄 {file_name} <span style='color: #666; font-size: 0.8em;'>(二进制文件)</span></strong>
                            <br>
                            <p style='color: #666; margin: 5px 0;'>无法以文本格式显示，请下载查看</p>
                            <a href="data:application/octet-stream;base64,{binary_base64}" download="{file_name}" style="background: #007bff; color: white; padding: 8px 15px; text-decoration: none; border-radius: 4px; font-size: 14px;">⬇️ Download {file_name}</a>
                            <span style='color: #666; margin-left: 10px;'>({file_size_str})</span>
                        </div>
                        """)
                    except Exception as e2:
                        print(f"[LOG] 二进制文件处理失败: {file_name}, 错误: {e2}")
                        html_parts.append(f"""
                        <div style='margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 5px;'>
                            <strong style='color: #333 !important;'>📄 {file_name} <span style='color: #666; font-size: 0.8em;'>(二进制文件)</span></strong>
                            <br>
                            <p style='color: #666; margin: 5px 0;'>无法以文本格式显示，请下载查看</p>
                            <p style='color: #dc3545;'>⚠️ 文件下载失败，请检查文件权限</p>
                            <span style='color: #666; margin-left: 10px;'>({file_size_str})</span>
                        </div>
                        """)
            except Exception as e:
                print(f"[LOG] 文本文件处理失败: {file_name}, 错误: {e}")
                # 作为普通文件处理
                try:
                    import base64
                    with open(file_path, 'rb') as f:
                        file_data = f.read()
                        file_base64 = base64.b64encode(file_data).decode('utf-8')
                    
                    html_parts.append(f"""
                    <div style='margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 5px;'>
                        <strong style='color: #333 !important;'>📄 {file_name}</strong>
                        <br>
                        <p style='color: #666; margin: 5px 0;'>文件读取失败，请下载查看</p>
                        <a href="data:application/octet-stream;base64,{file_base64}" download="{file_name}" style="background: #007bff; color: white; padding: 8px 15px; text-decoration: none; border-radius: 4px; font-size: 14px;">⬇️ Download {file_name}</a>
                        <span style='color: #666; margin-left: 10px;'>({file_size_str})</span>
                    </div>
                    """)
                except Exception as e2:
                    print(f"[LOG] 文件处理完全失败: {file_name}, 错误: {e2}")
                    html_parts.append(f"""
                    <div style='margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 5px;'>
                        <strong style='color: #333 !important;'>📄 {file_name}</strong>
                        <br>
                        <p style='color: #666; margin: 5px 0;'>文件读取失败，请下载查看</p>
                        <p style='color: #dc3545;'>⚠️ 文件下载失败，请检查文件权限</p>
                        <span style='color: #666; margin-left: 10px;'>({file_size_str})</span>
                    </div>
                    """)
                
        elif file_ext == '.pdf':
            print(f"[LOG] 检测到PDF文件: {file_name}")
            # PDF文件使用iframe展示和Blob下载
            try:
                import base64
                with open(file_path, 'rb') as f:
                    pdf_data = f.read()
                    pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
                
                print(f"[LOG] 成功编码PDF文件: {file_name}")
                html_parts.append(f"""
                <div style='margin: 15px 0; padding: 10px; border: 2px solid #dc3545; border-radius: 5px; background: #fff5f5;'>
                    <h4 style='color: #333 !important;'>📕 {file_name} <span style='color: #666; font-size: 0.8em;'>(PDF文档)</span></h4>
                    <div style='border: 1px solid #ddd; border-radius: 4px; overflow: hidden;'>
                        <iframe src="data:application/pdf;base64,{pdf_base64}" width="100%" height="500px" style="border: none;">
                            <p>您的浏览器不支持PDF预览。请点击下载按钮下载文件。</p>
                        </iframe>
                    </div>
                    <br>
                    <a href="data:application/pdf;base64,{pdf_base64}" download="{file_name}" 
                       style="background: #dc3545; color: white; padding: 8px 15px; text-decoration: none; border-radius: 4px; font-size: 14px; border: none; cursor: pointer; display: inline-block;">
                        ⬇️ Download {file_name}
                    </a>
                    <span style='color: #666; margin-left: 10px;'>({file_size_str})</span>
                </div>
                """)
            except Exception as e:
                print(f"[LOG] PDF文件处理失败: {file_name}, 错误: {e}")
                # 尝试重新读取PDF文件
                try:
                    import base64
                    with open(file_path, 'rb') as f:
                        pdf_data = f.read()
                        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
                    
                    html_parts.append(f"""
                    <div style='margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 5px;'>
                        <strong style='color: #333 !important;'>📕 {file_name} <span style='color: #666; font-size: 0.8em;'>(PDF文档)</span></strong>
                        <br>
                        <p style='color: #666; margin: 5px 0;'>PDF预览失败，请下载查看</p>
                        <a href="data:application/pdf;base64,{pdf_base64}" download="{file_name}" 
                           style="background: #dc3545; color: white; padding: 8px 15px; text-decoration: none; border-radius: 4px; font-size: 14px; border: none; cursor: pointer; display: inline-block;">
                            ⬇️ Download {file_name}
                        </a>
                        <span style='color: #666; margin-left: 10px;'>({file_size_str})</span>
                    </div>
                    """)
                except Exception as e2:
                    print(f"[LOG] PDF文件处理完全失败: {file_name}, 错误: {e2}")
                    html_parts.append(f"""
                    <div style='margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 5px;'>
                        <strong style='color: #333 !important;'>📕 {file_name} <span style='color: #666; font-size: 0.8em;'>(PDF文档)</span></strong>
                        <br>
                        <p style='color: #666; margin: 5px 0;'>PDF预览失败，请下载查看</p>
                        <p style='color: #dc3545;'>⚠️ 文件下载失败，请检查文件权限</p>
                        <span style='color: #666; margin-left: 10px;'>({file_size_str})</span>
                    </div>
                    """)
            
        else:
            print(f"[LOG] 处理普通文件: {file_name} (扩展名: {file_ext})")
            # 其他文件类型，根据扩展名显示不同图标
            if file_ext in ['.xlsx', '.xls']:
                #icon = "📊"
                file_type = "Excel文件"
                color = "#28a745"
            elif file_ext in ['.docx', '.doc']:
                #icon = "📝"
                file_type = "Word文档"
                color = "#007bff"
            elif file_ext in ['.pptx', '.ppt']:
                #icon = "📋"
                file_type = "PowerPoint文件"
                color = "#fd7e14"
            elif file_ext in ['.zip', '.rar', '.7z', '.tar', '.gz']:
                #icon = "🗜️"
                file_type = "压缩文件"
                color = "#6f42c1"
            elif file_ext in ['.mp4', '.avi', '.mov', '.mkv']:
                #icon = "🎬"
                file_type = "视频文件"
                color = "#e83e8c"
            elif file_ext in ['.mp3', '.wav', '.flac', '.aac']:
                #icon = "🎵"
                file_type = "音频文件"
                color = "#20c997"
            else:
                #icon = "📄"
                file_type = "未知类型"
                color = "#6c757d"
            icon = get_file_icon(file_ext)
            
            # 读取文件内容并编码为base64
            try:
                import base64
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                    file_base64 = base64.b64encode(file_data).decode('utf-8')
                
                html_parts.append(f"""
                <div style='margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 5px; border-left: 4px solid {color};'>
                    <strong style='color: #333 !important;'>{icon} {file_name} <span style='color: #666; font-size: 0.8em;'>({file_type})</span></strong>
                    <br>
                    <a href="data:application/octet-stream;base64,{file_base64}" download="{file_name}" style="background: {color}; color: white; padding: 8px 15px; text-decoration: none; border-radius: 4px; font-size: 14px; margin-top: 5px; display: inline-block;">⬇️ Download {file_name}</a>
                    <span style='color: #666; margin-left: 10px;'>({file_size_str})</span>
                </div>
                """)
            except Exception as e:
                print(f"[LOG] 文件处理失败: {file_name}, 错误: {e}")
                html_parts.append(f"""
                <div style='margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 5px; border-left: 4px solid {color};'>
                    <strong style='color: #333 !important;'>{icon} {file_name} <span style='color: #666; font-size: 0.8em;'>({file_type})</span></strong>
                    <br>
                    <p style='color: #dc3545;'>⚠️ 文件下载失败，请检查文件权限</p>
                    <span style='color: #666; margin-left: 10px;'>({file_size_str})</span>
                </div>
                """)
    
    print(f"[LOG] HTML生成完成，共 {len(html_parts)-1} 个文件链接")
    return "".join(html_parts)

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
    
    # Set environment variables for database.py to use
    os.environ["BIOMNI_CURRENT_MODEL"] = llm_model
    if source and source != "Auto-detect":
        os.environ["BIOMNI_CURRENT_SOURCE"] = source
    if base_url and base_url.strip():
        os.environ["BIOMNI_CURRENT_BASE_URL"] = base_url.strip()
    if api_key and api_key.strip():
        os.environ["BIOMNI_CURRENT_API_KEY"] = api_key.strip()
    
    # Also create a config file for the session
    config_data = {
        "model": llm_model,
        "source": source if source != "Auto-detect" else None,
        "base_url": base_url.strip() if base_url and base_url.strip() else None,
        "api_key": api_key.strip() if api_key and api_key.strip() else "EMPTY"
    }
    
    config_file_path = f"/tmp/biomni_session_{session_id}.json"
    try:
        with open(config_file_path, 'w') as f:
            json.dump(config_data, f)
        os.environ["BIOMNI_SESSION_CONFIG_FILE"] = config_file_path
        print(f"[LOG] 创建配置文件: {config_file_path}")
    except Exception as e:
        print(f"[LOG] 创建配置文件失败: {e}")
    
    # 打印当前所有会话信息
    print(f"[LOG] 当前活跃会话数量: {len(session_manager.sessions)}")
    for sid, sess in session_manager.sessions.items():
        print(f"[LOG] 会话 {sid}: agent={sess['agent'] is not None}, error={sess['agent_error']}")
    
    # 打印全局agent状态
    print(f"[LOG] 全局agent状态: agent={agent is not None}, error={agent_error}")
    
    try:
        from biomni.agent import A1
        
        # 检查是否在会话工作空间中，如果是则使用相对路径
        session_data_path = "./data"
        if Path(session_data_path).exists():
            # 如果在会话工作空间中，使用本地的./data
            effective_data_path = session_data_path
            print(f"[LOG] 使用会话工作空间数据目录: {effective_data_path}")
        else:
            # 否则使用原始数据路径
            effective_data_path = data_path
            print(f"[LOG] 使用原始数据路径: {effective_data_path}")
        
        # Prepare agent parameters
        agent_params = {
            "path": effective_data_path,
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
    
    print(f"[LOG] 停止执行，session_id: {session_id}")  # 添加日志
    
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
        print(f"[LOG] 已设置停止标志，session_id: {session_id}")  # 添加日志
        return "⏹️ Stopping execution...", "Execution stopped."
    
    return "⏹️ No active session found.", "No session to stop."

def ask_biomni_stream(question: str, session_id: str = "", data_path: str = "./data", plain: bool = False):
    """Ask a question to the Biomni agent with streaming output."""
    global agent, agent_error, current_task, stop_flag
    
    # 记录开始时间
    start_time = time.time()
    print(f"[LOG] 提问，session_id: {session_id}, question: {question[:50]}...")  # 添加日志
    
    # 计算运行时间的辅助函数
    def get_runtime_display():
        """计算并格式化运行时间"""
        elapsed_time = time.time() - start_time
        if elapsed_time < 60:
            return f"{elapsed_time:.1f}秒"
        elif elapsed_time < 3600:
            minutes = int(elapsed_time // 60)
            seconds = elapsed_time % 60
            return f"{minutes}分{seconds:.1f}秒"
        else:
            hours = int(elapsed_time // 3600)
            minutes = int((elapsed_time % 3600) // 60)
            seconds = elapsed_time % 60
            return f"{hours}小时{minutes}分{seconds:.1f}秒"
    
    # 格式化token统计信息
    def format_token_stats(agent, plain=False):
        """格式化token统计信息用于显示"""
        try:
            if not hasattr(agent, 'get_token_summary'):
                return "Token统计功能不可用"
            
            token_summary = agent.get_token_summary()
            
            if plain:
                # 纯文本格式
                stats_text = f"""Token 使用统计:
总请求数: {token_summary.get('total_requests', 0):,}
会话问题数: {token_summary.get('questions_asked', 0):,}
累计输入tokens: {token_summary.get('total_prompt_tokens', 0):,}
累计输出tokens: {token_summary.get('total_completion_tokens', 0):,}
累计总tokens: {token_summary.get('total_tokens', 0):,}
会话时长: {token_summary.get('session_duration', 'N/A')}
平均每次输入: {token_summary.get('average_prompt_tokens', 0):.1f} tokens
平均每次输出: {token_summary.get('average_completion_tokens', 0):.1f} tokens
平均每次总计: {token_summary.get('average_total_tokens', 0):.1f} tokens"""
                return stats_text
            else:
                # HTML格式
                stats_html = f"""
                <div style='margin: 20px 0; padding: 15px; background: linear-gradient(135deg, #17a2b8 0%, #138496 100%); color: white; border-radius: 8px;'>
                    <h3 style='margin: 0 0 10px 0; color: white;'>🔢 Token 使用统计</h3>
                    <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 14px;'>
                        <div><strong>总请求数:</strong> {token_summary.get('total_requests', 0):,}</div>
                        <div><strong>会话问题数:</strong> {token_summary.get('questions_asked', 0):,}</div>
                        <div><strong>累计输入tokens:</strong> {token_summary.get('total_prompt_tokens', 0):,}</div>
                        <div><strong>累计输出tokens:</strong> {token_summary.get('total_completion_tokens', 0):,}</div>
                        <div><strong>累计总tokens:</strong> {token_summary.get('total_tokens', 0):,}</div>
                        <div><strong>会话时长:</strong> {token_summary.get('session_duration', 'N/A')}</div>
                    </div>
                    <div style='margin-top: 10px; font-size: 13px; border-top: 1px solid rgba(255,255,255,0.3); padding-top: 10px;'>
                        <div><strong>平均每次输入:</strong> {token_summary.get('average_prompt_tokens', 0):.1f} tokens</div>
                        <div><strong>平均每次输出:</strong> {token_summary.get('average_completion_tokens', 0):.1f} tokens</div>
                        <div><strong>平均每次总计:</strong> {token_summary.get('average_total_tokens', 0):.1f} tokens</div>
                    </div>
                </div>
                """
                return stats_html
        except Exception as e:
            if plain:
                return f"Token统计获取失败: {str(e)}"
            else:
                return f"<div style='color: #dc3545;'>Token统计获取失败: {str(e)}</div>"
    
    # 检查是否有有效的会话ID
    if not session_id or session_id == "":
        print(f"[LOG] 没有有效的session_id，提示用户先创建agent")  # 添加日志
        yield f"❌ No session assigned. Please click '🚀 Create Agent' button first to create a session.", "", ""
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
        yield f"❌ Biomni agent not initialized for session {session_id}.\n\n请先点击'🚀 Create Agent'按钮创建agent，然后再提问。\n\n注意：每个会话都需要独立创建agent。", "", ""
        return
    
    if not question.strip():
        yield "❌ Please enter a question.", "", ""
        return
    
    # 设置会话工作空间
    print(f"[LOG] 开始设置会话工作空间，session_id: {session_id}, data_path: {data_path}")
    session_dir, original_dir = setup_session_workspace(session_id, data_path)
    print(f"[LOG] 会话工作空间设置完成，session_dir: {session_dir}, original_dir: {original_dir}")
    print(f"[LOG] 当前工作目录: {os.getcwd()}")
    
    # 验证数据目录链接
    if os.path.exists("./data"):
        print(f"[LOG] ✅ 数据目录链接成功: ./data -> {os.path.realpath('./data')}")
        try:
            data_contents = os.listdir('./data')
            print(f"[LOG] 数据目录内容: {len(data_contents)} 个项目，前10个: {data_contents[:10]}...")
        except Exception as e:
            print(f"[LOG] 读取数据目录内容失败: {e}")
    else:
        print(f"[LOG] ❌ 数据目录 ./data 不存在，链接可能失败")
    
    session_manager.update_session(session_id, stop_flag=False)
    
    try:
        # Clear previous execution logs
        session_agent.clear_execution_logs()
        
        # 记录执行前的token统计
        initial_token_stats = format_token_stats(session_agent, plain=plain)
        
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
        last_output_index = -1  # 记录上次输出的位置
        last_log_count = 0  # 记录上次日志的数量
        
        while session_task.is_alive():
            # 检查停止标志
            session = session_manager.get_session(session_id)
            if session and session['stop_flag']:
                # Call agent's stop method to actually stop execution
                if session_agent:
                    session_agent.stop()
                # 获取当前的执行日志
                logs = session_agent.get_execution_logs()
                if plain:
                    # plain模式下只输出新增的日志
                    current_log_count = len(logs)
                    if current_log_count > last_log_count:
                        # 有新日志，只输出新增的部分
                        new_logs = logs[last_log_count:]
                        execution_log = "\n".join([entry["formatted"] for entry in new_logs])
                        last_log_count = current_log_count
                    else:
                        # 没有新日志
                        execution_log = ""
                else:
                    # HTML模式下输出所有日志
                    execution_log = "\n".join([entry["formatted"] for entry in logs])
                # 获取当前的中间输出
                intermediate_outputs = session_agent.get_intermediate_outputs()
                
                # 扫描会话目录中的所有新生成文件
                saved_files = scan_session_files(session_dir)
                files_html = generate_file_links_html(saved_files, session_dir)
                
                # 获取最终token统计
                final_token_stats = format_token_stats(session_agent, plain=plain)
                
                # 构建停止消息，保留现有内容
                if plain:
                    # 纯文本格式 - 输出所有新内容
                    if intermediate_outputs:
                        # 从上次位置往后输出所有新内容
                        current_index = len(intermediate_outputs) - 1
                        if current_index > last_output_index:
                            # 有新内容，输出从上次位置到当前位置的所有内容
                            new_outputs = intermediate_outputs[last_output_index + 1:]
                            stop_message = "\n\n".join([output['content'] for output in new_outputs])
                            last_output_index = current_index
                        else:
                            # 没有新内容
                            stop_message = "无新内容"
                    else:
                        stop_message = "无中间结果"
                    
                    # plain模式下不追加token统计，因为API有专门的token_stats输出
                    
                    # 添加停止信息
                    runtime_display = get_runtime_display()
                    stop_message += f"\n⏹️ 执行已停止\n用户已停止任务执行。\n运行时间: {runtime_display}\n"
                    
                else:
                    # HTML格式
                    stop_message = ""
                    if intermediate_outputs:
                        stop_message = f"<div style='margin: 30px 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px; text-align: center;'><h2 style='margin: 0; font-size: 1.5em;'>📊 Execution Steps ({len(intermediate_outputs)} total)</h2></div>\n\n"
                        for output in intermediate_outputs:
                            step_header = f"<div style='margin: 40px 0 20px 0; border-top: 3px solid #007acc; padding-top: 20px;'><h3><strong>📝 Step {output['step']} ({output['message_type']}) - {output['timestamp']}</strong></h3></div>"
                            step_content = output['content']
                            parsed_content = parse_advanced_content(step_content)
                            stop_message += f"{step_header}\n{parsed_content}\n\n"
                    
                    # 添加生成的文件链接
                    if files_html:
                        stop_message += files_html
                    
                    # 添加token统计信息
                    stop_message += final_token_stats
                    
                    # 追加停止信息和运行时间
                    runtime_display = get_runtime_display()
                    stop_message += f"\n\n<div style='margin: 20px 0; padding: 15px; background: linear-gradient(135deg, #dc3545 0%, #c82333 100%); color: white; border-radius: 8px; text-align: center;'><h3 style='margin: 0;'>⏹️ Execution Stopped</h3><p style='margin: 5px 0 0 0;'>Task execution has been stopped by user.</p><p style='margin: 5px 0 0 0;'>运行时间: {runtime_display}</p></div>"
                
                # 清理会话工作空间
                cleanup_session_workspace(original_dir)
                
                yield stop_message, execution_log, final_token_stats
                session_task.join()  # Give it a moment to finish timeout=1
                return
            
            # Get current logs
            logs = session_agent.get_execution_logs()
            if plain:
                # plain模式下只输出新增的日志
                current_log_count = len(logs)
                if current_log_count > last_log_count:
                    # 有新日志，只输出新增的部分
                    new_logs = logs[last_log_count:]
                    execution_log = "\n".join([entry["formatted"] for entry in new_logs])
                    last_log_count = current_log_count
                else:
                    # 没有新日志
                    execution_log = ""
            else:
                # HTML模式下输出所有日志
                execution_log = "\n".join([entry["formatted"] for entry in logs])
            
            # Get intermediate outputs
            intermediate_outputs = session_agent.get_intermediate_outputs()
            
            # Get current token stats
            current_token_stats = format_token_stats(session_agent, plain=plain)
            
            # Check if we have new steps or intermediate results
            if len(logs) > last_step_count or len(intermediate_outputs) > last_intermediate_count:
                last_step_count = len(logs)
                last_intermediate_count = len(intermediate_outputs)
                
                
                # Format intermediate results based on plain mode
                if plain:
                    # Plain text format for API - output all new content since last update
                    if intermediate_outputs:
                        # 从上次位置往后输出所有新内容
                        current_index = len(intermediate_outputs) - 1
                        if current_index > last_output_index:
                            # 有新内容，输出从上次位置到当前位置的所有内容
                            new_outputs = intermediate_outputs[last_output_index + 1:]
                            intermediate_text = "\n\n".join([output['content'] for output in new_outputs])
                            last_output_index = current_index
                        else:
                            # 没有新内容，保持上次的输出
                            intermediate_text = "⏳ 处理中... 请等待中间结果。"
                    else:
                        intermediate_text = "⏳ 处理中... 请等待中间结果。"
                    
                    # plain模式下不追加token统计，因为API有专门的token_stats输出
                    
                else:
                    # HTML format
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
                    
                    # 添加当前token统计
                    intermediate_text += current_token_stats
                
                yield intermediate_text, execution_log, current_token_stats
            
            time.sleep(0.5)  # Update every 0.5 seconds for better responsiveness
        
        # Wait for task to complete
        session_task.join()
        
        # 清理会话工作空间
        cleanup_session_workspace(original_dir)
        
        # Handle results
        if 'error' in result_container:
            logs = session_agent.get_execution_logs()
            if plain:
                # plain模式下只输出新增的日志
                current_log_count = len(logs)
                if current_log_count > last_log_count:
                    # 有新日志，只输出新增的部分
                    new_logs = logs[last_log_count:]
                    execution_log = "\n".join([entry["formatted"] for entry in new_logs])
                    last_log_count = current_log_count
                else:
                    # 没有新日志
                    execution_log = ""
            else:
                # HTML模式下输出所有日志
                execution_log = "\n".join([entry["formatted"] for entry in logs])
            
            # 扫描会话目录中的所有新生成文件
            saved_files = scan_session_files(session_dir)
            files_html = generate_file_links_html(saved_files, session_dir)
            
            # 获取最终token统计
            final_token_stats = format_token_stats(session_agent, plain=plain)
            
            runtime_display = get_runtime_display()
            
            if plain:
                # 纯文本格式错误消息
                error_message = f"❌ 错误: {result_container['error']}\n\n"
                # plain模式下不追加token统计，因为API有专门的token_stats输出
                error_message += f"运行时间: {runtime_display}\n"
            else:
                # HTML格式错误消息
                error_message = f"❌ **Error:** {result_container['error']}\n\n"
                if files_html:
                    error_message += files_html
                error_message += final_token_stats
                error_message += f"\n\n<div style='margin: 20px 0; padding: 15px; background: linear-gradient(135deg, #dc3545 0%, #c82333 100%); color: white; border-radius: 8px; text-align: center;'><h3 style='margin: 0;'>❌ 执行出错</h3><p style='margin: 5px 0 0 0;'>运行时间: {runtime_display}</p></div>"
            yield error_message, execution_log, final_token_stats
            return
        
        if 'result' in result_container:
            
            # Format the full execution log
            logs = session_agent.get_execution_logs()
            if plain:
                # plain模式下只输出新增的日志
                current_log_count = len(logs)
                if current_log_count > last_log_count:
                    # 有新日志，只输出新增的部分
                    new_logs = logs[last_log_count:]
                    execution_log = "\n".join([entry["formatted"] for entry in new_logs])
                    last_log_count = current_log_count
                else:
                    # 没有新日志
                    execution_log = ""
            else:
                # HTML模式下输出所有日志
                execution_log = "\n".join([entry["formatted"] for entry in logs])
            
            # 扫描会话目录中的所有新生成文件
            saved_files = scan_session_files(session_dir)
            files_html = generate_file_links_html(saved_files, session_dir)
            
            # 获取最终token统计
            final_token_stats = format_token_stats(session_agent, plain=plain)
            
            # Format the final output based on plain mode
            if plain:
                # 纯文本格式 - 输出所有新内容
                intermediate_outputs = session_agent.get_intermediate_outputs()
                if intermediate_outputs:
                    # 从上次位置往后输出所有新内容
                    current_index = len(intermediate_outputs) - 1
                    if current_index > last_output_index:
                        # 有新内容，输出从上次位置到当前位置的所有内容
                        new_outputs = intermediate_outputs[last_output_index + 1:]
                        intermediate_text = "\n\n".join([output['content'] for output in new_outputs])
                        last_output_index = current_index
                    else:
                        # 没有新内容
                        intermediate_text = "无新内容"
                else:
                    intermediate_text = "无中间结果可用。"
                
                # plain模式下不追加token统计，因为API有专门的token_stats输出
                
                # 添加总运行时间
                runtime_display = get_runtime_display()
                intermediate_text += f"\n✅ 执行完成\n总运行时间: {runtime_display}\n"
                
            else:
                # HTML格式
                intermediate_text = ""
                
                # 添加中间输出
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
                
                # 添加生成的文件链接
                if files_html:
                    intermediate_text += files_html
                    
                # 添加最终token统计
                intermediate_text += final_token_stats
                
                # 添加总运行时间
                runtime_display = get_runtime_display()
                intermediate_text += f"\n\n<div style='margin: 20px 0; padding: 15px; background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; border-radius: 8px; text-align: center;'><h3 style='margin: 0;'>✅ 执行完成</h3><p style='margin: 5px 0 0 0;'>总运行时间: {runtime_display}</p></div>"
            
            yield intermediate_text, execution_log, final_token_stats
        else:
            runtime_display = get_runtime_display()
            final_token_stats = format_token_stats(session_agent, plain=plain)
            
            # 获取执行日志
            logs = session_agent.get_execution_logs()
            if plain:
                # plain模式下只输出新增的日志
                current_log_count = len(logs)
                if current_log_count > last_log_count:
                    # 有新日志，只输出新增的部分
                    new_logs = logs[last_log_count:]
                    execution_log = "\n".join([entry["formatted"] for entry in new_logs])
                    last_log_count = current_log_count
                else:
                    # 没有新日志
                    execution_log = ""
            else:
                # HTML模式下输出所有日志
                execution_log = "\n".join([entry["formatted"] for entry in logs])
            
            if plain:
                no_result_message = f"❌ 无结果\n\n运行时间: {runtime_display}\n"
            else:
                no_result_message = f"❌ No result received.\n\n{final_token_stats}\n\n<div style='margin: 20px 0; padding: 15px; background: linear-gradient(135deg, #ffc107 0%, #e0a800 100%); color: white; border-radius: 8px; text-align: center;'><h3 style='margin: 0;'>⚠️ 无结果</h3><p style='margin: 5px 0 0 0;'>运行时间: {runtime_display}</p></div>"
            yield no_result_message, execution_log, final_token_stats
            
    except Exception as e:
        # 确保在异常时也清理工作空间
        if 'original_dir' in locals():
            cleanup_session_workspace(original_dir)
            
        logs = session_agent.get_execution_logs() if session_agent else []
        if plain:
            # plain模式下只输出新增的日志
            if session_agent:
                current_log_count = len(logs)
                if current_log_count > last_log_count:
                    # 有新日志，只输出新增的部分
                    new_logs = logs[last_log_count:]
                    execution_log = "\n".join([entry["formatted"] for entry in new_logs])
                    last_log_count = current_log_count
                else:
                    # 没有新日志
                    execution_log = ""
            else:
                execution_log = ""
        else:
            # HTML模式下输出所有日志
            execution_log = "\n".join([entry["formatted"] for entry in logs])
        
        # 扫描会话目录中的所有新生成文件（如果有）
        saved_files = []
        files_html = ""
        if session_dir:
            saved_files = scan_session_files(session_dir)
            if saved_files:
                files_html = generate_file_links_html(saved_files, session_dir)
        
        # 获取错误时的token统计
        error_token_stats = format_token_stats(session_agent, plain=plain) if session_agent else ("Token统计不可用" if plain else "<div style='color: #dc3545;'>Token统计不可用</div>")
        
        runtime_display = get_runtime_display()
        
        if plain:
            error_message = f"❌ 处理问题时出错: {str(e)}\n\n"
            if files_html:
                error_message += files_html
            # plain模式下不追加token统计，因为API有专门的token_stats输出
            error_message += f"运行时间: {runtime_display}\n"
        else:
            error_message = f"❌ Error processing question: {str(e)}\n\n"
            if files_html:
                error_message += files_html
            error_message += error_token_stats
            error_message += f"\n\n<div style='margin: 20px 0; padding: 15px; background: linear-gradient(135deg, #dc3545 0%, #c82333 100%); color: white; border-radius: 8px; text-align: center;'><h3 style='margin: 0;'>❌ 处理出错</h3><p style='margin: 5px 0 0 0;'>运行时间: {runtime_display}</p></div>"
        yield error_message, execution_log, error_token_stats

def ask_biomni(question: str, data_path: str = "./data", plain: bool = False):
    """Non-streaming version for backward compatibility."""
    for result in ask_biomni_stream(question, data_path=data_path, plain=plain):
        final_result = result
    return final_result


def upload_and_add_data(files, descriptions, session_id: str = ""):
    """Upload files and add them to the agent's data lake."""
    if not session_id or session_id == "":
        return "❌ No session assigned. Please create an agent first.", ""
    
    session = session_manager.get_session(session_id)
    if not session or not session['agent']:
        return "❌ Agent not found. Please create an agent first.", ""
    
    if not files:
        return "❌ No files selected for upload.", ""
    
    try:
        # Prepare data dictionary
        data_dict = {}
        for i, file in enumerate(files):
            if file is not None:
                # Get description for this file
                description = descriptions[i] if i < len(descriptions) and descriptions[i].strip() else f"Uploaded file: {file.name}"
                data_dict[file.name] = description
        
        # Add data to agent
        success = session['agent'].add_data(data_dict)
        
        if success:
            # List current custom data
            custom_data = session['agent'].list_custom_data()
            data_list = "\n".join([f"• {name}: {desc}" for name, desc in custom_data])
            
            return f"✅ Successfully added {len(data_dict)} file(s) to data lake.", f"📊 Custom Data in Agent:\n\n{data_list}"
        else:
            return "❌ Failed to add data to agent.", ""
            
    except Exception as e:
        return f"❌ Error uploading data: {str(e)}", ""


def list_custom_data(session_id: str = ""):
    """List all custom data in the agent's data lake."""
    if not session_id or session_id == "":
        return "❌ No session assigned. Please create an agent first."
    
    session = session_manager.get_session(session_id)
    if not session or not session['agent']:
        return "❌ Agent not found. Please create an agent first."
    
    try:
        custom_data = session['agent'].list_custom_data()
        if custom_data:
            data_list = "\n".join([f"• {name}: {desc}" for name, desc in custom_data])
            return f"📊 Custom Data in Agent:\n\n{data_list}"
        else:
            return "📊 No custom data found in agent."
    except Exception as e:
        return f"❌ Error listing data: {str(e)}"


def remove_custom_data(data_name: str, session_id: str = ""):
    """Remove a custom data item from the agent's data lake."""
    if not session_id or session_id == "":
        return "❌ No session assigned. Please create an agent first."
    
    if not data_name.strip():
        return "❌ Please specify a data name to remove."
    
    session = session_manager.get_session(session_id)
    if not session or not session['agent']:
        return "❌ Agent not found. Please create an agent first."
    
    try:
        success = session['agent'].remove_custom_data(data_name.strip())
        if success:
            return f"✅ Successfully removed '{data_name}' from data lake."
        else:
            return f"❌ Data item '{data_name}' not found in data lake."
    except Exception as e:
        return f"❌ Error removing data: {str(e)}"


def get_token_statistics(session_id: str = ""):
    """获取详细的token统计信息"""
    if not session_id or session_id == "":
        return "❌ No session assigned. Please create an agent first.", ""
    
    session = session_manager.get_session(session_id)
    if not session or not session['agent']:
        return "❌ Agent not found. Please create an agent first.", ""
    
    try:
        agent = session['agent']
        if not hasattr(agent, 'get_token_summary'):
            return "Token统计功能不可用", ""
        
        token_summary = agent.get_token_summary()
        token_history = agent.get_token_history()
        
        # 生成主要统计信息
        stats_html = f"""
        <div style='margin: 20px 0; padding: 20px; background: linear-gradient(135deg, #17a2b8 0%, #138496 100%); color: white; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);'>
            <h2 style='margin: 0 0 15px 0; color: white; text-align: center;'>🔢 Token 使用统计总览</h2>
            <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 15px 0;'>
                <div style='background: rgba(255,255,255,0.2); padding: 15px; border-radius: 8px; text-align: center;'>
                    <div style='font-size: 24px; font-weight: bold; margin-bottom: 5px;'>{token_summary.get('total_requests', 0):,}</div>
                    <div style='font-size: 14px; opacity: 0.9;'>总请求数</div>
                </div>
                <div style='background: rgba(255,255,255,0.2); padding: 15px; border-radius: 8px; text-align: center;'>
                    <div style='font-size: 24px; font-weight: bold; margin-bottom: 5px;'>{token_summary.get('questions_asked', 0):,}</div>
                    <div style='font-size: 14px; opacity: 0.9;'>会话问题数</div>
                </div>
                <div style='background: rgba(255,255,255,0.2); padding: 15px; border-radius: 8px; text-align: center;'>
                    <div style='font-size: 24px; font-weight: bold; margin-bottom: 5px;'>{token_summary.get('total_tokens', 0):,}</div>
                    <div style='font-size: 14px; opacity: 0.9;'>累计总tokens</div>
                </div>
                <div style='background: rgba(255,255,255,0.2); padding: 15px; border-radius: 8px; text-align: center;'>
                    <div style='font-size: 18px; font-weight: bold; margin-bottom: 5px;'>{token_summary.get('session_duration', 'N/A')}</div>
                    <div style='font-size: 14px; opacity: 0.9;'>会话时长</div>
                </div>
            </div>
            <div style='display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-top: 15px; font-size: 14px; border-top: 1px solid rgba(255,255,255,0.3); padding-top: 15px;'>
                <div><strong>累计输入:</strong> {token_summary.get('total_prompt_tokens', 0):,} tokens</div>
                <div><strong>累计输出:</strong> {token_summary.get('total_completion_tokens', 0):,} tokens</div>
                <div><strong>平均每次:</strong> {token_summary.get('average_total_tokens', 0):.1f} tokens</div>
            </div>
        </div>
        """
        
        # 生成详细历史记录
        history_html = ""
        if token_history:
            history_html = "<div style='margin: 10px 0;'>"
            for i, record in enumerate(reversed(token_history[-10:])):  # 显示最近10条记录
                record_html = f"""
                <div style='margin: 10px 0; padding: 12px; background: #f8f9fa; border-left: 4px solid #007bff; border-radius: 4px;'>
                    <div style='font-weight: bold; color: #007bff; margin-bottom: 5px;'>
                        请求 #{record['request_id']} - {record['timestamp']}
                    </div>
                    <div style='display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; font-size: 13px; color: #666;'>
                        <div>📝 输入: {record['prompt_tokens']:,} tokens</div>
                        <div>💬 输出: {record['completion_tokens']:,} tokens</div>
                        <div>📊 总计: {record['total_tokens']:,} tokens</div>
                    </div>
                    <div style='font-size: 12px; color: #888; margin-top: 5px;'>
                        模型: {record.get('model', '未知')} | 响应长度: {record.get('response_length', 0):,} 字符
                    </div>
                </div>
                """
                history_html += record_html
            history_html += "</div>"
        else:
            history_html = "<div style='text-align: center; color: #666; padding: 20px;'>暂无token使用历史记录</div>"
        
        return stats_html, history_html
        
    except Exception as e:
        return f"❌ 获取token统计失败: {str(e)}", ""

def reset_token_statistics(session_id: str = ""):
    """重置token统计"""
    if not session_id or session_id == "":
        return "❌ No session assigned. Please create an agent first.", ""
    
    session = session_manager.get_session(session_id)
    if not session or not session['agent']:
        return "❌ Agent not found. Please create an agent first.", ""
    
    try:
        agent = session['agent']
        if hasattr(agent, 'reset_token_stats'):
            agent.reset_token_stats()
            return "✅ Token统计已重置", "<div style='text-align: center; color: #666; padding: 10px;'>Token统计已重置，暂无历史记录</div>"
        else:
            return "❌ Token统计重置功能不可用", ""
    except Exception as e:
        return f"❌ 重置token统计失败: {str(e)}", ""

def get_new_files_list(session_id: str = "") -> list:
    """获取会话目录中所有新增文件的完整路径列表
    
    Args:
        session_id: 会话ID，如果为空则返回空列表
        
    Returns:
        list: 所有新增文件的完整路径列表
    """
    if not session_id or session_id == "":
        print("[LOG] 未提供会话ID，返回空列表")
        return []
    
    # 获取会话结果目录
    session_dir = get_session_results_dir(session_id)
    if session_dir is None:
        print(f"[LOG] 无效的会话ID '{session_id}'，无法获取文件列表")
        return []
    
    print(f"[LOG] 获取新增文件列表，会话目录: {session_dir}")
    
    # 使用scan_session_files获取所有文件
    new_files = scan_session_files(session_dir)
    print(f"[LOG] 发现 {len(new_files)} 个新增文件")
    return new_files

def export_token_data(session_id: str = ""):
    """导出token使用数据"""
    print(f"[LOG] 开始导出token数据，session_id: {session_id}")
    
    if not session_id or session_id == "":
        print(f"[LOG] 未提供session_id，导出失败")
        return "❌ No session assigned. Please create an agent first.", None
    
    session = session_manager.get_session(session_id)
    if not session or not session['agent']:
        return "❌ Agent not found. Please create an agent first.", None
    
    try:
        agent = session['agent']
        if not hasattr(agent, 'get_token_summary'):
            return "Token统计功能不可用", None
        
        token_summary = agent.get_token_summary()
        token_history = agent.get_token_history()
        
        # 生成CSV格式的数据
        import io
        import csv
        from datetime import datetime
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow(['Request_ID', 'Timestamp', 'Prompt_Tokens', 'Completion_Tokens', 'Total_Tokens', 'Model', 'Response_Length'])
        
        # 写入历史数据
        for record in token_history:
            writer.writerow([
                record['request_id'],
                record['timestamp'],
                record['prompt_tokens'],
                record['completion_tokens'],
                record['total_tokens'],
                record.get('model', 'unknown'),
                record.get('response_length', 0)
            ])
        
        # 添加汇总信息
        writer.writerow([])
        writer.writerow(['=== Token Usage Summary ==='])
        writer.writerow(['Total Requests', token_summary.get('total_requests', 0)])
        writer.writerow(['Questions Asked', token_summary.get('questions_asked', 0)])
        writer.writerow(['Total Prompt Tokens', token_summary.get('total_prompt_tokens', 0)])
        writer.writerow(['Total Completion Tokens', token_summary.get('total_completion_tokens', 0)])
        writer.writerow(['Total Tokens', token_summary.get('total_tokens', 0)])
        writer.writerow(['Session Duration', token_summary.get('session_duration', 'N/A')])
        writer.writerow(['Average Prompt Tokens', f"{token_summary.get('average_prompt_tokens', 0):.2f}"])
        writer.writerow(['Average Completion Tokens', f"{token_summary.get('average_completion_tokens', 0):.2f}"])
        writer.writerow(['Average Total Tokens', f"{token_summary.get('average_total_tokens', 0):.2f}"])
        
        csv_content = output.getvalue()
        output.close()
        
        # 创建导出目录 - 使用会话结果目录
        import os
        # export_dir = "./exports"  # 删除原因：目录路径不正确，应该使用会话结果目录
        export_dir = get_session_results_dir(session_id)
        if export_dir is None:
            return f"❌ 错误：无效的会话ID '{session_id}'，无法导出token数据", None
        
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"token_usage_{session_id[:8]}_{timestamp}.csv"
        file_path = os.path.join(export_dir, filename)
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(csv_content)
        
        # 返回成功消息和文件对象供Gradio下载
        print(f"[LOG] Token数据导出成功，文件路径: {file_path}")
        return f"✅ Token数据导出成功！文件保存到: {file_path}", gr.File(value=file_path, visible=True)
        
    except Exception as e:
        print(f"[LOG] Token数据导出失败: {str(e)}")
        return f"❌ 导出token数据失败: {str(e)}", None

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

def generate_html_template(intermediate_results: str, execution_log: str, filename: str, execute_color: str = "#333333") -> str:
    """生成通用的HTML模板"""
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Biomni Results - {filename}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .log-section {{ background: #f8f9fa; font-family: monospace; white-space: pre-wrap; }}
        h1, h2 {{ color: #333; }}
        .timestamp {{ color: #666; font-size: 0.9em; }}
        .intermediate-results {{ max-height: 800px; overflow-y: auto; padding: 20px; background-color: #ffffff; border-radius: 8px; border: 1px solid #e1e5e9; }}
        .intermediate-results pre {{ background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 6px; padding: 12px; margin: 10px 0; overflow-x: auto; font-family: 'Courier New', monospace; font-size: 14px; line-height: 1.4; }}
        .intermediate-results .execute-block {{ background-color: #1e1e1e; color: {execute_color}; padding: 15px; border-radius: 8px; margin: 10px 0; font-family: 'Courier New', monospace; white-space: pre-wrap; border-left: 4px solid #007acc; font-weight: normal; }}
        .intermediate-results .observation-block {{ background-color: #f8f9fa; border: 1px solid #e9ecef; padding: 15px; border-radius: 8px; margin: 10px 0; }}
        .intermediate-results .solution-block {{ background-color: #e8f5e8; border: 1px solid #c3e6c3; padding: 15px; border-radius: 8px; margin: 10px 0; }}
        .intermediate-results .think-block {{ background-color: #f8f9fa; border: 1px solid #e9ecef; padding: 10px; border-radius: 6px; margin: 8px 0; }}
        .intermediate-results .think-content {{ color: #6c757d; font-size: 0.9em; font-style: italic; line-height: 1.4; }}
    </style>
</head>
<body>
    <h1>🧬 Biomni AI Agent Results</h1>
    <div class="timestamp">Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
    
    <div class="section">
        <h2>📊 Output & Execution Steps</h2>
        <div class="intermediate-results">
            {intermediate_results}
        </div>
    </div>
    
    <div class="section log-section">
        <h2>📝 Detailed Execution Log</h2>
        {execution_log}
    </div>
</body>
</html>"""

def save_current_results(intermediate_results: str, execution_log: str, session_id: str = "", question: str = "") -> tuple:
    """保存当前结果到本地文件"""
    print(f"[LOG] 开始保存结果，session_id: {session_id}")  # 添加日志
    
    try:
        # 生成保存目录
        if session_id:
            save_dir = get_session_results_dir(session_id)
            if save_dir is None:
                return f"❌ 错误：无效的会话ID '{session_id}'", ""
        else:
            # save_dir = "./results"
            return f"❌ 错误：无效的会话ID '{session_id}'，无法保存结果", ""
        
        # 确保目录存在
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        
        # 生成时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 生成文件名
        if question:
            # 从问题中提取前20个字符作为文件名的一部分
            question_part = re.sub(r'[^\w\s-]', '', question[:20]).strip().replace(' ', '_')
            if question_part:
                combined_filename = f"biomni_results_{timestamp}_{question_part}.html"
            else:
                combined_filename = f"biomni_results_{timestamp}.html"
        else:
            combined_filename = f"biomni_results_{timestamp}.html"
        
        # 创建包含HTML和日志的完整文档（只生成这一个文件）
        combined_content = generate_html_template(intermediate_results, execution_log, combined_filename, "#333333")
        
        # 保存完整文档（这是唯一生成的文件）
        combined_path = os.path.join(save_dir, combined_filename)
        with open(combined_path, 'w', encoding='utf-8') as f:
            f.write(combined_content)
        print(f"[LOG] 已保存完整文档到: {combined_path}")  # 添加日志
        
        # 扫描并保存生成的文件
        saved_files = scan_session_files(save_dir)
        files_info = ""
        if saved_files:
            files_info = "\n\n生成的文件:\n"
            for file_path in saved_files:
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                file_size_str = format_file_size(file_size)
                files_info += f"• {file_name} ({file_size_str})\n"
        
        success_message = f"✅ 结果已成功保存到本地!\n\n保存位置: {save_dir}\n\n保存的文件:\n• {combined_filename}{files_info}\n\n💡 提示: 您也可以点击浏览器下载按钮直接下载完整结果文件。"
        
        print(f"[LOG] 保存完成，共保存 {len(saved_files) + 1} 个文件")  # 添加日志
        return success_message, save_dir
        
    except Exception as e:
        error_message = f"❌ 保存结果失败: {str(e)}"
        print(f"[LOG] 保存失败: {e}")  # 添加日志
        return error_message, ""

# Create the Gradio interface
js_code = """
<script>
// 删除原因：移除downloadPDFBlob相关函数，改用base64 data URL方式下载
// 所有文件下载现在都使用 <a href="data:application/xxx;base64,xxx" download="filename"> 的方式

// 保存结果到本地的函数 saveResultsToLocal 也移除
</script>
"""

css_code = """
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
    
    /* 默认文字颜色 */
    .intermediate-results div {
        color: #333 !important;
    }
    
    /* 特别针对状态栏 - 使用更具体的选择器 */
    .intermediate-results div[style*="background: linear-gradient"],
    .intermediate-results div[style*="background-color: rgb(220, 53, 69)"],
    .intermediate-results div[style*="background-color: #dc3545"],
    .intermediate-results div[style*="background-color: purple"],
    .intermediate-results div[style*="background-color: #6f42c1"],
    .intermediate-results div[style*="background-color: red"],
    .intermediate-results div[style*="background-color: #ff0000"],
    .intermediate-results div[style*="background-color: #007bff"] {
        color: white !important;
        font-weight: bold !important;
    }
    
    /* 文件显示区域保持黑色文字 */
    .intermediate-results div[style*="border: 2px solid"],
    .intermediate-results div[style*="border: 1px solid"],
    .intermediate-results div[style*="background: #f8f9fa"],
    .intermediate-results div[style*="background: #fff5f5"],
    .intermediate-results div[style*="background: #f0f8ff"],
    .intermediate-results div[style*="background: #fff8dc"],
    .intermediate-results div[style*="background: #f0fff0"] {
        color: #333 !important;
    }
    
    .intermediate-results div[style*="border: 2px solid"] *,
    .intermediate-results div[style*="border: 1px solid"] *,
    .intermediate-results div[style*="background: #f8f9fa"] *,
    .intermediate-results div[style*="background: #fff5f5"] *,
    .intermediate-results div[style*="background: #f0f8ff"] *,
    .intermediate-results div[style*="background: #fff8dc"] *,
    .intermediate-results div[style*="background: #f0fff0"] * {
        color: inherit !important;
    }
    
    /* 添加下载按钮样式 */
    .pdf-download-btn {
        background: #dc3545;
        color: white;
        padding: 8px 15px;
        text-decoration: none;
        border-radius: 4px;
        font-size: 14px;
        border: none;
        cursor: pointer;
        transition: background-color 0.3s ease;
    }
    
    .pdf-download-btn:hover {
        background: #c82333;
    }
    
    /* 移除output区域的高度限制 */
    .intermediate-results {
        max-height: none !important;
        height: auto !important;
        overflow: visible !important;
    }
    
    /* 移除所有output相关组件的高度限制 */
    [data-testid="tab-content"] {
        max-height: none !important;
        height: auto !important;
        overflow: visible !important;
    }
    
    /* 移除gr.HTML组件的高度限制 */
    .gr-html {
        max-height: none !important;
        height: auto !important;
        overflow: visible !important;
    }
    
    /* 移除gr.Textbox组件的高度限制 */
    .gr-textbox {
        max-height: none !important;
        height: auto !important;
        overflow: visible !important;
    }
    
    /* 确保Tab内容区域不受限制 */
    .tabs-content {
        max-height: none !important;
        height: auto !important;
        overflow: visible !important;
    }
    
    /* 移除所有可能的容器限制 */
    .gr-container {
        max-height: none !important;
        height: auto !important;
        overflow: visible !important;
    }
    
    /* 移除gr-block的高度限制 */
    .gr-block {
        max-height: none !important;
        height: auto !important;
        overflow: visible !important;
    }
    
    /* 移除gr-form的高度限制 */
    .gr-form {
        max-height: none !important;
        height: auto !important;
        overflow: visible !important;
    }
    
    /* 确保所有输出区域都能自由扩展 */
    [data-testid="output"] {
        max-height: none !important;
        height: auto !important;
        overflow: visible !important;
    }
    
    /* 移除accordion内容的高度限制 */
    .gr-accordion-content {
        max-height: none !important;
        height: auto !important;
        overflow: visible !important;
    }
"""
with gr.Blocks(title="🧬 Biomni AI Agent Demo", theme=gr.themes.Soft(), head=js_code, css=css_code) as demo:
    # gr.HTML(js_code)
    gr.Markdown("# 🧬 Biomni AI Agent Demo")
    gr.Markdown("Configure your LLM settings and ask Biomni to run biomedical tasks!")
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("## ⚙️ Agent Configuration")
            
            # LLM Configuration
            llm_model = gr.Textbox(
                label="Model Name",
                value="qwen3-coder-plus",
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
                value="https://dashscope.aliyuncs.com/compatible-mode/v1",
                placeholder="e.g., https://api.openai.com/v1 or http://localhost:8000/v1",
                info="Custom API endpoint URL. Leave empty for default."
            )
            
            api_key = gr.Textbox(
                label="API Key (Optional)",
                value="sk-879bc788fbeb4d97bfb041e4360fdde5",
                placeholder="Enter your API key",
                type="password",
                info="API key for the service. Can also be set via environment variables."
            )

            # data_path = gr.Textbox(
            #     label="Data Path",
            #     value="./data",
            #     placeholder="./data",
            #     info="Path where Biomni data will be stored"
            # ) 
          
            # 固定数据路径，用户不可修改
            data_path = gr.State("./data")
            
            ## 显示数据路径信息（只读）
            #gr.Markdown("**Data Path:** `./data` (固定路径)")
            
            verbose = gr.Checkbox(
                label="Enable Verbose Logging",
                value=True,
                info="Show detailed progress logs during execution (recommended for debugging)"
            )
            
            plain_output = gr.Checkbox(
                label="Plain Text Output",
                value=False,
                info="Output raw text without HTML formatting for intermediate results, execution logs, and token stats"
            )
            
            # Control buttons
            with gr.Row():
                create_btn = gr.Button("🚀 Create Agent", variant="primary")
                reset_btn = gr.Button("🔄 Reset Agent", variant="secondary")
            
            # Status display - 整合session id信息
            status_text = gr.Textbox(
                label="Status",
                value="No session assigned. Click 'Create Agent' to start.",
                interactive=False,
                lines=3
            )
            
            # Session ID state - 用于在组件间传递会话ID
            session_id_state = gr.State("")
            
            config_info = gr.Textbox(
                label="Current Configuration",
                interactive=False,
                lines=4
            )
            
            # Current data display
            data_list_display = gr.Textbox(
                label="Current Data in Agent",
                interactive=False,
                lines=6,
                placeholder="No data uploaded yet. Upload files to see them here."
            )
            
            # Upload status display
            upload_status = gr.Textbox(
                label="Upload Status",
                interactive=False,
                lines=2,
                placeholder="Upload status will appear here..."
            )
            
            # Link status display
            link_status = gr.Textbox(
                label="Link Status",
                interactive=False,
                lines=2,
                placeholder="Link status will appear here..."
            )
            
            # New files list display
            gr.Markdown("## 📁 New Files List")
            new_files_list = gr.Textbox(
                label="Generated Files",
                interactive=False,
                lines=10,
                placeholder="Newly generated files will appear here after execution...",
                container=True
            )
            
            # Button to refresh new files list
            refresh_files_btn = gr.Button("🔄 Refresh Files List", variant="secondary")
            

            
        with gr.Column(scale=3):
            with gr.Row():
                with gr.Column(scale=2):
                    gr.Markdown("## 💬 Chat with Biomni")
                    # Chat interface
                    question = gr.Textbox(
                        label="Your Question",
                        placeholder="Ask Biomni to run a biomedical task...",
                        lines=5
                    )
                    
                    # Control buttons
                    with gr.Row():
                        ask_btn = gr.Button("🤖 Ask Biomni", variant="primary", scale=2)
                        stop_btn = gr.Button("⏹️ Stop", variant="stop", scale=1, interactive=False)
                    
                with gr.Column(scale=1):
                    # Data upload section below chat
                    gr.Markdown("### 📁 Upload Data")
                    # File upload component
                    file_upload = gr.File(
                        label="Data Files",
                        file_count="multiple",
                        # file_types=[".csv", ".tsv", ".txt", ".json", ".xlsx", ".xls", ".parquet", ".h5", ".h5ad", ".fa", ".fq", ".fasta", ".fastq", ".bam", ".vcf", ".gff", ".pdf"],
                        height=70
                    )
                    # Description inputs for each file
                    file_descriptions = gr.Textbox(
                        label="File Descriptions (Optional)",
                        placeholder="One description per line",
                        lines=1
                    )
                    upload_btn = gr.Button("📤 Upload", variant="primary", interactive=False)
            
            # Multiple output areas
            with gr.Tab("Output"):
                intermediate_results = gr.HTML(
                    label="Output & Execution Steps",
                    value="<div style='text-align: center; color: #666; padding: 20px;'>Output will appear here...</div>",
                    elem_classes=["intermediate-results"],
                    container=False
                )
                # 添加生成链接按钮和文件链接
                with gr.Row():
                    download_btn = gr.Button("🔗 Generate Report Link", variant="primary", scale=1, interactive=False)
                    file_link = gr.File(
                        label="Download Report",
                        visible=False,
                        scale=1
                    )

            with gr.Tab("Token Statistics"):
                token_stats = gr.HTML(
                    label="Token Usage Statistics",
                    value="<div style='text-align: center; color: #666; padding: 20px;'>Token statistics will appear here after agent initialization...</div>",
                    container=False
                )
                
                # 添加token历史记录
                with gr.Accordion("📊 详细Token历史", open=False):
                    token_history = gr.HTML(
                        label="Token History",
                        value="<div style='text-align: center; color: #666; padding: 10px;'>No token history available yet...</div>",
                        container=False
                    )
                
                # 添加token管理按钮
                with gr.Row():
                    reset_tokens_btn = gr.Button("🔄 Reset Token Stats", variant="secondary", scale=1)
                    export_tokens_btn = gr.Button("📊 Export Token Data", variant="primary", scale=1)
                
                # 添加token数据下载链接
                token_file_link = gr.File(
                    label="📥 Download Token Data",
                    visible=False,
                    scale=1
                )

            with gr.Tab("Execution Log"):
                execution_log = gr.Textbox(
                    label="Detailed Execution Log",
                    lines=30,
                    interactive=False,
                    placeholder="Detailed execution logs will appear here...",
                    container=False
                )
            
            
            # 添加明显的间隔分隔线
            gr.Markdown("---")
            gr.Markdown("<div style='height: 20px;'></div>")  # 额外的垂直间距

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
    def create_agent_with_new_session(llm_model, source, base_url, api_key, data_path, verbose, plain_output):
        """创建agent时分配新的会话ID"""
        # 总是生成新的会话ID
        new_session_id = get_timestamp_session_id()
        print(f"[LOG] 创建agent时分配新会话ID: {new_session_id}")  # 添加日志
        result = create_agent(llm_model, source, base_url, api_key, data_path, verbose, new_session_id)
        # 更新status显示，整合session id信息
        status_text = f"✅ Agent created successfully!\nSession ID: {new_session_id}"
        return status_text, result[1], new_session_id
    
    # Data management event handlers
    def handle_upload(files, descriptions, session_id):
        """Handle file upload with descriptions."""
        if not files:
            return "❌ No files selected for upload.", ""
        
        # Split descriptions by newlines
        desc_list = descriptions.split('\n') if descriptions.strip() else []
        
        return upload_and_add_data(files, desc_list, session_id)
    
    def get_current_data_list(session_id):
        """Get current data list for display."""
        if not session_id or session_id == "":
            return "📊 No session assigned. Please create an agent first."
        
        session = session_manager.get_session(session_id)
        if not session or not session['agent']:
            return "📊 No agent found. Please create an agent first."
        
        try:
            custom_data = session['agent'].list_custom_data()
            if custom_data:
                data_list = "\n".join([f"• {name}: {desc}" for name, desc in custom_data])
                return f"📊 Custom Data in Agent:\n\n{data_list}"
            else:
                return "📊 No custom data found in agent."
        except Exception as e:
            return f"❌ Error listing data: {str(e)}"
    
    def get_result_files_list(session_id, plain: bool = False):
        """更新新增文件列表显示，包含文件大小"""
        print(f"[LOG] 进入 get_result_files_list: session_id={session_id}, plain={plain}")
        if not session_id or session_id == "":
            return "❌ No session assigned. Please create an agent first."
        
        try:
            new_files = get_new_files_list(session_id)
            if new_files:
                if plain:
                    # plain模式下显示文件路径和大小
                    file_info_list = []
                    for file_path in new_files:
                        try:
                            file_size = os.path.getsize(file_path)
                            file_info_list.append(f"{file_path} ({file_size})")
                        except Exception as e:
                            file_info_list.append(f"{file_path} (Unknown)")
                    print(f"[LOG] get_result_files_list: plain模式，共 {len(file_info_list)} 个文件")
                    return "\n".join(file_info_list)
                else:
                    # HTML模式下显示文件路径、大小和图标
                    file_info_list = []
                    total_size = 0
                    for file_path in new_files:
                        try:
                            file_size = os.path.getsize(file_path)
                            total_size += file_size
                            file_name = os.path.basename(file_path)
                            file_ext = os.path.splitext(file_path)[1].lower()
                            
                            # 根据文件类型选择图标
                            icon = get_file_icon(file_ext)
                            size_str = format_file_size(file_size)
                            file_info_list.append(f"{icon} {file_name} ({size_str})")
                        except Exception as e:
                            file_name = os.path.basename(file_path)
                            file_info_list.append(f"📁 {file_name} (大小未知)")
                    
                    # 格式化总大小
                    total_size_str = format_file_size(total_size)
                    
                    file_list = "\n".join(file_info_list)
                    print(f"[LOG] get_result_files_list: HTML模式，共 {len(new_files)} 个文件，总大小 {total_size_str}")
                    return f"🗂️ 发现 {len(new_files)} 个新增文件 (总大小: {total_size_str}):\n\n{file_list}"
            else:
                if plain:
                    print(f"[LOG] get_result_files_list: plain模式，无新增文件")
                    return ""
                else:
                    print(f"[LOG] get_result_files_list: HTML模式，无新增文件")
                    return "📂 暂无新增文件"
        except Exception as e:
            print(f"[LOG] get_result_files_list 失败: {e}")
            return f"❌ 获取文件列表失败: {str(e)}"
    
    def create_agent_and_update_data(llm_model, source, base_url, api_key, data_path, verbose, plain_output):
        """Create agent and update data list."""
        result = create_agent_with_new_session(llm_model, source, base_url, api_key, data_path, verbose, plain_output)
        data_list = get_current_data_list(result[2])  # result[2] is the new session_id
        return result[0], result[1], result[2], data_list
    
    # 开始执行时启用Stop按钮，禁用Ask按钮和Generate Link按钮
    def start_execution(question, session_id, data_path, plain_output):
        return gr.Button(interactive=False), gr.Button(interactive=True), gr.Button(interactive=False)
    
    # 停止执行时禁用Stop按钮，启用Ask按钮和Generate Link按钮
    def stop_execution_state():
        return gr.Button(interactive=True), gr.Button(interactive=False), gr.Button(interactive=True)
    
    # 任务完成时启用Generate Link按钮
    def task_completion_state():
        return gr.Button(interactive=True), gr.Button(interactive=False), gr.Button(interactive=True)
    
    # 更新token统计显示
    def update_token_display(session_id):
        """更新token统计显示"""
        if session_id:
            stats, history = get_token_statistics(session_id)
            return stats, history
        else:
            return "<div style='text-align: center; color: #666; padding: 20px;'>请先创建Agent以显示Token统计</div>", ""
    
    create_btn.click(
        fn=create_agent_and_update_data,
        inputs=[llm_model, source, base_url, api_key, data_path, verbose, plain_output],
        outputs=[status_text, config_info, session_id_state, data_list_display]
    ).then(
        fn=update_token_display,
        inputs=[session_id_state],
        outputs=[token_stats, token_history]
    ).then(
        fn=get_result_files_list,
        inputs=[session_id_state, plain_output],
        outputs=[new_files_list]
    )
    
    reset_btn.click(
        fn=reset_agent,
        inputs=[session_id_state],
        outputs=[status_text, config_info]
    )
    
    # Stop button
    stop_btn.click(
        fn=stop_execution,
        inputs=[session_id_state],
        outputs=[intermediate_results, execution_log]
    ).then(
        fn=stop_execution_state,
        outputs=[ask_btn, stop_btn, download_btn]
    )
    
    # Streaming ask function
    ask_btn.click(
        fn=start_execution,
        inputs=[question, session_id_state, data_path, plain_output],
        outputs=[ask_btn, stop_btn, download_btn]
    ).then(
        fn=reset_save_download_state,
        outputs=[download_btn, file_link, link_status]
    ).then(
        fn=ask_biomni_stream,
        inputs=[question, session_id_state, data_path, plain_output],
        outputs=[intermediate_results, execution_log, token_stats]
    ).then(
        fn=task_completion_state,
        outputs=[ask_btn, stop_btn, download_btn]
    ).then(
        fn=update_token_display,
        inputs=[session_id_state],
        outputs=[token_stats, token_history]
    ).then(
        fn=get_result_files_list,
        inputs=[session_id_state, plain_output],
        outputs=[new_files_list]
    )
    
    # Also allow Enter key to submit question
    question.submit(
        fn=start_execution,
        inputs=[question, session_id_state, data_path, plain_output],
        outputs=[ask_btn, stop_btn, download_btn]
    ).then(
        fn=reset_save_download_state,
        outputs=[download_btn, file_link, link_status]
    ).then(
        fn=ask_biomni_stream,
        inputs=[question, session_id_state, data_path, plain_output],
        outputs=[intermediate_results, execution_log, token_stats]
    ).then(
        fn=task_completion_state,
        outputs=[ask_btn, stop_btn, download_btn]
    ).then(
        fn=update_token_display,
        inputs=[session_id_state],
        outputs=[token_stats, token_history]
    ).then(
        fn=get_result_files_list,
        inputs=[session_id_state, plain_output],
        outputs=[new_files_list]
    )
    
    # 文件选择时启用上传按钮
    def enable_upload_button(files):
        return gr.Button(interactive=bool(files))
    
    file_upload.change(
        fn=enable_upload_button,
        inputs=[file_upload],
        outputs=[upload_btn]
    )
    
    upload_btn.click(
        fn=handle_upload,
        inputs=[file_upload, file_descriptions, session_id_state],
        outputs=[upload_status, data_list_display]
    ).then(
        fn=lambda: gr.Button(interactive=False),
        outputs=[upload_btn]
    )
    
    # Update data list when session changes
    session_id_state.change(
        fn=get_current_data_list,
        inputs=[session_id_state],
        outputs=[data_list_display]
    )
    
    # Token management buttons
    reset_tokens_btn.click(
        fn=reset_token_statistics,
        inputs=[session_id_state],
        outputs=[token_stats, token_history]
    )
    
    export_tokens_btn.click(
        fn=export_token_data,
        inputs=[session_id_state],
        outputs=[link_status, token_file_link]
    )
    
    # Refresh files button
    refresh_files_btn.click(
        fn=get_result_files_list,
        inputs=[session_id_state, plain_output],
        outputs=[new_files_list]
    )
    

    
    # Generate link button
    def handle_generate_link(intermediate_results, execution_log, session_id, question):
        """处理生成链接的请求，先保存再生成链接，一气呵成"""
        global save_download_state
        
        print(f"[LOG] 处理生成链接请求，session_id: {session_id}")
        
        # 检查内容是否变化
        current_hash = get_content_hash(intermediate_results, execution_log, question)
        
        # 第一步：先保存到本地（保存只能一次）
        print(f"[LOG] 开始保存结果到本地...")
        
        # 检查是否已经保存过相同内容
        if save_download_state['last_save_hash'] == current_hash:
            print(f"[LOG] 内容未变化，跳过保存")
            # 如果内容没变，直接返回已保存的文件路径
            if save_download_state['last_saved_file'] and os.path.exists(save_download_state['last_saved_file']):
                print(f"[LOG] 使用已保存的文件: {save_download_state['last_saved_file']}")
                return f"✅ 链接已生成", gr.File(value=save_download_state['last_saved_file'], visible=True), gr.Button(interactive=False)
            else:
                return f"❌ 未找到已保存的文件", gr.File(visible=False), gr.Button(interactive=False)
        else:
            # 执行保存
            save_result = save_current_results(intermediate_results, execution_log, session_id, question)
            if not save_result[0].startswith("✅"):
                return f"❌ 保存失败: {save_result[0]}", gr.File(visible=False), gr.Button(interactive=False)
            
            print(f"[LOG] 保存成功: {save_result[1]}")
            
            # 生成保存的文件路径
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if question:
                question_part = re.sub(r'[^\w\s-]', '', question[:20]).strip().replace(' ', '_')
                if question_part:
                    combined_filename = f"biomni_results_{timestamp}_{question_part}.html"
                else:
                    combined_filename = f"biomni_results_{timestamp}.html"
            else:
                combined_filename = f"biomni_results_{timestamp}.html"
            
            # 构建完整的文件路径
            if session_id:
                save_dir = get_session_results_dir(session_id)
                if save_dir is None:
                    return f"❌ 错误：无效的会话ID '{session_id}'", gr.File(visible=False), gr.Button(interactive=False)
            else:
                # save_dir = "./results"
                return f"❌ 错误：无效的会话ID '{session_id}'，无法生成链接", gr.File(visible=False), gr.Button(interactive=False)
            combined_path = os.path.join(save_dir, combined_filename)
            
            # 更新保存状态和文件路径
            save_download_state['last_save_hash'] = current_hash
            save_download_state['last_saved_file'] = combined_path  # 保存文件路径
        
        try:
            # 直接使用保存的文件路径
            if save_download_state['last_saved_file'] and os.path.exists(save_download_state['last_saved_file']):
                print(f"[LOG] 使用已保存的文件: {save_download_state['last_saved_file']}")
                return f"✅ 链接已生成", gr.File(value=save_download_state['last_saved_file'], visible=True), gr.Button(interactive=False)
            else:
                # 如果保存的文件不存在，重新生成
                print(f"[LOG] 保存的文件不存在，重新生成下载文件")
                
                # 生成文件名
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                if question:
                    question_part = re.sub(r'[^\w\s-]', '', question[:20]).strip().replace(' ', '_')
                    if question_part:
                        filename = f"biomni_results_{timestamp}_{question_part}.html"
                    else:
                        filename = f"biomni_results_{timestamp}.html"
                else:
                    filename = f"biomni_results_{timestamp}.html"
                
                # 创建包含HTML和日志的完整文档
                combined_content = generate_html_template(intermediate_results, execution_log, filename, "#333333")
                
                # 创建临时文件
                import tempfile
                temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
                temp_file.write(combined_content)
                temp_file.close()
                
                print(f"[LOG] 链接生成完成: {filename}")
                return f"✅ 链接已生成", gr.File(value=temp_file.name, visible=True), gr.Button(interactive=False)
            
        except Exception as e:
            error_message = f"❌ 链接生成失败: {str(e)}"
            print(f"[LOG] 链接生成失败: {e}")
            return error_message, gr.File(visible=False), gr.Button(interactive=False)
    
    download_btn.click(
        fn=handle_generate_link,
        inputs=[intermediate_results, execution_log, session_id_state, question],
        outputs=[link_status, file_link, download_btn]
    )

def format_file_size(file_size: int) -> str:
    """格式化文件大小显示"""
    if file_size < 1024:
        return f"{file_size} B"
    elif file_size < 1024 * 1024:
        return f"{file_size / 1024:.1f} KB"
    elif file_size < 1024 * 1024 * 1024:
        return f"{file_size / (1024 * 1024):.1f} MB"
    else:
        return f"{file_size / (1024 * 1024 * 1024):.1f} GB"

def get_file_icon(file_ext: str) -> str:
    """根据文件扩展名获取图标"""
    file_ext = file_ext.lower()
    image_exts = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.tiff', '.webp'}
    text_exts = {'.txt', '.log', '.md'}
    code_exts = {'.py', '.js', '.ts', '.html', '.css', '.json', '.xml', '.yaml', '.yml', '.sql', '.r', '.sh', '.bat'}
    data_exts = {'.csv', '.tsv', '.xlsx', '.xls', '.parquet'}
    pdf_exts = {'.pdf'}
    doc_exts = {'.docx', '.doc'}
    ppt_exts = {'.pptx', '.ppt'}
    archive_exts = {'.zip', '.rar', '.7z', '.tar', '.gz'}
    video_exts = {'.mp4', '.avi', '.mov', '.mkv'}
    audio_exts = {'.mp3', '.wav', '.flac', '.aac'}

    if file_ext in image_exts:
        return "📸"
    if file_ext in text_exts:
        return "📄"
    if file_ext in code_exts:
        return "💻"
    if file_ext in data_exts:
        return "📊"
    if file_ext in pdf_exts:
        return "📕"
    if file_ext in doc_exts:
        return "📝"
    if file_ext in ppt_exts:
        return "📋"
    if file_ext in archive_exts:
        return "🗜️"
    if file_ext in video_exts:
        return "🎬"
    if file_ext in audio_exts:
        return "🎵"
    return "📁"

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=10, max_size=100)
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False, allowed_paths=["/opt/biomni/results/"]) 