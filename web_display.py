from flask import Flask, render_template, request, jsonify
import logging
from class_rag import VectorDbConnector
from class_rag import generate_vectors
from tools.pdf_split_zh import getParagraphs as get_paragraphs

import math

logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/data')
def display_data():
    # 初始化向量数据库连接
    from dotenv import load_dotenv
    import os
    from class_rag import generate_vectors
    
    load_dotenv()
    
    # 获取环境变量配置
    collection_name = os.getenv('CHROMADB_COLLECTION_NAME')
    if not collection_name:
        raise ValueError("CHROMADB_COLLECTION_NAME must be set in .env file")
    
    # 使用class_rag.py中的generate_vectors作为embedding函数
    def rag_embedding(text):
        return generate_vectors(text)
    
    vector_db = VectorDbConnector(
        collection_name=collection_name,
        embedding_fn=rag_embedding
    )

    # 获取请求参数
    page = int(request.args.get('page', 1))
    per_page = 5  # 固定每页5条

    # 获取全部数据（包含向量）
    results = vector_db.collection.get(include=['embeddings', 'documents', 'metadatas'])
    total = len(results['ids'])

    # 计算分页
    total_pages = math.ceil(total / per_page)
    start = (page - 1) * per_page
    end = start + per_page

    # 准备页面数据
    page_data = {
        'ids': results['ids'][start:end],
        'documents': results['documents'][start:end],
        'metadatas': results['metadatas'][start:end] if results['metadatas'] else None,
        'embeddings': results['embeddings'][start:end] if results['embeddings'] else None
    }

    return render_template(
        'data_display.html',
        data=page_data,
        page=page,
        total_pages=total_pages
    )

@app.route('/vectorize_data', methods=['POST'])
def vectorize_data():
    from dotenv import load_dotenv
    import os
    from class_rag import generate_vectors
    
    load_dotenv()
    collection_name = os.getenv('CHROMADB_COLLECTION_NAME')
    if not collection_name:
        return jsonify({'success': False, 'message': "CHROMADB_COLLECTION_NAME must be set in .env file"}), 500

    def rag_embedding(text):
        return generate_vectors(text)
    
    vector_db = VectorDbConnector(
        collection_name=collection_name,
        embedding_fn=rag_embedding
    )

    try:
        paragraphs = get_paragraphs()
        result = vector_db.add_documents(paragraphs)
        if result:
            return jsonify({'success': True, 'message': '数据已成功转为向量存储'})
        else:
            return jsonify({'success': False, 'message': '转为向量存储失败'}), 500
    except Exception as e:
        logger.error(f"转为向量存储时出错: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/search', methods=['POST'])
def search_data():
    from dotenv import load_dotenv
    import os
    from class_rag import generate_vectors
    
    load_dotenv()
    collection_name = os.getenv('CHROMADB_COLLECTION_NAME')
    if not collection_name:
        return jsonify({'success': False, 'message': "CHROMADB_COLLECTION_NAME must be set in .env file"}), 500

    def rag_embedding(text):
        return generate_vectors(text)
    
    vector_db = VectorDbConnector(
        collection_name=collection_name,
        embedding_fn=rag_embedding
    )

    data = request.get_json()
    query_text = data.get('query', '').strip()
    limit = int(data.get('limit', 5))

    if not query_text:
        return jsonify({'success': False, 'message': '查询文本不能为空'}), 400

    try:
        # 确保查询文本已正确编码
        if not isinstance(query_text, str):
            raise ValueError("查询文本必须是字符串")
            
        # 查询向量数据库
        # 生成并验证查询向量
        query_embedding = rag_embedding(query_text)
        if not query_embedding or not isinstance(query_embedding, list):
            raise ValueError("生成查询向量失败")
            
        # 确保query_embedding是二维数组
        if isinstance(query_embedding[0], list):
            query_embedding = query_embedding[0]  # 取第一层嵌套
            
        results = vector_db.collection.query(
            query_embeddings=[query_embedding] if not isinstance(query_embedding[0], list) else query_embedding,
            n_results=limit,
            include=['documents', 'metadatas', 'embeddings', 'distances']
        )

        # 验证查询结果格式
        if not results or 'ids' not in results or not results['ids'][0]:
            return jsonify({'success': False, 'message': '未找到匹配结果'})

        # 格式化结果
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                'id': results['ids'][0][i],
                'document': results['documents'][0][i],
                'metadata': results['metadatas'][0][i] if results['metadatas'] else None,
                'embedding': results['embeddings'][0][i] if results['embeddings'] else None,
                'distance': results['distances'][0][i] if results['distances'] else None
            })

        return jsonify({
            'success': True,
            'results': formatted_results
        })

    except Exception as e:
        logger.error(f"查询失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': '查询失败，请检查查询内容或稍后再试'
        }), 500

@app.route('/delete_data', methods=['POST'])
def delete_data():
    from dotenv import load_dotenv
    import os
    # from class_rag import generate_vectors
    
    load_dotenv()
    collection_name = os.getenv('CHROMADB_COLLECTION_NAME')
    if not collection_name:
        return jsonify({'success': False, 'message': "CHROMADB_COLLECTION_NAME must be set in .env file"}), 500

    def rag_embedding(text):
        return generate_vectors(text)
    
    vector_db = VectorDbConnector(
        collection_name=collection_name,
        embedding_fn=rag_embedding
    )

    data = request.get_json()
    ids = data.get('ids', [])
    try:
        # 判断删除模式
        if ids == "ALL":
            # 全部删除逻辑 - 删除并重建集合
            try:
                collection_name = vector_db.collection.name
                metadata = vector_db.collection.metadata
                embedding_fn = vector_db.embedding_fn
                
                # 删除原集合
                vector_db.client.delete_collection(name=collection_name)
                # 重建集合
                vector_db.collection = vector_db.client.create_collection(
                    name=collection_name,
                    metadata=metadata,
                    embedding_function=embedding_fn
                )
                logger.info("全部数据删除成功(集合已重建)")
                return jsonify({'success': True, 'message': '全部数据删除成功'})
            except Exception as e:
                logger.error(f"全部删除失败: {str(e)}")
                return jsonify({'success': False, 'message': f'全部删除失败: {str(e)}'}), 500
        elif isinstance(ids, list) and len(ids) > 0:
            # 单条删除逻辑
            vector_db.collection.delete(ids=ids)
            remaining = vector_db.collection.get(ids=ids)
            if len(remaining['ids']) == 0:
                logger.info(f"ID为 {ids} 的数据删除成功")
                return jsonify({'success': True, 'message': '数据删除成功'})
            else:
                logger.error(f"删除验证失败，剩余ID数量: {len(remaining['ids'])}")
                return jsonify({'success': False, 'message': '数据删除不完整'}), 500
        else:
            logger.error("无效的删除参数")
            return jsonify({'success': False, 'message': '无效的删除参数'}), 400
            
    except Exception as e:
        logger.error(f"删除数据时出错: {str(e)}")
        return jsonify({'success': False, 'message': f'删除过程中发生错误: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(port=5001)  # 使用不同端口避免冲突
