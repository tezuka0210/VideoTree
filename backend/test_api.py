import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_get_tree():
    """测试获取树结构的接口"""
    print("--- 正在测试 [GET /api/trees/1] ---")
    try:
        response = requests.get(f"{BASE_URL}/api/trees/1")
        response.raise_for_status()  # 如果状态码不是2xx，则抛出异常

        tree_data = response.json()
        print("✅ 测试成功! 状态码:", response.status_code)
        print("返回数据:", json.dumps(tree_data, indent=2, ensure_ascii=False))

        # 找到根节点并返回其ID
        if tree_data and tree_data.get('nodes'):
            root_node = tree_data['nodes'][0]
            return root_node['node_id']
        else:
            print("❌ 错误：返回的数据中没有找到节点。")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ 测试失败: {e}")
        return None

def test_create_node(parent_id):
    """测试创建新节点的接口"""
    if not parent_id:
        print("--- 跳过 [POST /api/nodes] 测试，因为没有有效的父节点ID ---")
        return

    print("\n--- 正在测试 [POST /api/nodes] ---")
    payload = {
        "tree_id": 1,
        "parent_id": parent_id,
        "module_id": "TextGenerateVideo",
        "parameters": {
            "positive_prompt": "Night on the Yangtze: a full moon hangs low, its perfect reflection stretching like a silver ribbon across the dark, slow-moving river; distant fishing boats drift with lights dimmed, their shapes reduced to quiet silhouettes; far banks fade into indigo haze, layered mountain ridges rendered in wet ink tones; surface water carries gentle ripples that break the lunar image into shimmering shards of liquid mercury; cool palette of deep indigo, muted cobalt and antique silver, no human presence; 35 mm lens, f/4, long exposure capturing subtle star-trails above, 8 K clarity, tranquil timeless atmosphere", 
            "width":1024,
            "height":512
        }
    }

    try:
        print("发送的Payload:", json.dumps(payload, indent=2))
        # 注意：AI生成可能耗时较长，增加超时时间
        response = requests.post(f"{BASE_URL}/api/nodes", json=payload, timeout=300) 
        response.raise_for_status()

        new_tree_data = response.json()
        print("✅ 测试成功! 状态码:", response.status_code)
        print("新返回的树数据:", json.dumps(new_tree_data, indent=2, ensure_ascii=False))

        if len(new_tree_data['nodes']) > 1:
            print("🎉 成功创建了新节点！")
        else:
            print("⚠️ 警告：树结构中没有新增节点。")

    except requests.exceptions.RequestException as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    # 1. 首先，测试获取树并拿到根节点ID
    root_node_id = test_get_tree()

    # 2. 然后，使用获取到的根节点ID来测试创建新节点
    test_create_node(root_node_id)