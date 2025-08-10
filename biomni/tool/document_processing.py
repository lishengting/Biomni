import logging
import os
import subprocess
from pathlib import Path
from typing import List, Optional

# 配置日志
logger = logging.getLogger(__name__)

# 全局调试标志
DEBUG_MODE = True


def set_debug_mode(debug: bool):
    """设置调试模式用于日志记录。
    
    Args:
        debug (bool): True启用调试日志，False禁用
    """
    global DEBUG_MODE
    DEBUG_MODE = debug


def convert_document_libreoffice(
    input_file: str, 
    output_format: str, 
    output_dir: Optional[str] = None,
    headless: bool = True
) -> dict:
    """使用LibreOffice转换文档格式。
    
    LibreOffice是一个功能强大的开源办公套件，支持多种文档格式的相互转换：
    - 文字处理：docx, doc, odt, rtf, txt, html
    - 电子表格：xlsx, xls, ods, csv
    - 演示文稿：pptx, ppt, odp
    - 图形格式：svg, wmf, emf, png, jpg, gif, bmp
    - 其他格式：xml, pdf等
    
    Args:
        input_file (str): 输入文件路径
        output_format (str): 输出格式 (txt, pdf, html, rtf, docx, xlsx, pptx等)
        output_dir (str, optional): 输出目录，默认与输入文件同目录
        headless (bool): 是否使用无头模式，默认True
        
    Returns:
        dict: 包含转换结果和日志的字典
    """
    logger.info(f"开始转换文档: {input_file} -> {output_format}")
    
    try:
        # 检查输入文件是否存在
        if not os.path.exists(input_file):
            error_msg = f"输入文件不存在: {input_file}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "log": [error_msg]}
        
        # 设置输出目录
        if output_dir is None:
            output_dir = os.path.dirname(input_file) or "."
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 构建LibreOffice命令
        cmd = ["libreoffice"]
        if headless:
            cmd.append("--headless")
        
        cmd.extend([
            "--convert-to", output_format,
            "--outdir", output_dir,
            input_file
        ])
        
        if DEBUG_MODE:
            logger.debug(f"执行命令: {' '.join(cmd)}")
        
        # 执行转换
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=300  # 5分钟超时
        )
        
        if result.returncode == 0:
            # 查找输出文件
            input_name = Path(input_file).stem
            output_file = os.path.join(output_dir, f"{input_name}.{output_format}")
            
            if os.path.exists(output_file):
                success_msg = f"文档转换成功: {output_file}"
                logger.info(success_msg)
                return {
                    "success": True,
                    "output_file": output_file,
                    "log": [success_msg]
                }
            else:
                error_msg = f"转换完成但输出文件未找到: {output_file}"
                logger.warning(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "log": [error_msg]
                }
        else:
            error_msg = f"LibreOffice转换失败: {result.stderr}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "log": [error_msg]
            }
            
    except subprocess.TimeoutExpired:
        error_msg = "文档转换超时"
        logger.error(error_msg)
        return {"success": False, "error": error_msg, "log": [error_msg]}
    except Exception as e:
        error_msg = f"文档转换过程中发生错误: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg, "log": [error_msg]}


def batch_convert_documents(
    input_files: List[str], 
    output_format: str, 
    output_dir: Optional[str] = None
) -> dict:
    """批量转换多个文档到指定格式。
    
    Args:
        input_files (List[str]): 输入文件路径列表
        output_format (str): 输出格式
        output_dir (str, optional): 输出目录
        
    Returns:
        dict: 包含批量转换结果的字典
    """
    logger.info(f"开始批量转换 {len(input_files)} 个文档到 {output_format} 格式")
    
    results = []
    successful = 0
    failed = 0
    
    for input_file in input_files:
        result = convert_document_libreoffice(input_file, output_format, output_dir)
        
        results.append({
            "input_file": input_file,
            "result": result
        })
        
        if result["success"]:
            successful += 1
        else:
            failed += 1
    
    summary = f"批量转换完成: 成功 {successful} 个，失败 {failed} 个"
    logger.info(summary)
    
    return {
        "success": failed == 0,
        "total_files": len(input_files),
        "successful": successful,
        "failed": failed,
        "results": results,
        "summary": summary
    }


def extract_text_from_document(input_file: str, output_file: Optional[str] = None) -> dict:
    """从文档中提取纯文本。
    
    Args:
        input_file (str): 输入文档路径
        output_file (str, optional): 输出文本文件路径
        
    Returns:
        dict: 包含文本提取结果的字典
    """
    logger.info(f"开始从文档提取文本: {input_file}")
    
    try:
        # 使用LibreOffice转换为txt格式
        result = convert_document_libreoffice(input_file, "txt")
        
        if result["success"]:
            # 读取提取的文本
            with open(result["output_file"], 'r', encoding='utf-8') as f:
                text_content = f.read()
            
            # 如果指定了输出文件，复制内容
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(text_content)
                result["custom_output_file"] = output_file
            
            result["text_content"] = text_content
            result["text_length"] = len(text_content)
            
            success_msg = f"文本提取成功，长度: {len(text_content)} 字符"
            logger.info(success_msg)
            result["log"].append(success_msg)
            
            return result
        else:
            return result
            
    except Exception as e:
        error_msg = f"文本提取过程中发生错误: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg, "log": [error_msg]}


def convert_to_pdf(input_file: str, output_dir: Optional[str] = None) -> dict:
    """将文档转换为PDF格式。
    
    Args:
        input_file (str): 输入文档路径
        output_dir (str, optional): 输出目录
        
    Returns:
        dict: 包含转换结果的字典
    """
    logger.info(f"开始转换文档为PDF: {input_file}")
    return convert_document_libreoffice(input_file, "pdf", output_dir)


def convert_to_text(input_file: str, output_dir: Optional[str] = None) -> dict:
    """将文档转换为纯文本格式。
    
    Args:
        input_file (str): 输入文档路径
        output_dir (str, optional): 输出目录
        
    Returns:
        dict: 包含转换结果的字典
    """
    logger.info(f"开始转换文档为文本: {input_file}")
    return convert_document_libreoffice(input_file, "txt", output_dir)


def convert_to_html(input_file: str, output_dir: Optional[str] = None) -> dict:
    """将文档转换为HTML格式。
    
    Args:
        input_file (str): 输入文档路径
        output_dir (str, optional): 输出目录
        
    Returns:
        dict: 包含转换结果的字典
    """
    logger.info(f"开始转换文档为HTML: {input_file}")
    return convert_document_libreoffice(input_file, "html", output_dir)





def check_libreoffice_availability() -> dict:
    """检查LibreOffice工具的可用性。
    
    Returns:
        dict: 包含LibreOffice可用性状态的字典
    """
    logger.info("检查LibreOffice工具可用性")
    
    try:
        result = subprocess.run(
            ["libreoffice", "--version"], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            status_info = {
                "available": True,
                "version": version,
                "status": "可用"
            }
            logger.info(f"LibreOffice可用: {version}")
            return status_info
        else:
            error_msg = f"LibreOffice不可用: {result.stderr}"
            logger.warning(error_msg)
            return {
                "available": False,
                "error": error_msg,
                "status": "不可用"
            }
    except Exception as e:
        error_msg = f"检查LibreOffice时发生错误: {str(e)}"
        logger.error(error_msg)
        return {
            "available": False,
            "error": str(e),
            "status": "检查失败"
        }


def get_document_info(input_file: str) -> dict:
    """获取文档的基本信息。
    
    Args:
        input_file (str): 输入文档路径
        
    Returns:
        dict: 包含文档信息的字典
    """
    logger.info(f"获取文档信息: {input_file}")
    
    try:
        if not os.path.exists(input_file):
            error_msg = f"文件不存在: {input_file}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        
        file_path = Path(input_file)
        file_info = {
            "success": True,
            "file_name": file_path.name,
            "file_extension": file_path.suffix.lower(),
            "file_size": os.path.getsize(input_file),
            "file_path": str(file_path.absolute()),
            "is_readable": os.access(input_file, os.R_OK),
            "is_writable": os.access(input_file, os.W_OK)
        }
        
        # 检查是否为支持的格式
        supported_formats = ["docx", "doc", "odt", "rtf", "txt", "html", "htm", "xlsx", "xls", "ods", "csv", "pptx", "ppt", "odp", "svg", "wmf", "emf", "xml", "uot", "uof", "fodt", "fods", "fodp"]
        file_info["is_supported"] = file_info["file_extension"][1:] in supported_formats
        
        logger.info(f"文档信息获取成功: {file_info['file_name']}")
        return file_info
        
    except Exception as e:
        error_msg = f"获取文档信息时发生错误: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}
