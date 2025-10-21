import sqlite3
import json
import uuid
from datetime import datetime
from typing import Optional

# --- 配置 ---
# 数据库文件的名称，它将与 app.py 存储在同一个 backend/ 目录下
DATABASE_FILE = 'video_tree.db'

# --- 核心函数 ---

def get_db_connection():
    """获取数据库连接，并设置返回结果为字典形式"""
    conn = sqlite3.connect(DATABASE_FILE)
    # 这行代码让查询结果可以通过列名访问，像字典一样，非常方便
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    初始化数据库。如果数据库文件或表不存在，则创建它们。
    这个函数应该在 app.py 启动时被调用一次。
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 创建 Trees 表，用于存储每一个项目（每一棵树）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Trees (
        tree_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ''')

    # 创建 Nodes 表，用于存储树上的每一个节点
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Nodes (
        node_id TEXT PRIMARY KEY,
        tree_id INTEGER NOT NULL,
        parent_id TEXT,
        module_id TEXT NOT NULL,
        parameters TEXT,  -- 将作为JSON字符串存储
        assets TEXT,      -- 将作为JSON字符串存储
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tree_id) REFERENCES Trees (tree_id)
    );
    ''')

    conn.commit()
    conn.close()
    print("数据库已成功初始化。")

def create_tree(name: str) -> int:
    """
    创建一个新的树项目。
    返回新创建的树的 ID。
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Trees (name) VALUES (?)", (name,))
    tree_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return tree_id

def add_node(tree_id: int, parent_id: Optional[str], module_id: str, parameters: dict, assets: dict = None) -> str:
    """
    向指定的树添加一个新节点。
    返回新创建的节点的 ID (UUID)。
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    new_node_id = str(uuid.uuid4())
    # 将Python字典转换为JSON字符串，以便存入TEXT类型的数据库字段
    parameters_json = json.dumps(parameters)
    assets_json = json.dumps(assets) if assets else json.dumps({}) # 确保总是一个JSON字符串
    
    cursor.execute(
        """
        INSERT INTO Nodes (node_id, tree_id, parent_id, module_id, parameters, assets, status) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (new_node_id, tree_id, parent_id, module_id, parameters_json, assets_json, 'completed')
    )
    conn.commit()
    conn.close()
    return new_node_id

def get_node(node_id: str) -> Optional[dict]:
    """
    根据节点ID获取单个节点的详细信息。
    这是 app.py 中注入父节点资产时需要用到的函数。
    """
    if not node_id:
        return None
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Nodes WHERE node_id = ?", (node_id,))
    node = cursor.fetchone()
    conn.close()

    if not node:
        return None

    # 将数据库行对象转换为字典，并解析JSON字符串
    node_dict = dict(node)
    node_dict['parameters'] = json.loads(node_dict['parameters']) if node_dict['parameters'] else {}
    node_dict['assets'] = json.loads(node_dict['assets']) if node_dict['assets'] else {}
    return node_dict

def get_tree_as_json(tree_id: int) -> Optional[dict]:
    """
    获取一棵完整的树，并以适合前端使用的JSON格式返回。
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. 获取树（项目）的基本信息
    cursor.execute("SELECT * FROM Trees WHERE tree_id = ?", (tree_id,))
    tree_info = cursor.fetchone()
    
    if not tree_info:
        conn.close()
        return None # 如果找不到树，返回None

    # 2. 获取该树的所有节点
    cursor.execute("SELECT * FROM Nodes WHERE tree_id = ? ORDER BY created_at ASC", (tree_id,))
    nodes = cursor.fetchall()
    conn.close()

    # 3. 将节点列表转换为字典列表，并解析JSON字段
    node_list = []
    for node_row in nodes:
        node_dict = dict(node_row)
        node_dict['parameters'] = json.loads(node_dict['parameters']) if node_dict['parameters'] else {}
        node_dict['assets'] = json.loads(node_dict['assets']) if node_dict['assets'] else {}
        node_list.append(node_dict)

    # 4. 组合成最终的JSON对象
    return {
        "tree_id": tree_info["tree_id"],
        "name": tree_info["name"],
        "created_at": tree_info["created_at"],
        "nodes": node_list
    }
# --- 【新增】删除节点的功能 ---
def delete_node_and_descendants(node_id: str):
    """删除一个节点及其所有的子孙节点。<是一个迭代实现，比递归更安全。"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    nodes_to_delete = [node_id]
    
    # 使用循环查找所有子孙节点
    i = 0
    while i < len(nodes_to_delete):
        current_node_id = nodes_to_delete[i]
        cursor.execute("SELECT node_id FROM Nodes WHERE parent_id = ?", (current_node_id,))
        children = cursor.fetchall()
        for child in children:
            nodes_to_delete.append(child['node_id'])
        i += 1
        
        # 从后往前删除，以避免违反外键约束
        for n_id in reversed(nodes_to_delete):
            # 1. 在删除数据库记录前，先获取该节点的资产信息
            node_details = get_node(n_id)
            
            # 2. 如果存在资产信息，则尝试删除物理文件
            if node_details and 'assets' in node_details:
                assets = node_details.get('assets', {})
                # 将图片和视频的URL合并到一个列表中进行处理
                asset_urls = assets.get('images', []) + assets.get('videos', [])
                
                for asset_url in asset_urls:
                    try:
                        parsed_url = urllib.parse.urlparse(asset_url)
                        query_params = urllib.parse.parse_qs(parsed_url.query)
                        
                        filename = query_params.get('filename', [None])[0]
                        subfolder = query_params.get('subfolder', [''])[0]
                        
                        if filename:
                            # 生成文件可能存在的两个路径
                            # a) 它原始的输出路径
                            output_file_path = os.path.join(COMFYUI_OUTPUT_PATH, subfolder, filename)
                            # b) 它可能被复制到了输入路径以供图生图使用
                            input_file_path = os.path.join(COMFYUI_INPUT_PATH, filename)
                            
                            # 检查并删除两个路径下的文件
                            if os.path.exists(output_file_path):
                                os.remove(output_file_path)
                                print(f"    - 删除了物理文件: {output_file_path}")
                                
                            if os.path.exists(input_file_path):
                                os.remove(input_file_path)
                                print(f"    - 删除了物理文件: {input_file_path}")
                    except Exception as e:
                        print(f"    - 🟡 删除物理文件时出现警告: {e}")
                            
            # 3. 最后，删除数据库中的节点记录
            print(f"正在删除数据库节点: {n_id}")
            cursor.execute("DELETE FROM Nodes WHERE node_id = ?", (n_id,))
                
        conn.commit()
        conn.close()



# --- 用于独立测试此文件的部分 ---
if __name__ == '__main__':
    print("正在初始化数据库并进行测试...")
    init_db()
    
    # 测试：检查是否已存在ID为1的项目，如果不存在则创建一个
    if not get_tree_as_json(1):
        print("未找到项目1，正在创建测试项目...")
        test_tree_id = create_tree("我的第一个测试项目")
        print(f"创建了新项目，ID: {test_tree_id}")
        
        root_node_id = add_node(
            tree_id=test_tree_id, 
            parent_id=None, 
            module_id="Init", 
            parameters={"description": "这是项目的根节点"}
        )
        print(f"为项目 {test_tree_id} 添加了根节点, ID: {root_node_id}")

        child_node_id = add_node(
            tree_id=test_tree_id,
            parent_id=root_node_id,
            module_id="GenerateImage",
            parameters={"prompt": "一只猫"},
            assets={"images": ["/view?filename=cat.png"]}
        )
        print(f"添加了子节点, ID: {child_node_id}")

    # 获取并打印项目1的完整结构
    tree_data = get_tree_as_json(1)
    if tree_data:
        print("\n获取到的项目1的结构:")
        # pretty-print the JSON
        print(json.dumps(tree_data, indent=2, ensure_ascii=False))
    else:
        print("\n未找到项目1。")

