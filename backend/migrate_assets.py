import sqlite3
import json
import os
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs

# --- 配置 ---
DATABASE_FILE = 'video_tree.db'
BACKUP_FILE = f'video_tree_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'

def backup_database():
    """备份当前数据库"""
    if os.path.exists(DATABASE_FILE):
        try:
            with open(DATABASE_FILE, 'rb') as f_in, open(BACKUP_FILE, 'wb') as f_out:
                f_out.write(f_in.read())
            print(f"✅ 数据库已备份到: {BACKUP_FILE}")
            return True
        except Exception as e:
            print(f"❌ 备份数据库失败: {e}")
            return False
    else:
        print(f"⚠️  数据库文件 {DATABASE_FILE} 不存在，跳过备份。")
        return True

def extract_type_from_url(url: str) -> str:
    """从URL中提取 'type' 参数的值，如 'input' 或 'output'"""
    try:
        # 处理可能不带协议头的URL
        if not urlparse(url).scheme:
            url = f"http://dummy.com{url}"
        
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        if 'type' in query_params:
            return query_params['type'][0].lower()
    except Exception as e:
        # 如果URL格式异常，默认按output处理或忽略
        print(f"⚠️  无法解析URL '{url}' 的类型: {e}")
    
    # 默认返回 'unknown'，后续会被归为 'output' 或忽略
    return 'unknown'

def migrate_assets(assets_json: str) -> str:
    """
    将旧格式的 assets JSON 转换为新格式。
    旧格式: {"images": ["url1?type=input", "url2?type=output"]}
    新格式: {"input": {"images": ["url1?type=input"]}, "output": {"images": ["url2?type=output"]}}
    """
    if not assets_json:
        return json.dumps({"input": {}, "output": {}})

    try:
        old_assets = json.loads(assets_json)
        if not isinstance(old_assets, dict):
            print(f"⚠️  无效的 assets 格式，跳过: {assets_json}")
            return assets_json

        new_assets = {"input": {}, "output": {}}

        # 遍历旧 assets 中的所有媒体类型 (images, videos, audio, etc.)
        for media_type, urls in old_assets.items():
            if not isinstance(urls, list):
                continue

            # 为每种媒体类型初始化 input 和 output 列表
            if media_type not in new_assets["input"]:
                new_assets["input"][media_type] = []
            if media_type not in new_assets["output"]:
                new_assets["output"][media_type] = []

            # 逐个检查URL并分类
            for url in urls:
                if isinstance(url, str):
                    type_tag = extract_type_from_url(url)
                    if type_tag == 'input':
                        new_assets["input"][media_type].append(url)
                    elif type_tag == 'output' or type_tag == 'unknown':
                        # 无法识别类型的URL默认归入 output
                        new_assets["output"][media_type].append(url)

        # 清理空列表，使JSON更简洁
        for io_key in ["input", "output"]:
            for media_type in list(new_assets[io_key].keys()):
                if len(new_assets[io_key][media_type]) == 0:
                    del new_assets[io_key][media_type]

        return json.dumps(new_assets, indent=None)

    except json.JSONDecodeError:
        print(f"⚠️  解析 assets JSON 失败，跳过: {assets_json}")
        return assets_json

def migrate():
    """执行数据迁移"""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        conn.execute("PRAGMA foreign_keys = ON")

        # --- 步骤 1: 新增 title 字段 ---
        print("\n--- 步骤 1: 检查并添加 title 字段 ---")
        cursor.execute("PRAGMA table_info(nodes)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'title' not in columns:
            cursor.execute("ALTER TABLE nodes ADD COLUMN title TEXT")
            print("✅ 成功添加 'title' 字段。")
        else:
            print("ℹ️  'title' 字段已存在，跳过。")

        # --- 步骤 2: 迁移数据 ---
        print("\n--- 步骤 2: 开始迁移数据 ---")
        
        # 获取所有需要迁移的节点
        cursor.execute("SELECT node_id, module_id, assets FROM nodes")
        rows = cursor.fetchall()

        total_nodes = len(rows)
        processed_nodes = 0
        updated_nodes = 0
        skipped_nodes = 0

        print(f"ℹ️  找到 {total_nodes} 个节点需要处理。")

        for row in rows:
            node_id, module_id, old_assets_json = row
            processed_nodes += 1

            # --- 迁移 title ---
            new_title = module_id

            # --- 迁移 assets ---
            new_assets_json = migrate_assets(old_assets_json)
            
            # 检查 assets 是否真的被修改了（用于统计）
            assets_changed = old_assets_json != new_assets_json

            # --- 执行更新 ---
            cursor.execute(
                "UPDATE nodes SET title = ?, assets = ? WHERE node_id = ?",
                (new_title, new_assets_json, node_id)
            )

            if assets_changed:
                updated_nodes += 1

            # 每处理20个节点打印一次进度
            if processed_nodes % 20 == 0:
                print(f"ℹ️  进度: {processed_nodes}/{total_nodes}")

        conn.commit()
        
        print("\n--- 迁移完成 ---")
        print(f"✅ 总共处理节点数: {processed_nodes}")
        print(f"✅ 成功更新 assets 结构的节点数: {updated_nodes}")
        print(f"ℹ️  'title' 字段已全部填充为 'module_id' 的值。")
        print("\n🎉 数据库迁移成功！")

    except sqlite3.Error as e:
        print(f"\n❌ 数据库操作失败: {e}")
        if conn:
            conn.rollback()
            print("❌ 事务已回滚。")
    finally:
        if conn:
            conn.close()

def verify_migration():
    """验证迁移结果（可选）"""
    print("\n--- 开始验证迁移结果 ---")
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.row_factory = sqlite3.Row # 方便按列名访问

        # 检查 title 字段
        cursor.execute("SELECT node_id, title, module_id FROM nodes LIMIT 3")
        sample_nodes = cursor.fetchall()

        print("抽样检查 'title' 字段:")
        for node in sample_nodes:
            print(f"  节点 {node['node_id']}: title='{node['title']}', module_id='{node['module_id']}' -> {node['title'] == node['module_id']}")

        # 检查 assets 结构
        print("\n抽样检查 'assets' 结构:")
        cursor.execute("SELECT node_id, assets FROM nodes WHERE assets IS NOT NULL AND assets != '{}' LIMIT 3")
        asset_samples = cursor.fetchall()

        for node in asset_samples:
            print(f"\n  节点 {node['node_id']}:")
            try:
                assets = json.loads(node['assets'])
                print(f"    新结构包含 'input': {'input' in assets}")
                print(f"    新结构包含 'output': {'output' in assets}")
                if 'input' in assets:
                    print(f"      - input: {json.dumps(assets['input'], indent=6)}")
                if 'output' in assets:
                    print(f"      - output: {json.dumps(assets['output'], indent=6)}")
            except json.JSONDecodeError:
                print(f"    ❌ assets JSON 解析失败。")

        print("\n✅ 验证完成。")

    except sqlite3.Error as e:
        print(f"❌ 验证失败: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print("🚀 开始执行数据库迁移脚本...")
    print("📋 脚本将执行以下操作:")
    print("   1. 备份数据库。")
    print("   2. 为 'nodes' 表添加 'title' 字段。")
    print("   3. 将 'module_id' 的值填充到 'title' 字段。")
    print("   4. 重构 'assets' 字段，根据URL中的 'type' 参数区分 'input' 和 'output'。")
    
    input("\n⚠️  请确保已阅读上述操作。按 Enter 键继续...")
    
    if backup_database():
        migrate()
        
        choice = input("\n是否要验证迁移结果？(y/n): ").strip().lower()
        if choice == 'y':
            verify_migration()
            
    print("\n👋 脚本执行结束。")