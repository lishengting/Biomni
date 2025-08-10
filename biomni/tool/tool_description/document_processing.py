# 文档处理工具描述
# 这些工具用于处理各种文档格式的转换和文本提取，基于LibreOffice

description = [
    {
        "description": "使用LibreOffice将文档转换为指定格式，支持文字处理(docx/doc/odt)、电子表格(xlsx/xls/ods)、演示文稿(pptx/ppt/odp)、图形格式(svg/wmf/emf)、Web格式(html/xml)等多种格式的相互转换",
        "name": "convert_document_libreoffice",
        "optional_parameters": [
            {
                "default": None,
                "description": "输出目录路径，默认与输入文件同目录",
                "name": "output_dir",
                "type": "str",
            },
            {
                "default": True,
                "description": "是否使用无头模式，默认True",
                "name": "headless",
                "type": "bool",
            }
        ],
        "required_parameters": [
            {
                "default": None,
                "description": "输入文档的完整路径",
                "name": "input_file",
                "type": "str",
            },
            {
                "default": None,
                "description": "目标格式，支持：文字处理(docx/doc/odt/txt/rtf)、电子表格(xlsx/xls/ods/csv)、演示文稿(pptx/ppt/odp)、图形格式(pdf/svg/png/jpg)、Web格式(html/xml)等",
                "name": "output_format",
                "type": "str",
            }
        ],
    },
    {
        "description": "批量转换多个文档到指定格式，支持通配符模式匹配",
        "name": "batch_convert_documents",
        "optional_parameters": [
            {
                "default": None,
                "description": "输出目录路径",
                "name": "output_dir",
                "type": "str",
            }
        ],
        "required_parameters": [
            {
                "default": None,
                "description": "输入文档路径列表",
                "name": "input_files",
                "type": "List[str]",
            },
            {
                "default": None,
                "description": "目标格式",
                "name": "output_format",
                "type": "str",
            }
        ],
    },
    {
        "description": "从文档中提取纯文本内容，适用于内容分析和文本挖掘",
        "name": "extract_text_from_document",
        "optional_parameters": [
            {
                "default": None,
                "description": "输出文本文件路径，可选",
                "name": "output_file",
                "type": "str",
            }
        ],
        "required_parameters": [
            {
                "default": None,
                "description": "输入文档的完整路径",
                "name": "input_file",
                "type": "str",
            }
        ],
    },
    {
        "description": "将文档快速转换为PDF格式",
        "name": "convert_to_pdf",
        "optional_parameters": [
            {
                "default": None,
                "description": "输出目录路径",
                "name": "output_dir",
                "type": "str",
            }
        ],
        "required_parameters": [
            {
                "default": None,
                "description": "输入文档的完整路径",
                "name": "input_file",
                "type": "str",
            }
        ],
    },
    {
        "description": "将文档快速转换为纯文本格式",
        "name": "convert_to_text",
        "optional_parameters": [
            {
                "default": None,
                "description": "输出目录路径",
                "name": "output_dir",
                "type": "str",
            }
        ],
        "required_parameters": [
            {
                "default": None,
                "description": "输入文档的完整路径",
                "name": "input_file",
                "type": "str",
            }
        ],
    },
    {
        "description": "获取支持的文档格式信息，包括输入和输出格式列表",
        "name": "get_supported_formats",
        "optional_parameters": [],
        "required_parameters": [],
    },
    {
        "description": "检查LibreOffice工具的可用性和版本信息",
        "name": "check_libreoffice_availability",
        "optional_parameters": [],
        "required_parameters": [],
    }
]
