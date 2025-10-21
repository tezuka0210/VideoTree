import os
import json
import requests
import uuid
import time
import urllib.parse
import websocket # 用于与ComfyUI进行实时通信
import shutil
import mimetypes
import re
from flask import Flask, request, jsonify, send_from_directory, render_template, send_file, abort, Response
from flask_cors import CORS
from dotenv import load_dotenv
from typing import Optional
from moviepy import VideoFileClip, concatenate_videoclips,ImageClip
# 导入之前设计的数据库操作模块
import database

# --- 1. 初始化与配置 ---

load_dotenv()
app = Flask(__name__, template_folder='templates')
CORS(app)

# --- 配置常量 ---
COMFYUI_SERVER_ADDRESS = "223.193.6.178:8188" # ComfyUI后端的地址和端口
CLIENT_ID = str(uuid.uuid4()) # 为我们的后端应用生成一个唯一的客户端ID
UPLOAD_FOLDER = 'assets'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
BASE_COMFYUI_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'comfyui', 'comfyui'))
COMFYUI_INPUT_PATH = os.path.join(BASE_COMFYUI_PATH, 'input')
COMFYUI_OUTPUT_PATH = os.path.join(BASE_COMFYUI_PATH, 'output')
print(f"ComfyUI的输入目录被设置为: {COMFYUI_INPUT_PATH}")
print(f"ComfyUI的输出目录被设置为: {COMFYUI_OUTPUT_PATH}")
os.makedirs(COMFYUI_INPUT_PATH, exist_ok=True)
# 图片目录
IMAGE_DIR = os.path.join(BASE_COMFYUI_PATH, "output")
# 视频目录
VIDEO_DIR = os.path.join(IMAGE_DIR, "video")
STITCHED_OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), 'stitched_videos') # 存放拼接结果
os.makedirs(STITCHED_OUTPUT_FOLDER, exist_ok=True)

# --- 2. 核心辅助函数 ---

def find_node_id_by_title(workflow: dict, target_title: str) -> Optional[str]:
    """遍历工作流JSON，根据自定义的节点标题查找节点ID。"""
    for node_id, node_info in workflow.items():
        if '_meta' in node_info and node_info['_meta'].get('title') == target_title:
            return node_id
    return None

def load_workflow(module_id: str) -> Optional[dict]:
    """根据模块ID从workflows文件夹加载对应的工作流JSON文件。"""
    workflow_path = os.path.join('workflows', f"{module_id}.json")
    if not os.path.exists(workflow_path):
        return None
    with open(workflow_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def queue_comfyui_prompt(workflow: dict) -> dict:
    """将工作流提交到ComfyUI的队列中。"""
    prompt_data = {"prompt": workflow, "client_id": CLIENT_ID}
    print(">>> 正在向ComfyUI提交工作流...")
    
    # 【关键调试代码】打印最终要发送的工作流JSON
    print("--- 最终发送给 ComfyUI 的工作流 (可复制用于调试) ---")
    print(json.dumps(workflow, indent=2, ensure_ascii=False))
    print("----------------------------------------------------")
    
    response = requests.post(f"http://{COMFYUI_SERVER_ADDRESS}/prompt", json=prompt_data)
    response.raise_for_status()
    print("<<< ComfyUI已接受任务。")
    return response.json()

def get_comfyui_outputs(prompt_id: str) -> dict:
    """
    通过WebSocket连接，等待ComfyUI任务执行完成，并获取输出结果。
    这是处理耗时任务的关键。
    """
    ws = websocket.WebSocket()
    ws.connect(f"ws://{COMFYUI_SERVER_ADDRESS}/ws?clientId={CLIENT_ID}")
    
    while True:
        try:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        # 执行完成的标志
                        break 
        except websocket.WebSocketConnectionClosedException:
            print("WebSocket连接已关闭，任务可能已完成或中断。")
            break
    ws.close()

    # 从/history API获取最终的输出信息
    history_response = requests.get(f"http://{COMFYUI_SERVER_ADDRESS}/history/{prompt_id}")
    history_response.raise_for_status()
    history = history_response.json()
    
    outputs = {}
    # 遍历历史记录中的输出
    for node_id, node_output in history[prompt_id]['outputs'].items():
        if 'images' in node_output:
            image_list = []
            for image in node_output['images']:
                cache_buster = int(time.time())
                # ComfyUI的/view API可以获取图片，我们需要构建完整的URL
                image_url = f"/view?filename={urllib.parse.quote_plus(image['filename'])}&subfolder={urllib.parse.quote_plus(image['subfolder'])}&type={image['type']}&_cache_buster={cache_buster}"
                image_list.append(image_url)
            outputs['images'] = image_list
        # 你可以在这里添加对视频等其他输出类型的处理
        if 'videos' in node_output: 
            video_list = []
            for video in node_output['videos']:
                cache_buster = int(time.time())
                # ComfyUI的/view API可以获取图片，我们需要构建完整的URL
                video_url = f"/view?filename={urllib.parse.quote_plus(video['filename'])}&subfolder={urllib.parse.quote_plus(video['subfolder'])}&type={video['type']}&_cache_buster={cache_buster}"
                video_list.append(video_url)
            outputs['videos'] = video_list

    return outputs


# --- 3. Flask API 路由定义 ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route("/view", methods=["GET"])
def view_file():
    filename = request.args.get("filename")
    if not filename:
        return abort(400, "缺少 filename 参数")

    # 搜索路径
    image_path = os.path.join(IMAGE_DIR, filename)
    video_path = os.path.join(VIDEO_DIR, filename)

    if os.path.exists(image_path):
        file_path = image_path
    elif os.path.exists(video_path):
        file_path = video_path
    else:
        return abort(404, f"文件 {filename} 不存在")

    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        mime_type = "application/octet-stream"

    # --- 视频 Range 支持 ---
    if mime_type.startswith("video/"):
        try:
            file_size = os.path.getsize(file_path)
            range_header = request.headers.get("Range", None)

            if range_header:
                # Range 请求
                start, end = range_header.replace("bytes=", "").split("-")
                start = int(start)
                end = int(end) if end else file_size - 1
                length = end - start + 1

                with open(file_path, "rb") as f:
                    f.seek(start)
                    data = f.read(length)

                rv = Response(data, 206, mimetype=mime_type)
                rv.headers.add("Content-Range", f"bytes {start}-{end}/{file_size}")
                rv.headers.add("Accept-Ranges", "bytes")
                rv.headers.add("Content-Length", str(length))
                rv.headers.add("X-Content-Type-Options", "nosniff")
                return rv
            else:
                # 首次请求（非 Range）
                rv = send_file(file_path, mimetype=mime_type)
                rv.headers.add("Accept-Ranges", "bytes")
                rv.headers.add("X-Content-Type-Options", "nosniff")
                return rv
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # --- 图片或其他文件 ---
    rv = send_file(file_path, mimetype=mime_type)
    rv.headers.add("X-Content-Type-Options", "nosniff")
    return rv



@app.route('/api/assets/upload', methods=['POST'])
def upload_asset():
    """API: 供用户上传全新的文件，并直接保存到ComfyUI的input目录"""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[1]
    filepath = os.path.join(COMFYUI_INPUT_PATH, filename)
    file.save(filepath)
    print(f"    - 文件已上传并保存到ComfyUI的输入目录: {filepath}")
    # 返回纯文件名
    return jsonify({"name": filename}), 201


@app.route('/api/trees/<int:tree_id>', methods=['GET'])
def get_tree(tree_id):
    """API: 获取一棵树的完整结构，如果项目或根节点不存在，则自动创建。"""
    tree_data = database.get_tree_as_json(tree_id)
    
    # 场景1：连项目（树）本身都不存在
    if not tree_data:
        print(f"项目 {tree_id} 不存在，正在自动创建...")
        # 简单处理：只为ID为1的项目自动创建
        if tree_id == 1:
            new_tree_id = database.create_tree("我的第一个项目")
            database.add_node(new_tree_id, None, "Init", {"description": "项目根节点"})
            tree_data = database.get_tree_as_json(new_tree_id)
        else:
            return jsonify({"error": f"Tree with ID {tree_id} not found."}), 404
        
    #  场景2：项目存在，但里面是空的（没有任何节点）
    elif not tree_data.get('nodes'):
        print(f"项目 {tree_id} 为空，正在自动添加根节点...")
        database.add_node(tree_id, None, "Init", {"description": "项目根节点"})
        # 重新获取一次数据
        tree_data = database.get_tree_as_json(tree_id)
        
    return jsonify(tree_data)

# --- 【新增】删除节点的API接口 ---
@app.route('/api/nodes/<node_id>', methods=['DELETE'])
def delete_node(node_id):
    """API: 删除一个节点及其所有后代。"""
    try:
        # 调用我们新创建的数据库函数
        database.delete_node_and_descendants(node_id)
        return jsonify({"status": "success", "message": f"节点 {node_id} 及其后代已被删除。"}), 200
    except Exception as e:
        print(f"删除节点 {node_id} 时出错: {e}")
        return jsonify({"error": "删除节点失败。"}), 500

@app.route('/api/nodes', methods=['POST'])
def create_node():
    """API: 创建一个新节点，即执行一次生成操作。"""
    data = request.get_json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print("-------------------------------")
    tree_id = data.get('tree_id')
    parent_id = data.get('parent_id') # 现在我们简化为单个父节点
    module_id = data.get('module_id')
    parameters = data.get('parameters', {})

    workflow = load_workflow(module_id)
    if workflow is None:
        return jsonify({"error": f"Workflow for module '{module_id}' not found."}), 404

    # --- 动态修改工作流 ---
    # PROMPT
    prompt_positive_node_id = find_node_id_by_title(workflow, "CLIP Text Encode (Positive Prompt)")
    if prompt_positive_node_id and 'positive_prompt' in parameters:
        workflow[prompt_positive_node_id]["inputs"]["text"] = parameters['positive_prompt']
    
    prompt_negative_node_id = find_node_id_by_title(workflow, "CLIP Text Encode (Negative Prompt)")
    if prompt_negative_node_id and 'negative_prompt' in parameters:
        workflow[prompt_negative_node_id]["inputs"]["text"] = parameters['negative_prompt']

    # WIDTH HEIGHT LENGTH BATCH_SIZE SPEED
    size_node_id = find_node_id_by_title(workflow, "Size_Setting")
    if size_node_id:
        if 'width' in parameters:
            workflow[size_node_id]["inputs"]["width"] = parameters['width']
        if 'height' in parameters:
            workflow[size_node_id]["inputs"]["height"] = parameters['height']
        if 'batch_size' in parameters:
            workflow[size_node_id]["inputs"]["batch_size"] = parameters['batch_size']
        if 'length' in parameters:
            workflow[size_node_id]["inputs"]["length"] = parameters['length']
        if 'speed' in parameters:
            workflow[size_node_id]["inputs"]["speed"] = parameters['speed']

    # KSAMPLE
    sampler_node_id = find_node_id_by_title(workflow, "KSampler")
    if sampler_node_id:
        if 'seed' in parameters:
            workflow[sampler_node_id]["inputs"]["seed"] = parameters['seed']
        if 'cfg' in parameters:
            workflow[sampler_node_id]["inputs"]["cfg"] = parameters['cfg']
        if 'step' in parameters:
            workflow[sampler_node_id]["inputs"]["steps"] = parameters['steps']
        if 'denoise' in parameters:
            workflow[sampler_node_id]["inputs"]["denoise"] = parameters['denoise']

    # FLUX GUIDANCE
    guidance_node_id = find_node_id_by_title(workflow, "FluxGuidance")
    if guidance_node_id and 'guidance' in parameters:
        workflow[guidance_node_id]["inputs"]["guidance"] = parameters['guidance']


    # IMAGE
    image_input_node_id = find_node_id_by_title(workflow, "LoadImage")
    if image_input_node_id and 'image_input' in parameters:
        image_input_info = parameters['image_input']
        image_filename = None
        # 场景1: 图像来自一个已存在的节点   
        if image_input_info.get('type') == 'from_node':
            source_node_id = image_input_info.get('node_id')
            source_node = database.get_node(source_node_id)
            if source_node and source_node.get('assets', {}).get('images'):
                image_url = source_node['assets']['images'][0]
                parsed_url = urllib.parse.urlparse(image_url)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                
                filename = query_params.get('filename', [None])[0]
                subfolder = query_params.get('subfolder', [''])[0]
                
                if filename:
                # 构建源文件和目标文件的完整路径
                    source_path = os.path.join(COMFYUI_OUTPUT_PATH, subfolder, filename)
                    destination_path = os.path.join(COMFYUI_INPUT_PATH, filename)
                    # 检查源文件是否存在，然后复制
                    if os.path.exists(source_path):
                        try:
                            with open(source_path, 'rb') as f_read:
                                with open(destination_path, 'wb') as f_write:
                                    f_write.write(f_read.read())
                            image_filename = filename
                            print(f"    - 已将文件 '{filename}' 从output手动复制到input目录。")
                        except IOError as e:
                            print(f"    -  错误: 文件复制失败: {e}")
                    else:
                        print(f"    - 错误: 源文件 '{source_path}' 不存在，无法复制。")

                
         # 场景2: 图像是用户新上传的
        elif image_input_info.get('type') == 'new_upload':
            # 直接使用上传接口返回的路径，并提取文件名
            # 注意：这要求ComfyUI能访问到这个'assets'文件夹
            image_filename = image_input_info.get('filename')
                
        # 如果成功获取了文件名，则注入到工作流中
        if image_filename:
            workflow[image_input_node_id]["inputs"]["image"] = image_filename
        else:
            print(f"警告：无法从 image_input 参数中解析出有效的图像文件名。")

    # IMAGE MOVE
    image_move_input_node_id = find_node_id_by_title(workflow, "LoadImage(Move)")
    if image_move_input_node_id and 'image_input' in parameters:
        image_move_input_info = parameters['image_input']
        image_filename = None
        # 场景1: 图像来自一个已存在的节点   
        if source_node and source_node.get('assets', {}).get('images'):
                image_url = source_node['assets']['images'][0]
                parsed_url = urllib.parse.urlparse(image_url)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                
                filename = query_params.get('filename', [None])[0]
                subfolder = query_params.get('subfolder', [''])[0]
                
                if filename:
                # 构建源文件和目标文件的完整路径
                    source_path = os.path.join(COMFYUI_OUTPUT_PATH, subfolder, filename)
                    destination_path = os.path.join(COMFYUI_INPUT_PATH, filename)
                    # 检查源文件是否存在，然后复制
                    if os.path.exists(source_path):
                        try:
                            with open(source_path, 'rb') as f_read:
                                with open(destination_path, 'wb') as f_write:
                                    f_write.write(f_read.read())
                            image_filename = filename
                            print(f"    - 已将文件 '{filename}' 从output手动复制到input目录。")
                        except IOError as e:
                            print(f"    -  错误: 文件复制失败: {e}")
                    else:
                        print(f"    - 错误: 源文件 '{source_path}' 不存在，无法复制。")
                
         # 场景2: 图像是用户新上传的
        elif image_move_input_info.get('type') == 'new_upload':
            image_filename = image_input_info.get('filename')
        if image_filename:
            workflow[image_input_node_id]["inputs"]["image"] = image_filename
        else:
            print(f"警告：无法从 image_input 参数中解析出有效的图像文件名。")

    # IMAGE MASK
    image_mask_input_node_id = find_node_id_by_title(workflow, "LoadImage(Mask)")
    if image_mask_input_node_id and 'image_input' in parameters:
        image_mask_input_info = parameters['image_input']
        image_filename = None
        # 场景1: 图像来自一个已存在的节点   
        if image_mask__input_info.get('type') == 'from_node':
            source_node_id = image_mask__input_info.get('node_id')
            source_node = database.get_node(source_node_id)
            if source_node and source_node.get('assets', {}).get('images'):
                image_url = source_node['assets']['images'][0]
                parsed_url = urllib.parse.urlparse(image_url)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                
                filename = query_params.get('filename', [None])[0]
                subfolder = query_params.get('subfolder', [''])[0]
                
                if filename:
                # 构建源文件和目标文件的完整路径
                    source_path = os.path.join(COMFYUI_OUTPUT_PATH, subfolder, filename)
                    destination_path = os.path.join(COMFYUI_INPUT_PATH, filename)
                    # 检查源文件是否存在，然后复制
                    if os.path.exists(source_path):
                        try:
                            with open(source_path, 'rb') as f_read:
                                with open(destination_path, 'wb') as f_write:
                                    f_write.write(f_read.read())
                            image_filename = filename
                            print(f"    - 已将文件 '{filename}' 从output手动复制到input目录。")
                        except IOError as e:
                            print(f"    -  错误: 文件复制失败: {e}")
                    else:
                        print(f"    - 错误: 源文件 '{source_path}' 不存在，无法复制。")
                
         # 场景2: 图像是用户新上传的
        elif image_mask_input_info.get('type') == 'new_upload':
             image_filename = image_input_info.get('filename')
        if image_filename:
            workflow[image_input_node_id]["inputs"]["image"] = image_filename
        else:
            print(f"警告：无法从 image_input 参数中解析出有效的图像文件名。")


    try:
        # --- 调用ComfyUI并等待结果 ---
        queued_prompt = queue_comfyui_prompt(workflow)
        prompt_id = queued_prompt['prompt_id']
        
        # 使用WebSocket等待并获取输出
        outputs = get_comfyui_outputs(prompt_id)

    except Exception as e:
        print(f"执行ComfyUI工作流时出错: {e}")
        return jsonify({"error": "Failed to execute ComfyUI workflow."}), 500

    # --- 在数据库中记录新节点 ---
    new_node_id = database.add_node(
        tree_id=tree_id,
        parent_id=parent_id,
        module_id=module_id,
        parameters=parameters,
        assets=outputs # 直接保存从ComfyUI获取的输出信息
    )

    # --- 返回更新后的树结构 ---
    updated_tree = database.get_tree_as_json(tree_id)
    return jsonify(updated_tree), 201


# --- 【核心修改】视频拼接 API 接口 (使用 moviepy) ---
@app.route('/api/stitch', methods=['POST'])
def stitch_videos():
    data = request.get_json()
    clips_data = data.get('clips') # <-- 接收包含类型的数据

    if not clips_data or len(clips_data) < 1: # 至少需要一个片段
        return jsonify({"error": "需要至少一个片段路径"}), 400

    moviepy_clips = [] # 用于存放 VideoFileClip 或 ImageClip 对象
    default_image_duration = 3 # 图片作为视频片段的默认时长（秒）
    target_fps = 24 # 目标输出帧率 (可以根据需要调整)

    try:
        # --- 1. 将相对路径转换为绝对路径并创建 MoviePy Clip 对象 ---
        for clip_info in clips_data:
            relative_path = clip_info.get('path')
            clip_type = clip_info.get('type') # 'image' 或 'video'

            if not relative_path or not clip_type:
                raise ValueError(f"片段信息不完整: {clip_info}")

            # 解析相对路径
            parsed_url = urllib.parse.urlparse(relative_path)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            filename = query_params.get('filename', [None])[0]
            subfolder = query_params.get('subfolder', [''])[0]
            if not filename:
                raise ValueError(f"无法从路径解析文件名: {relative_path}")

            # 构建绝对路径
            # 【重要】需要区分图片和视频可能在不同的目录下
            if clip_type == 'video':
                # 假设视频都在 output/video 子目录下
                full_path = os.path.join(COMFYUI_OUTPUT_PATH, 'video', filename)
                
            else: # 图片
                 # 假设图片直接在 output 目录下
                full_path = os.path.join(COMFYUI_OUTPUT_PATH, filename)
                

            if not os.path.exists(full_path):
                # 尝试去掉 subfolder 查找，兼容旧数据或不同工作流
                full_path_alt = os.path.join(COMFYUI_OUTPUT_PATH, filename)
                if not os.path.exists(full_path_alt):
                   raise FileNotFoundError(f"媒体文件未找到: {full_path} 或 {full_path_alt}")
                else:
                    full_path = full_path_alt # 使用备用路径


            # 创建 MoviePy Clip 对象
            if clip_type == 'video':
                print(f"加载视频: {full_path}")
                video_clip = VideoFileClip(full_path)
                # 可选：统一设置帧率，避免拼接问题
                # if video_clip.fps != target_fps:
                #     print(f"  调整帧率从 {video_clip.fps} 到 {target_fps}")
                #     video_clip = video_clip.set_fps(target_fps)
                moviepy_clips.append(video_clip)
            else: # 图片
                print(f"加载图片并创建为 {default_image_duration} 秒片段: {full_path}")
                # 【核心修正】先创建 ImageClip，然后直接设置 duration 属性
                image_clip = ImageClip(full_path)
                image_clip.duration = default_image_duration
                # 【核心修正】设置 fps 属性 (注意：是 fps 不是 set_fps 方法)
                image_clip.fps = target_fps
                moviepy_clips.append(image_clip)

        if not moviepy_clips:
             raise ValueError("未能成功加载任何媒体片段")

        # --- 2. 使用 moviepy 拼接视频 ---
        print("使用 moviepy 拼接片段...")
        final_clip = concatenate_videoclips(moviepy_clips, method="compose") # compose 更稳定

        # --- 3. 写入输出文件 ---
        output_filename = f"stitched_{uuid.uuid4()}.mp4"
        output_path_absolute = os.path.join(STITCHED_OUTPUT_FOLDER, output_filename)
        print(f"写入拼接后的视频到: {output_path_absolute}")
        # 确保输出有统一的帧率和兼容的编码
        final_clip.write_videofile(
            output_path_absolute,
            codec="libx264",    # H.264 编码，兼容性好
            audio_codec="aac",  # AAC 音频编码
            fps=target_fps,     # 指定输出帧率
            threads=4,          # 使用多线程加速
            preset='medium'     # 速度与质量平衡
        )

        # --- 4. 关闭所有打开的文件句柄 ---
        for clip in moviepy_clips:
            clip.close()
        final_clip.close()

        # --- 5. 返回结果 URL ---
        output_url = f"/stitched/{output_filename}"
        print(f"拼接完成，访问 URL: {output_url}")
        return jsonify({"output_url": output_url}), 200

    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
         return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"Moviepy 处理过程中发生错误: {type(e).__name__} - {e}")
        # 清理 clip 对象
        for clip in moviepy_clips:
            try: clip.close()
            except: pass
        return jsonify({"error": f"视频拼接失败: {e}"}), 500

# --- 【不变】用于下载/访问拼接后视频的路由 ---
@app.route('/stitched/<filename>')
def download_stitched_video(filename):
    try:
        return send_from_directory(STITCHED_OUTPUT_FOLDER, filename, as_attachment=False)
    except FileNotFoundError:
        abort(404)

@app.route('/api/database/download', methods=['GET'])
def download_database():
    """提供SQLite数据库文件的下载"""
    try:
        backend_directory = os.path.dirname(os.path.abspath(__file__))
        return send_from_directory(
            directory=backend_directory,
            path='video_tree.db',
            as_attachment=True,
            download_name='video_tree_backup.db'
        )
    except FileNotFoundError:
        return jsonify({"error": "数据库文件未找到!"}), 404
 
# --- 4. 启动应用 ---

if __name__ == '__main__':
    # 在启动应用前，确保数据库和表已创建
    database.init_db()
    
    # 初始化时可以创建一个默认的树/项目
    if not database.get_tree_as_json(1):
        tree_id = database.create_tree("我的第一个项目")
        database.add_node(tree_id, None, "Init", {"description": "项目根节点"})
        print(f"已创建默认项目，ID为: {tree_id}")

    app.run(host='0.0.0.0', port=5000, debug=True)

