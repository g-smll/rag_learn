import uuid

import requests
import chromadb
import json
from tools import pdfSplitTest_Ch
import logging

TEXT_LANGUAGE = "Chinese"
INPUT_PDF = "doc/健康档案.pdf"
PAGE_NUMBERS = None

CHROMADB_DIRECTORY = "chromaDB"
CHROMADB_COLLECTION_NAME = "demo001"

SILICON_FLOW_API_BASE = "https://api.siliconflow.cn/v1/embeddings"
SILICON_FLOW_EMBEDDING_API_KEY = "Bearer sk-xkmpyoaangdwwjirbwajaifivchxeqarueggkgaafnauikkd"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
def get_embeddings(texts):
    payload = {
        "model": "BAAI/bge-m3",
        "input": texts,
        "encoding_format": "float"
    }
    headers = {
        "Authorization": SILICON_FLOW_EMBEDDING_API_KEY,
        "Content-Type": "application/json"
    }
    try:
        response = requests.request("POST", SILICON_FLOW_API_BASE, json=payload, headers=headers)
        data_dict = json.loads(response.text)
        data = data_dict.get("data", [])
        return [x.get("embedding") for x in data]
    except Exception as e:
        print('向量化异常： {e}')
        return []


def generate_vectors(data, max_batch_size=25):
    results = []
    for i in range(0, len(data), max_batch_size):
        batch = data[i:i + max_batch_size]
        # 调用向量生成get_embeddings方法  根据调用的API不同进行选择
        response = get_embeddings(batch)
        results.extend(response)
    return results

class VectorDbConnector:
    def __init__(self, collection_name, embedding_fn):
        global CHROMADB_DIRECTORY
        chroma_client = chromadb.PersistentClient(path=CHROMADB_DIRECTORY)
        self.collection = chroma_client.get_or_create_collection(name=collection_name)
        self.embedding_fn = embedding_fn
        self.client = chroma_client

    def add_documents(self, documents):
        try:
            embeddings = self.embedding_fn(documents)
            if not embeddings or len(embeddings) == 0:
                logger.warning("未生成有效的向量，跳过添加。")
                return False
            self.collection.add(
                embeddings=embeddings,
                documents=documents,
                ids=[str(uuid.uuid4()) for _ in range(len(documents))]
            )
            return True
        except Exception as e:
            logger.error(f"添加文档失败: {str(e)}")
            return False

    def search(self, query, top_n):
        try:
            result = self.collection.query(
                query_embeddings=self.embedding_fn(query),
                n_results=top_n
            )
            return result

        except Exception as e:
            print('')
            return []

    def del_documents(self, ids):
        """
        从向量数据库中删除文档
        
        参数:
            ids: 可以是以下形式:
                - 'ALL' (删除全部文档)
                - 单个文档ID字符串
                - 文档ID列表
                
        返回:
            True 删除成功
            False 删除失败
        """
        try:
            if not hasattr(self, 'collection') or self.collection is None:
                logger.error("数据库连接未初始化或已断开")
                return False

            if ids == 'ALL':
                # 清空全部向量数据
                try:
                    count = len(self.collection.get()['ids'])
                    self.collection.delete(where={})
                    logger.warning(f"已清空全部向量数据，共 {count} 个文档")
                    return True
                except Exception as e:
                    logger.error(f"清空全部数据失败: {str(e)}")
                    return False
                
            if isinstance(ids, str):
                # 处理单个ID字符串
                ids = [ids]
                
            if not isinstance(ids, list) or len(ids) == 0:
                logger.error("无效的ID参数，必须是非空列表或字符串")
                return False
                
            try:
                result = self.collection.delete(ids=ids)
                deleted_count = len(result.get('ids', []))
                if deleted_count > 0:
                    logger.info(f"成功删除 {deleted_count} 个文档")
                else:
                    logger.warning("未找到匹配的文档进行删除")
                return deleted_count > 0
            except Exception as e:
                logger.error(f"删除文档失败: {str(e)}")
                return False
            
        except Exception as e:
            logger.error(f"删除文档失败: {str(e)}")
            return 0

def get_paragraphs():
    global TEXT_LANGUAGE, CHROMADB_COLLECTION_NAME, INPUT_PDF, PAGE_NUMBERS
    if TEXT_LANGUAGE == 'Chinese':
        paragraphs = pdfSplitTest_Ch.getParagraphs(
            filename=INPUT_PDF,
            page_numbers=PAGE_NUMBERS,
            min_line_length=1
        )
        return paragraphs

def vectorStoreSave():
    global TEXT_LANGUAGE, CHROMADB_COLLECTION_NAME, INPUT_PDF, PAGE_NUMBERS
    if TEXT_LANGUAGE == 'Chinese':
        paragraphs = pdfSplitTest_Ch.getParagraphs(
            filename=INPUT_PDF,
            page_numbers=PAGE_NUMBERS,
            min_line_length=1
        )
        vector_db = VectorDbConnector(CHROMADB_COLLECTION_NAME, generate_vectors)
        vector_db.add_documents(paragraphs)
        # user_query = "张三九的基本信息是什么"
        # search_result = vector_db.search(user_query, 5)
        # print(search_result)

def vectorSearch():
    vector_db = VectorDbConnector(CHROMADB_COLLECTION_NAME, generate_vectors)
    user_query = "李四六的基本信息是什么"
    search_result= vector_db.search(user_query, 2)
    return search_result


if __name__ == '__main__':
    vectorStoreSave()
    # embedding = get_embeddings('你是谁？')
    # result = vectorSearch()
    # logger.info(f"检索向量数据库的结果: {result}")