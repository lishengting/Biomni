# 文档处理工具描述
# 这些工具用于处理各种文档格式的转换和文本提取，基于LibreOffice

description = [
    {
        "description": "使用LibreOffice打开、读取并转换文档为指定格式。输入格式：docx/doc/odt/rtf/txt/html/xlsx/xls/ods/csv/pptx/ppt/odp/svg/wmf/emf/xml。输出格式：pdf/txt/html/rtf/docx/doc/odt/xml/xlsx/xls/ods/csv/pptx/ppt/odp/svg/png/jpg/gif/bmp。具体转换示例：doc→pdf, doc→txt, doc→html, docx→doc, xlsx→pdf, pptx→pdf等。基于LibreOffice开源办公套件，完全支持Microsoft Office格式(doc/xls/ppt)和OpenDocument格式",
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
        "description": "批量打开、读取并转换多个文档到指定格式，支持通配符模式匹配。输入格式：docx/doc/odt/rtf/txt/html/xlsx/xls/ods/csv/pptx/ppt/odp/svg/wmf/emf/xml。输出格式：pdf/txt/html/rtf/docx/doc/odt/xml/xlsx/xls/ods/csv/pptx/ppt/odp/svg/png/jpg/gif/bmp。批量转换示例：多个doc文件→pdf，多个xlsx文件→csv，多个pptx文件→html等",
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
        "description": "打开、读取文档并从其中提取纯文本内容，适用于内容分析和文本挖掘。支持格式：docx/doc/odt/rtf/txt/html/xlsx/xls/ods/csv/pptx/ppt/odp/svg/wmf/emf/xml。特别适用于从Word文档(doc/docx)、Excel表格(xlsx/xls)、PowerPoint演示文稿(pptx/ppt)中提取文本内容",
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
        "description": "打开、读取文档并快速转换为PDF格式。输入格式：docx/doc/odt/rtf/txt/html/xlsx/xls/ods/csv/pptx/ppt/odp/svg/wmf/emf/xml。转换示例：doc→pdf, docx→pdf, xlsx→pdf, pptx→pdf, odt→pdf等。特别适合将Microsoft Office文档(doc/xls/ppt)转换为PDF格式",
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
        "description": "打开、读取文档并快速转换为纯文本格式。输入格式：docx/doc/odt/rtf/txt/html/xlsx/xls/ods/csv/pptx/ppt/odp/svg/wmf/emf/xml。转换示例：doc→txt, docx→txt, xlsx→txt, pptx→txt, odt→txt等。特别适合从Microsoft Office文档(doc/xls/ppt)中提取纯文本内容",
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
        "description": "获取文档的基本信息，包括文件名、扩展名、文件大小、路径、读写权限以及是否为支持的格式。支持格式：docx/doc/odt/rtf/txt/html/htm/xlsx/xls/ods/csv/pptx/ppt/odp/svg/wmf/emf/xml等。特别适用于检查Microsoft Office文档(doc/xls/ppt)和OpenDocument格式文件的基本信息",
        "name": "get_document_info",
        "optional_parameters": [],
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
        "description": "检查LibreOffice工具的可用性和版本信息",
        "name": "check_libreoffice_availability",
        "optional_parameters": [],
        "required_parameters": [],
    }
]
