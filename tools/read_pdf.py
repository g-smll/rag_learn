import PyPDF2
import logging
import re

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def read_pdf(file_path):
    try:
        with open(file_path, 'rb') as file:
            # 创建PDF阅读器对象
            pdf_reader = PyPDF2.PdfReader(file)
            
            # 获取页数
            num_pages = len(pdf_reader.pages)
            logger.info(f"PDF文件共有 {num_pages} 页")
            
            # 读取所有页面的文本
            text = ""
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                text += page.extract_text()
            
            return text
    except Exception as e:
        logger.error(f"读取PDF文件时发生错误: {str(e)}")
        return None

def count_person_records(text):
    # 用正则表达式匹配"健康档案"或"患者姓名"开头的段落，并统计个数
    # 这里用"健康档案"或"患者姓名"作为分隔符，分割后去除空段，得到每个人的健康信息段落数
    parts = re.split(r'(?:健康档案|患者姓名)', text)
    # 去除空段，并统计个数
    person_records = [part.strip() for part in parts if part.strip()]
    return len(person_records)

def extract_names(text):
    # 用正则表达式匹配"健康档案"或"患者姓名"后的人名（例如"张三九"或"李四六"）
    # 这里假设人名是2-3个汉字，且后面跟着"，男"或"，女"或"，女性"等
    pattern = r'(?:健康档案|患者姓名)[为是]?([一-龥]{2,3})[，,]\s*(?:男|女)'
    names = re.findall(pattern, text)
    return names

def process_health_records(file_path):
    """
    处理健康档案文件，返回按人分段的信息
    """
    # 读取PDF文件
    text = read_pdf(file_path)
    if not text:
        return None
    
    # 按人分段
    person_records = split_by_person(text)
    
    # 打印每个人的信息摘要
    for idx, info in enumerate(person_records):
        logger.info(f"\n=== 第{idx+1}个人的健康信息摘要 ===")
        # 提取基本信息
        basic_info = re.search(r'(?:基本信息|患者姓名).*?(?=二、|$)', info, re.DOTALL)
        if basic_info:
            logger.info(f"基本信息：{basic_info.group(0).strip()}")
        # 提取医疗历史
        medical_history = re.search(r'医疗历史.*?(?=三、|$)', info, re.DOTALL)
        if medical_history:
            logger.info(f"主要病史：{medical_history.group(0).strip()}")
    
    return person_records

if __name__ == "__main__":
    pdf_path = "doc/健康档案.pdf"
    text = read_pdf(pdf_path)
    if text:
        count = count_person_records(text)
        names = extract_names(text)
        logger.info(f"健康档案.pdf中共有 {count} 人的健康信息，分别是：{', '.join(names)}")
    else:
        logger.info("未读取到有效内容。") 