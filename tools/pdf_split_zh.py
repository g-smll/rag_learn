import re
import pdfplumber
import logging

INPUT_PDF = "./doc/健康档案.pdf"

# 配置日志格式和级别
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pdf_processor.log'),
        logging.StreamHandler()
    ]
)


def split_health_records_by_person(content):
    """按个人分段健康档案内容，精确匹配独立行的'健康档案'"""
    # 使用正则表达式匹配独立行的"健康档案"（前后无其他内容）
    pattern = re.compile(r'^\s*健康档案\s*$', re.MULTILINE)
    matches = list(pattern.finditer(content))

    if len(matches) < 3:
        # 尝试更宽松的匹配作为备选
        fallback_pattern = re.compile(r'健康档案')
        matches = list(fallback_pattern.finditer(content))
        if len(matches) < 3:
            raise ValueError(f"文档中未找到足够的健康档案记录，只找到 {len(matches)} 处")

    start_indices = [m.start() for m in matches]

    # 提取三个人的档案内容
    records = []
    for i in range(len(start_indices)):
        start = start_indices[i]
        # 确定当前档案的结束位置（下一个档案的开始或文档结尾）
        end = start_indices[i + 1] if i < len(start_indices) - 1 else len(content)
        records.append(content[start:end].strip())

    return records


def getParagraphs(pdf_path=INPUT_PDF, parser_type='pdfplumber', page_numbers=None, min_line_length=1, chunk_size=800, overlap_size=200):
    """
    解析PDF文件并处理内容，支持多种解析策略
    
    参数:
        pdf_path: PDF文件路径
        parser_type: 解析器类型，可选'pdfplumber'或'pdfminer'，默认为'pdfplumber'
        page_numbers: 指定页码列表(仅pdfminer有效)，None表示所有页面
        min_line_length: 最小行长度(仅pdfminer有效)
        chunk_size: 文本块大小(仅pdfminer有效)
        overlap_size: 重叠大小(仅pdfminer有效)
    返回:
        包含处理后的文本块列表或健康档案列表
    """
    if parser_type == 'pdfplumber':
        full_text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                # 添加分页标记（保留原始结构）
                full_text += f"===== Page {i + 1} =====\n{text}\n\n"
        return split_health_records_by_person(full_text)
        
    elif parser_type == 'pdfminer':
        from pdfminer.high_level import extract_pages
        from pdfminer.layout import LTTextContainer
        
        # 提取文本段落
        paragraphs = []
        buffer = ''
        full_text = ''
        for i, page_layout in enumerate(extract_pages(pdf_path)):
            if page_numbers is not None and i not in page_numbers:
                continue
            for element in page_layout:
                if isinstance(element, LTTextContainer):
                    full_text += element.get_text() + '\n'
        
        # 组织成段落
        lines = full_text.split('\n')
        for text in lines:
            if len(text) >= min_line_length:
                buffer += (' '+text) if not text.endswith('-') else text.strip('-')
            elif buffer:
                paragraphs.append(buffer)
                buffer = ''
        if buffer:
            paragraphs.append(buffer)
            
        # 分割成带重叠的文本块
        def sent_tokenize(input_string):
            sentences = re.split(r'(?<=[。！？；?!])', input_string)
            return [sentence for sentence in sentences if sentence.strip()]
            
        sentences = [s.strip() for p in paragraphs for s in sent_tokenize(p)]
        chunks = []
        i = 0
        while i < len(sentences):
            chunk = sentences[i]
            overlap = ''
            prev = i - 1
            while prev >= 0 and len(sentences[prev])+len(overlap) <= overlap_size:
                overlap = sentences[prev] + ' ' + overlap
                prev -= 1
            chunk = overlap+chunk
            next = i + 1
            while next < len(sentences) and len(sentences[next])+len(chunk) <= chunk_size:
                chunk = chunk + ' ' + sentences[next]
                next += 1
            chunks.append(chunk)
            i = next
            
        return chunks
        
    else:
        raise ValueError(f"不支持的解析器类型: {parser_type}")


def is_standalone_health_record(line):
    """检查一行是否只包含'健康档案'（无其他内容）"""
    cleaned = line.strip()
    return cleaned == "健康档案" or cleaned == "健康档案："


# 增强版解析函数，处理更复杂的边界情况
def enhanced_parse_pdf(pdf_path):
    """增强版PDF解析，精确处理每行内容"""
    records = []
    current_record = []
    found_record = False

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            for line in text.split('\n'):
                # 检查是否是独立的健康档案标题
                if is_standalone_health_record(line):
                    if current_record and found_record:
                        # 保存前一个档案
                        records.append("\n".join(current_record))
                        current_record = []
                    found_record = True

                # 添加到当前档案
                current_record.append(line)

    # 添加最后一个档案
    if current_record and found_record:
        records.append("\n".join(current_record))

    return records


# 使用示例
if __name__ == "__main__":
    pdf_path = "../doc/健康档案.pdf"  # 替换为实际PDF文件路径

    try:
        # 两种解析方式选择：
        # 方式1：快速解析（适用于格式规范的PDF）
        health_records = getParagraphs(pdf_path)

        # 方式2：增强解析（适用于格式不规范的PDF）
        # health_records = enhanced_parse_pdf(pdf_path)

        logging.info(f"找到 {len(health_records)} 份健康档案")

        for i, record in enumerate(health_records):
            logging.info(f"\n{'=' * 50}")
            logging.info(f"=== 第{i + 1}份健康档案（共{len(record)}字符）===")
            logging.info(f"{'-' * 50}")

            # 提取前两行作为标题预览
            first_lines = "\n".join(record.split('\n')[:2])
            logging.info(first_lines)
            logging.info(record)  # 完整记录使用debug级别

            # 保存完整档案
            # with open(f"health_record_{i + 1}.txt", "w", encoding="utf-8") as f:
                 #f.write(record)

            # logging.info(f"{'-' * 50}")
            #logging.info(f"档案已保存至: health_record_{i + 1}.txt")

    except FileNotFoundError:
        logging.error(f"错误：文件 {pdf_path} 不存在")
    except ValueError as e:
        logging.error(f"处理错误: {e}")
    except Exception as e:
        logging.error(f"未知错误: {str(e)}")