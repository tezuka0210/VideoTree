# AI 视频工作流管理系统 (本地演示版)

本项目是一个用于管理和执行 AI 图像/视频生成工作流的可视化平台。它旨在将 ComfyUI 的复杂能力封装在一个更友好、可追溯的界面中，用于介绍视频的AIGC内容生产。

这个版本是**本地演示版**

---

## 核心功能

* **可视化工作流**: 以树状图展示所有生成历史，节点间的父子关系一目了然。
* **查看节点详情**: 点击节点卡片，可查看该节点生成的提示词 (Prompt)。
* **视频/图片预览**: 点击节点上的缩略图可放大预览。
* **视频拼接**: 可将任意节点的结果添加到拼接序列，并生成一个新视频。

---

### 依赖环境

请确保您的电脑已安装：
* Python (3.8 或更高版本)
* Node.js (v18 或更高版本)

### 步骤 1：启动后端 (Python Flask)

1.  打开一个终端，进入 `video_tree/backend/` 目录。
    ```bash
    cd path/to/video_tree/backend
    ```
2. 启动后端服务器：
    ```bash
    python app.py
    ```

### 步骤 2：启动前端 (Vue.js)

1.  打开新的终端，进入 `video_tree/frontend/` 目录。
    ```bash
    cd path/to/video_tree/frontend
    ```
2.  安装 Node.js 依赖：
    ```bash
    npm install
    ```
3.  启动前端开发服务器：
    ```bash
    npm run dev
    ```

### 步骤 3：访问应用

打开浏览器访问：
`http://localhost:5173`

---

## 如何使用

* **查看节点**: 页面加载后，会看到数据库中已有的工作流。
* **查看 Prompt**: 对于有 `positive_prompt` 参数的节点 (如文生图节点)，卡片底部会自动显示提示词。
* **生成**:
    1.  红：输入内容预处理工作流
    2.  黄：生图工作流
    3.  绿：生视频工作流
* **视频拼接**:
    1.  点击任意节点缩略图上的 "▶" 按钮，将其添加到下方的拼接栏。
    3.  点击拼接栏右下角的“开始拼接”按钮，系统将生成拼接后的视频。



* **工作流存储位置**：video_tree/backend/workflows
  - CameraControl.json 运镜工作流
    - CLIP Text Encode (Negative Prompt) > text
    - CLIP Text Encode (Positive Prompt) > text
    - KSamplerAdvanced2 > noise_seed
    - LoadImage > image
    - CreateVideo > fps
    - Size_Setting > camera_pose（可选Pan Up, Pan Down, Pan Left, Pan Right, Zoom In, Zoom Out, Anti Clockwise (ACW), ClockWise (CW))
    - Size_Setting > width
    - Size_Setting > height
    - Size_Setting > speed
    - Size_Setting > length
    - WanCameraImageToVideo > batch_size
  - FrameInterpolation 补帧
    - LoadVideo > file
    - RIFE VFI > multiplier
    - CreateVideo > fps
  - ImageCanny 提取线稿
    - LoadImage > image
    - Canny > low_threshold
    - Canny >high_threshold
  - ImageGenerateImage
    - 增加lora选择项
      - 选择无 > ImageGenerateImage_Basic
      - 选择canny > ImageGenerateImage_Canny
    - LoadImage > image
    - CLIP Text Encode (Positive Prompt) > text
    - KSampler > seed
    - KSampler > steps
    - FluxGuidance > guidance
    - Size_Setting > width
    - Size_Setting > height
    - Size_Setting > batch_size
  - ImageGenerateVideo
    - CLIP Text Encode (Negative Prompt) > text
    - CLIP Text Encode (Positive Prompt) > text
    - KSamplerAdvanced2 > noise_seed
    - LoadImage > image
    - CreateVideo > fps
    - Size_Setting > width
    - Size_Setting > height
    - Size_Setting > batch_size
    - Size_Setting > length
  - ImageHDRestoration
    - CLIP Text Encode (Positive Prompt) > text
    - CLIP Text Encode (Negative Prompt) > text
    - KSampler > seed
    - KSampler > denoise
    - LoadImage > image
  - ImageMerging 双图合并
    - LoadImage > image
    - LoadImage(Move) > image
    - Image Stitch > stitch (可选top, left, bottom, right）
  - PartialRepainting局部重绘
    - CLIP Text Encode (Positive Prompt) > text
    - KSampler > seed
    - KSampler > steps
    - FluxGuidance > guidance
    - LoadImage > image
    - LoadImage （Mask) > image
  - Put_It_Here
    - CLIP Text Encode (Positive Prompt) > text
    - KSampler > seed
    - KSampler > steps
    - FluxGuidance > guidance
    - LoadImage > image
    - LoadImage （Mask) > image
    - RepeatLatentBatch > amount
  - RemoveBackground去除背景
    - LoadImage > image
    - Image Rembg (Remove Background) > model
      - 可选：
        - u2net：通用显著性检测，一般不如isnet-general-use
        - u2netp：u2net的轻量级版本，轻量级的效果更差
        - u2net_human_seg：针对人像分割训练的模型
        - silueta：和u2net相同，大小减少到43Mb，方便在小内存机器上使用
        - isnet-general-use ：一个新的通用的预训练模型。
        - isnet-anime：专门针对动画人物的分割模型
    - Image Rembg (Remove Background) >  alpha_matting_foreground_threshold
    - Image Rembg (Remove Background) >  alpha_matting_background_threshold
    - Image Rembg (Remove Background) >  alpha_matting_erode_size
  - TextGenerateImage
    - CLIP Text Encode (Positive Prompt) > text
    - KSampler > seed
    - KSampler > steps
    - FluxGuidance > guidance
    - Size_Setting > width
    - Size_Setting > height
    - Size_Setting > batch_size
  - TextGenerateVideo
    - CLIP Text Encode (Negative Prompt) > text
    - CLIP Text Encode (Positive Prompt) > text
    - KSamplerAdvanced2 > noise_seed
    - CreateVideo > fps
    - Size_Setting > width
    - Size_Setting > height
    - Size_Setting > batch_size
    - Size_Setting > length
  - FLFrameToVideo
    - CLIP Text Encode (Negative Prompt) > text
    - CLIP Text Encode (Positive Prompt) > text
    - KSamplerAdvanced2 > noise_seed
    - LoadStartImage > image
    - LoadLastImage > image
    - CreateVideo > fps
    - Size_Setting > width
    - Size_Setting > height
    - Size_Setting > batch_size
    - Size_Setting > length