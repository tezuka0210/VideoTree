<template>
  <div class="bg-white rounded shadow p-6">
    
    <div id="workflow-form" class="space-y-4">
      <div>
        <label class="block text-sm font-medium text-gray-600 mb-1">父节点</label>
        <input
          id="selected-node-input"
          type="text"
          :value="selectedNodeText"
          class="w-full bg-gray-100 border border-gray-300 rounded-md p-2 text-gray-500 text-sm"
          readonly
        >
      </div>

      <div>
        <label for="module-select" class="block text-sm font-medium text-gray-600 mb-1">选择模块</label>
        <select id="module-select" v-model="moduleId" class="w-full bg-white border border-gray-300 rounded-md p-2">
          <option
            v-for="module in availableModules"
            :key="module.id"
            :value="module.id"
          >
            {{ module.name }}
          </option>
          </select>
      </div>

      <div v-if="props.initialWorkflowType ==='image' || props.initialWorkflowType === 'video'">
        <label for="prompt-input" class="block text-sm font-medium text-gray-600 mb-1">Prompt</label>
        <textarea
          id="prompt-input"
          rows="4"
          v-model="prompt"
          class="w-full bg-white border border-gray-300 rounded-md p-2"
          placeholder="请输入您的创意..."
        ></textarea>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div v-if="props.initialWorkflowType ==='image'">
          <label for="seed-input" class="block text-sm font-medium text-gray-600 mb-1">Seed</label>
          <input
            type="number"
            id="seed-input"
            v-model.number="seed"
            @keydown.enter.prevent
            class="w-full bg-white border border-gray-300 rounded-md p-2"
            placeholder="随机"
          >
        </div>
        <div v-if="props.initialWorkflowType ==='image'">
          <label for="steps-input" class="block text-sm font-medium text-gray-600 mb-1">Steps</label>
          <input
            type="number"
            id="steps-input"
            v-model.number="steps"
            @keydown.enter.prevent
            class="w-full bg-white border border-gray-300 rounded-md p-2"
          >
        </div>
        <div v-if="props.initialWorkflowType ==='image' || props.initialWorkflowType === 'video'">
          <label for="cfg-input" class="block text-sm font-medium text-gray-600 mb-1">CFG</label>
          <input
            
            type="number"
            id="cfg-input"
            step="0.1"
            v-model.number="cfg"
            @keydown.enter.prevent
            class="w-full bg-white border border-gray-300 rounded-md p-2"
          >
        </div>
        <div v-if="props.initialWorkflowType ==='image'">
          <label for="denoise-input" class="block text-sm font-medium text-gray-600 mb-1">Denoise</label>
          <input
            type="number"
            id="denoise-input"
            step="0.05"
            v-model.number="denoise"
            @keydown.enter.prevent
            class="w-full bg-white border border-gray-300 rounded-md p-2"
          >
        </div>
      </div>
      <div v-if="props.initialWorkflowType === 'video'">
          <label for="noise_seed-input" class="block text-sm font-medium text-gray-600 mb-1">Seed</label>
          <input
            type="number"
            id="noise_seed-input"
            v-model.number="seed"
            @keydown.enter.prevent
            class="w-full bg-white border border-gray-300 rounded-md p-2"
            placeholder="随机"
          >
        </div>

      <div>
        <label for="image-upload" class="block text-sm font-medium text-gray-600 mb-1">图片输入 (可选)</label>
        <input
          type="file"
          id="image-upload"
          ref="fileInputRef"
          :disabled="props.isGenerating"
          @change="onFileChange"
          accept="image/*"
          class="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-100 file:text-blue-700 hover:file:bg-blue-200"
        >
        <p class="text-xs text-gray-500 mt-1">提示：上传新图将覆盖父节点图像。</p>
      </div>

      <div class="pt-2">
        <button
          id="generate-btn"
          :disabled="isGenerating"
          @click="onGenerateClick"
          class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg flex items-center justify-center transition-colors disabled:bg-gray-400"
        >
          <span id="button-text">{{isGenerating ? '生成中...' : '开始生成' }}</span>
          <div
            id="button-loader"
            :class="['loader ease-linear rounded-full border-4 border-t-4 border-gray-200 h-6 w-6 ml-3', { 'hidden': !isGenerating }]"
          ></div>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'

// (核心修改) 定义所有可用模块
const allModules = [
  { id: 'ImageCanny', name: 'ImageCanny', type: 'preprocess' },
  { id: 'RemoveBackground', name: 'RemoveBackground', type: 'preprocess' },
  { id: 'ImageMerging', name: 'ImageMerging', type: 'preprocess' },

  { id: 'TextGenerateImage', name: 'TextToImage', type: 'image' },
  { id: 'ImageGenerateImage_Basic', name: 'ImageToImage', type: 'image' },
  { id: 'ImageGenerateImage_Canny', name: 'CannyToImage', type: 'image' },
  { id: 'PartialRepainting', name: 'PartialRepainting', type: 'image' },
  { id: 'ImageHDRestoration', name: 'ImageHDRestoration', type: 'image' },
  { id: 'Put_It_Here', name: 'ObjectMigration', type: 'image' },

  { id: 'TextGenerateVideo', name: 'TextToVideo', type: 'video' },
  { id: 'ImageGenerateVideo', name: 'ImageToVideo', type: 'video' },
  { id: 'CameraControl', name: 'CameraControl', type: 'video' },
  { id: 'FrameInterpolation', name: 'FrameInterpolation', type: 'video' },
  { id: 'FLFrameToVideo', name: 'FisrtAndLastFrameControl', type: 'video' },
  
];

// (核心修改) 创建一个计算属性，根据传入的类型过滤模块列表
const availableModules = computed(() => {
  if (!props.initialWorkflowType) {
    return allModules; // 如果没有类型，显示全部 (或只显示默认?)
  }
  return allModules.filter(module => module.type === props.initialWorkflowType);
});

// --- 1. Props (从 App.vue 传入) ---

// 定义组件接收的 props，TypeScript 方式
const props = defineProps<{
  selectedIds: string[];
  isGenerating: boolean;
  initialModuleId: string | null;
  initialWorkflowType: 'preprocess' | 'image' | 'video' | null;
}>()

// --- 2. Emits (向 App.vue 传出) ---

// 定义组件可以发出的事件
const emit = defineEmits<{
  (e: 'generate', moduleId: string, parameters: Record<string, any>): void;
  (e: 'upload', file: File): void;
}>()

// --- 3. 本地响应式状态 (Local State) ---

// 表单字段的本地状态
const moduleId = ref('TextGenerateImage')
const prompt = ref('')
const seed = ref<number | null>(null) // null 表示随机
const steps = ref(20)
const cfg = ref(7.5)
const denoise = ref(0.8)

// 对 <input type="file"> DOM 元素的引用
const fileInputRef = ref<HTMLInputElement | null>(null)


// (Core Change 13) Watch the prop and update local state
watch(() => props.initialModuleId, (newModuleId) => {
  if (newModuleId) {
    moduleId.value = newModuleId;
  }
}, { immediate: true }); // immediate: true ensures it runs on mount
// --- 4. 计算属性 (Computed) ---

// 动态计算父节点输入框的显示文本
// 这替换了原版 JS 中的 updateSelectedNodeInput() 函数
const selectedNodeText = computed(() => {
  // VVVV 添加这个日志 VVVV
  console.log(
    `%c[Form] 5. Computed 正在重新计算...`,
    'color: #FFA500; font-weight: bold;'
  );
  // ^^^^ 添加这个日志 ^^^^
  const count = props.selectedIds.length
  if (count === 0) {
    return '未选择 (将创建根节点)'
  } 
  if (count === 1) {
    // (新) 我们先把[0]取出来
    const firstId = props.selectedIds[0] 
    // (新) 我们再检查它是不是真的存在 (虽然在 count === 1 时它一定在)
    // 这一步能 100% 让 TypeScript 闭嘴
    if (firstId) {
      return `已选择 (1): ${firstId.substring(0, 8)}...`
    }
    // 理论上走不到这里，但这是个安全出口
    return '错误：无法读取ID'
  }

  // 专为 ImageMerging 优化提示
  if (moduleId.value === 'ImageMerging' && count === 2) {
    return `已选择 2 个节点 (合并就绪)`
  }

  return `已选择 (${count}) 个节点`
})


watch(() => props.selectedIds, (newIds) => {
  console.log("%c--- 表单(Form) 收到 Prop 更新 ---", "color: blue; font-weight: bold");
  console.log("  表单收到的新 IDs:", newIds);
}, { deep: true });
// --- 5. 事件处理器 (Methods) ---

/**
 * 当文件上传框内容改变时触发
 */
function onFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0] // 获取选中的第一个文件

  if (file) {
    // (核心) 将文件 emit 出去，让 App.vue 的 useWorkflow.ts 去处理
    emit('upload', file)
  }

  // (重要) 清空文件输入框
  // 这样用户才能在上传同一个文件时再次触发 change 事件
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

/**
 * 当点击 "开始生成" 按钮时触发
 */
function onGenerateClick() {
  // 1. 组装参数
  const parameters: Record<string, any> = {
    positive_prompt: prompt.value,
    // 如果 seed.value 是 null 或 0，就生成一个随机数
    seed: seed.value || Math.floor(Math.random() * 1000000000000000),
    steps: steps.value,
    cfg: cfg.value,
    denoise: denoise.value,
  }

  // 2. (核心) 将模块ID和参数 emit 出去，让 App.vue 去处理
  emit('generate', moduleId.value, parameters)

  // 3. (可选) 生成后清空 prompt
  // prompt.value = ''
}
</script>