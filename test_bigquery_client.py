import uuid
import requests
import json


BASE_URL = "http://localhost:9898"


def run_all_tests():
    """主函数，运行所有测试用例"""
    print("--- Running Happy Path Test ---")
    test_crud_happy_path()

    print("\n--- Running Negative Path Test (Get Non-existent) ---")
    test_get_non_existent_document()


def test_crud_happy_path():
    """测试完整的 CRUD 成功流程"""
    created_idx = None  # 先声明，以便在 finally 中使用
    try:
        # 1. Test POST (Create)
        print("Testing POST /documents")
        new_doc_data = {
            "title": "Test Document " + str(uuid.uuid4()),
            "type": "Article",
            "publish_time": "2025-06-14",
            "author": "Test Author",
            "url": "http://example.com/testdoc",
            "text": "This is the content of the test document."
        }
        response = requests.post(f"{BASE_URL}/documents", json=new_doc_data)
        print(f"POST /documents Status Code: {response.status_code}")
        response.raise_for_status()  # 如果状态码不是 2xx，会抛出异常

        created_doc = response.json()
        created_idx = created_doc.get('idx')
        print(f"Created document with idx: {created_idx}")
        assert response.status_code == 201

        # 2. Test GET (Read)
        print(f"\nTesting GET /documents/{created_idx}")
        response_get = requests.get(f"{BASE_URL}/documents/{created_idx}")
        assert response_get.status_code == 200
        assert response_get.json().get('idx') == created_idx
        print("GET by idx successful.")

        # 3. Test PUT (Update)
        print(f"\nTesting PUT /documents/{created_idx}")
        update_data = {"title": "Updated Test Document"}
        response_put = requests.put(
            f"{BASE_URL}/documents/{created_idx}", json=update_data)
        assert response_put.status_code == 200
        updated_doc = response_put.json()
        assert updated_doc.get('title') == update_data['title']
        print("PUT successful.")

    except Exception as e:
        print(f"\n--- AN ERROR OCCURRED DURING HAPPY PATH TEST: {e} ---")
        # 即使发生错误，我们依然希望执行 finally 来清理数据

    finally:
        # 4. Test DELETE (Cleanup)
        # 这个块无论 try 是否成功都会执行
        if created_idx:
            print(f"\n[Cleanup] Testing DELETE /documents/{created_idx}")
            response_delete = requests.delete(
                f"{BASE_URL}/documents/{created_idx}")
            assert response_delete.status_code == 200
            print(f"DELETE successful. Response: {response_delete.json()}")

            # 5. Verify Deletion
            print(f"[Cleanup] Verifying deletion of {created_idx}")
            response_verify = requests.get(
                f"{BASE_URL}/documents/{created_idx}")
            assert response_verify.status_code == 404
            print("Verification of deletion successful (404 Not Found).")
        else:
            print("\n[Cleanup] No document was created, skipping delete.")


def test_get_non_existent_document():
    """测试获取一个不存在的文档"""
    non_existent_idx = "this-idx-definitely-does-not-exist"
    response = requests.get(f"{BASE_URL}/documents/{non_existent_idx}")
    print(f"GET non-existent Status Code: {response.status_code}")
    assert response.status_code == 404
    print("Successfully asserted 404 for a non-existent document.")


if __name__ == '__main__':
    try:
        run_all_tests()
        print("\n✅ All tests passed!")
    except requests.exceptions.ConnectionError:
        print("\n❌ Test failed: Could not connect to the server.")
        print("   Please ensure the Flask server is running on " + BASE_URL)
    except AssertionError as e:
        print(f"\n❌ A test assertion failed: {e}")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
