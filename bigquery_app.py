from typing import Any, Dict
import uuid
from flask import Flask, abort, request, jsonify
import os
from google.cloud import bigquery
from google.api_core.exceptions import NotFound

from google_client import bigquery_client as client

from dotenv import load_dotenv

load_dotenv()

print(f"--- SCRIPT TOP LEVEL ---")
print(f"WERKZEUG_RUN_MAIN: {os.environ.get('WERKZEUG_RUN_MAIN')}")
print(f"FLASK_DEBUG env: {os.environ.get('FLASK_DEBUG')}")
print(f"FLASK_ENV env: {os.environ.get('FLASK_ENV')}")


GOOGLE_PROJECT_NAME = os.environ.get("GOOGLE_PROJECT_NAME")
BIGQUERY_DATASET_ID = os.environ.get("BIGQUERY_DATASET_ID")
BIGQUERY_TABLE_NAME = os.environ.get("BIGQUERY_TABLE_NAME")

TABLE_ID = f"{GOOGLE_PROJECT_NAME}.{BIGQUERY_DATASET_ID}.{BIGQUERY_TABLE_NAME}"

app = Flask(__name__)


@app.route('/documents', methods=['POST'])
def create_document():
    if not client:
        return jsonify({"error": "BigQuery client 未初始化"}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "请求体中缺少 JSON 数据"}), 400

    # 如果caller提供了idx就直接使用
    if 'idx' in data and data.get('idx'):
        user_provided_idx = data['idx']
        check_query = f"SELECT COUNT(1) FROM `{TABLE_ID}` WHERE idx = @idx"
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter(
                "idx", "STRING", user_provided_idx)]
        )
        try:
            results = list(client.query(
                check_query, job_config=job_config).result())
            if results[0][0] > 0:
                return jsonify({"error": f"文档 idx '{user_provided_idx}' 已存在"}), 409
        except Exception as e:
            return jsonify({"error": f"检查 idx 时出错: {e}"}), 500
    else:
        data['idx'] = str(uuid.uuid4())

    # TODO: 检查其他必需字段，后面调整为实际项目中需要的字段
    required_fields = ['title', 'type', 'text']
    if not all(field in data for field in required_fields):
        missing_fields = [
            field for field in required_fields if field not in data]
        return jsonify({"error": f"缺少必需字段: {', '.join(missing_fields)}"}), 400

    # 确保所有字段都存在，对于可选字段，如果不存在则设为 NULL
    fields_order = ['idx', 'title', 'type',
                    'publish_time', 'author', 'url', 'text']
    values_tuple = tuple(data.get(field) for field in fields_order)

    query = f"""
        INSERT INTO `{TABLE_ID}` (idx, title, type, publish_time, author, url, text)
        VALUES {values_tuple}
    """

    try:
        query_job = client.query(query)
        query_job.result()  # 等待作业完成

        if query_job.errors:
            print(f"插入数据时出错: {query_job.errors}")
            return jsonify({"error": "插入数据到 BigQuery 失败", "details": query_job.errors}), 500

        print(f"成功使用 DML INSERT 插入新文档，idx: {data['idx']}")
        return jsonify(data), 201

    except Exception as e:
        print(f"插入数据时出错: {e}")
        return jsonify({"error": f"插入数据到 BigQuery 失败: {e}"}), 500


@app.route('/documents', methods=['GET'])
def get_all_documents():
    if not client:
        return jsonify({"error": "BigQuery client 未初始化"}), 500

    query = f"SELECT * FROM `{TABLE_ID}`"
    try:
        query_job = client.query(query)
        results = [dict(row) for row in query_job]
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": f"查询失败: {e}"}), 500


@app.route('/documents/<string:idx>', methods=['GET'])
def get_document(idx):
    if not client:
        return jsonify({"error": "BigQuery client 未初始化"}), 500

    query = f"SELECT * FROM `{TABLE_ID}` WHERE idx = @idx"
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("idx", "STRING", idx),
        ]
    )

    try:
        query_job = client.query(query, job_config=job_config)
        results = [dict(row) for row in query_job]
        if results:
            return jsonify(results[0]), 200
        else:
            return jsonify({"error": "文档未找到"}), 404
    except Exception as e:
        return jsonify({"error": f"查询失败: {e}"}), 500


@app.route('/documents/<string:idx>', methods=['PUT'])
def update_document(idx):
    if not client:
        return jsonify({"error": "BigQuery client 未初始化"}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "请求体中缺少 JSON 数据"}), 400

    set_clauses = []
    query_params = []
    for key, value in data.items():
        if key != 'idx':
            set_clauses.append(f"{key} = @{key}")
            param_type = "STRING"
            query_params.append(
                bigquery.ScalarQueryParameter(key, param_type, value))

    if not set_clauses:
        return jsonify({"error": "请求体中没有可更新的字段"}), 400

    # 添加用于 WHERE 子句的 idx 参数
    query_params.append(bigquery.ScalarQueryParameter("idx", "STRING", idx))

    query = f"""
        UPDATE `{TABLE_ID}`
        SET {', '.join(set_clauses)}
        WHERE idx = @idx
    """

    job_config = bigquery.QueryJobConfig(query_parameters=query_params)

    try:
        query_job = client.query(query, job_config=job_config)
        query_job.result()

        if query_job.num_dml_affected_rows > 0:
            return get_document(idx)
        else:
            return jsonify({"error": "文档未找到或无需更新"}), 404

    except Exception as e:
        return jsonify({"error": f"更新失败: {e}"}), 500


@app.route('/documents/<string:idx>', methods=['DELETE'])
def delete_document(idx):
    if not client:
        return jsonify({"error": "BigQuery client 未初始化"}), 500

    query = f"DELETE FROM `{TABLE_ID}` WHERE idx = @idx"
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("idx", "STRING", idx),
        ]
    )

    try:
        query_job = client.query(query, job_config=job_config)
        query_job.result()

        if query_job.num_dml_affected_rows > 0:
            return jsonify({"message": f"文档 {idx} 已成功删除"}), 200
        else:
            return jsonify({"error": "文档未找到"}), 404
    except NotFound:
        return jsonify({"error": "文档未找到"}), 404
    except Exception as e:
        return jsonify({"error": f"删除失败: {e}"}), 500


@app.errorhandler(400)
def bad_request(error):
    return jsonify(error=str(error.description)), 400


@app.errorhandler(404)
def not_found(error):
    return jsonify(error=str(error.description)), 404


@app.errorhandler(500)
def internal_server_error(error):
    return jsonify(error=str(error.description)), 500


if __name__ == '__main__':
    print(f"--- RUNNING __main__ ---")
    print(f"Flask app debug actual: {app.debug}")
    print(
        f"Flask app use_reloader actual (config): {app.config.get('USE_RELOADER')}")
    app.run(host='0.0.0.0', port=9898, debug=False, use_reloader=False)
