import requests
import json
import os
import random
import time

# --- 配置 ---
# 确保这个URL与您 app.py 运行的地址和端口一致
BASE_URL = "http://127.0.0.1:5000"
TREE_ID = 1 # 我们要测试的项目ID

def print_header(title):
    """打印漂亮的标题"""
    print(f"\n--- 正在测试 [{title}] ---")

def print_payload(payload):
    """打印发送的数据"""
    print("发送的Payload:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

def test_get_tree():
    """测试获取树结构的API"""
    print_header(f"GET /api/trees/{TREE_ID}")
    try:
        response = requests.get(f"{BASE_URL}/api/trees/{TREE_ID}")
        response.raise_for_status() # 如果状态码不是2xx，则抛出异常
        print(f"✅ 测试成功! 状态码: {response.status_code}")
        data = response.json()
        print("返回数据:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        # 找到根节点并返回其ID
        if data.get('nodes'):
            return data['nodes'][0]['node_id']
    except requests.exceptions.RequestException as e:
        print(f"❌ 测试失败: {e}")
    return None

def test_text_to_image(parent_node_id):
    """测试文生图"""
    print_header("POST /api/nodes (文生图)")
    if not parent_node_id:
        print("--- 跳过测试，因为没有有效的父节点ID ---")
        return None
        
    payload = {
      "tree_id": TREE_ID,
      "parent_id": parent_node_id,
      "module_id": "TextGenerateImage",
      "parameters": {
        "positive_prompt": "An beautiful cat, masterpiece, high quality",
        "width": 1024,
        "height": 512,
        "seed": random.randint(0, 999999999999999)
      }
    }
    print_payload(payload)
    
    try:
        response = requests.post(f"{BASE_URL}/api/nodes", json=payload)
        response.raise_for_status()
        print(f"✅ 测试成功! 状态码: {response.status_code}")
        data = response.json()
        # 找到最新生成的那个节点并返回其ID
        if data.get('nodes') and len(data['nodes']) > 1:
            new_node = data['nodes'][-1] # 最后一个节点是最新创建的
            print(f"新生成的节点ID: {new_node['node_id']}")
            return new_node['node_id']
    except requests.exceptions.RequestException as e:
        print(f"❌ 测试失败: {e}")
    return None


def test_image_to_image_from_node(parent_node_id):
    """测试图生图（基于已存在的节点）"""
    print_header("POST /api/nodes (图生图 - 来自节点)")
    if not parent_node_id:
        print("--- 跳过测试，因为没有有效的父节点ID ---")
        return None

    payload = {
        "tree_id": TREE_ID,
        "parent_id": parent_node_id, # 父节点是上一步生成的猫图
        "module_id": "ImageGenerateImage_Basic",
        "parameters": {
        "positive_prompt": "Take the exact cat from the input image—same fur color, markings, size, and proportions—and place it in the center of a lush, sunlit lawn during mid-morning; the cat is mid-pounce, front paws extended, ears forward, chasing a small white butterfly; soft green grass blades bend under its paws, a few scattered clover flowers visible; background shows a gentle blur of more lawn and distant trees, natural blue sky with faint clouds; keep original lighting direction and color temperature, 50 mm lens, f/2.8, 1/1000 s freeze motion, 8 K clarity, playful outdoor atmosphere.",
        "width":1024,
        "height": 512,
        "seed": random.randint(0, 999999999999999),
        "image_input": {
            "type": "from_node",
            "node_id": parent_node_id # 明确告诉后端使用这个节点的图片
        }
      }
    }
    print_payload(payload)

    try:
        response = requests.post(f"{BASE_URL}/api/nodes", json=payload)
        response.raise_for_status()
        print(f"✅ 测试成功! 状态码: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ 测试失败: {e}")


# def test_image_to_video_from_node(parent_node_id):
#     """测试图生视频（基于已存在的节点）"""
#     print_header("POST /api/nodes (图生视频 - 来自节点)")
#     if not parent_node_id:
#         print("--- 跳过测试，因为没有有效的父节点ID ---")
#         return None

#     payload = {
#         "tree_id": TREE_ID,
#         "parent_id": parent_node_id, # 父节点是上一步生成的猫图
#         "module_id": "ImageGenerateVideo",
#         "parameters": {
#         "positive_prompt": "猫在跑动跳跃",
#         "width":1024,
#         "height": 512,
#         "seed": random.randint(0, 999999999999999),
#         "image_input": {
#             "type": "from_node",
#             "node_id": parent_node_id # 明确告诉后端使用这个节点的图片
#         }
#       }
#     }
#     print_payload(payload)


#     try:
#         response = requests.post(f"{BASE_URL}/api/nodes", json=payload)
#         response.raise_for_status()
#         print(f"✅ 测试成功! 状态码: {response.status_code}")
#     except requests.exceptions.RequestException as e:
#         print(f"❌ 测试失败: {e}")

def test_upload_image():
    """测试图片上传"""
    print_header("POST /api/assets/upload (上传新图)")
    filepath = 'cat.jpg'
    if not os.path.exists(filepath):
        print(f"--- 跳过测试，因为在当前目录下未找到 '{filepath}' 文件 ---")
        return None
    
    with open(filepath, 'rb') as f:
        files = {'file': (filepath, f, 'image/png')}
        try:
            response = requests.post(f"{BASE_URL}/api/assets/upload", files=files)
            response.raise_for_status()
            data = response.json()
            uploaded_filename = data.get('filename')
            print(f"✅ 测试成功! 文件已上传，服务器路径: {uploaded_filename}")
            return uploaded_filename
        except requests.exceptions.RequestException as e:
            print(f"❌ 测试失败: {e}")
    return None

def test_image_to_image_from_upload(parent_node_id, new_image_filename):
    """测试图生图（基于新上传的图片）"""
    print_header("POST /api/nodes (图生图 - 来自上传)")
    if not parent_node_id or not new_image_filename:
        print("--- 跳过测试，因为缺少父节点ID或新图片 ---")
        return

    payload = {
        "tree_id": TREE_ID,
        "parent_id": parent_node_id,
        "module_id": "ImageGenerateImage_Basic",
        "parameters": {
            "positive_prompt": "Insert the exact cat from the input image — same fur color, markings, size, and proportions — into a bright, modern living room: mid-afternoon natural light spills through sheer white curtains onto a low linen-upholstered sofa and light-walnut coffee table; the cat is caught mid-leap, front paws stretched toward a dangling feather toy suspended from a floor-to-ceiling cat tree in the left foreground; soft cream carpet shows subtle paw indentations, while background shelves and wall art fall into gentle bokeh; keep original lighting direction and temperature, 35 mm lens, f/2.8, 1/1000 s freeze motion, 8 K clarity, lively yet cozy indoor atmosphere.",
            "width":1024,
            "height": 512,
            "seed": random.randint(0, 999999999999999),
            "image_input": {
                "type": "new_upload",
                "filename": new_image_filename # 告诉后端使用这个新上传的图片
        }
      }
    }
    print_payload(payload)

    try:
        response = requests.post(f"{BASE_URL}/api/nodes", json=payload)
        response.raise_for_status()
        print(f"✅ 测试成功! 状态码: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ 测试失败: {e}")


# def test_image_to_video_from_upload(parent_node_id, new_image_filename):
#     """测试图生图（基于新上传的视频）"""
#     print_header("POST /api/nodes (图生视频 - 来自上传)")
#     if not parent_node_id or not new_image_filename:
#         print("--- 跳过测试，因为缺少父节点ID或新图片 ---")
#         return

#     payload = {
#         "tree_id": TREE_ID,
#         "parent_id": parent_node_id,
#         "module_id": "ImageGenerateVideo",
#         "parameters": {
#             "positive_prompt": "猫在跑动跳跃",
#             "width":1024,
#             "height": 512,
#             "seed": random.randint(0, 999999999999999),
#             "image_input": {
#                 "type": "new_upload",
#                 "filename": new_image_filename # 告诉后端使用这个新上传的图片
#         }
#       }
#     }
#     print_payload(payload)

#     try:
#         response = requests.post(f"{BASE_URL}/api/nodes", json=payload)
#         response.raise_for_status()
#         print(f"✅ 测试成功! 状态码: {response.status_code}")
#     except requests.exceptions.RequestException as e:
#         print(f"❌ 测试失败: {e}")


if __name__ == "__main__":
    # 按顺序执行所有测试
    root_node_id = test_get_tree()
    
    # 测试1: 文生图
    t2i_node_id = test_text_to_image(root_node_id)
    time.sleep(1)
    # 测试2: 图生图 (基于上一步的结果)
    # test_image_to_video_from_node(t2i_node_id)
    test_image_to_image_from_node(t2i_node_id)
    
    time.sleep(1)
    # 测试3: 上传新图片
    uploaded_filename = test_upload_image()
    time.sleep(1)
    # 测试4: 图生图 (基于新上传的图片)
    # root_node_id_new = test_get_tree()
    # test_image_to_video_from_upload(root_node_id, uploaded_filename)
    test_image_to_image_from_upload(root_node_id, uploaded_filename)