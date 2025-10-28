<template>
  <div class="container mx-auto p-4 h-full flex flex-col">
    <header class="text-center mb-6">
      <h1 class="text-3xl font-semibold text-gray-800">工作流创作与回顾</h1>
      <p id="status" class="text-gray-500 mt-1">{{ statusText }}</p>
    </header>

    <main class="grid grid-cols-3 gap-6 flex-1 min-h-0">

      <div class="col-span-2 flex flex-col gap-4 min-h-0">
        <WorkflowTree
          class="flex-1 min-h-0"
          :nodes="allNodes"
          v-model:selectedIds="selectedParentIds"
          @delete-node="handleDeleteNode"
          @add-clip="addClipToStitch"
          @open-preview="openPreview"
        />

        <StitchingPanel
          v-model:clips="stitchingClips"
          :is-stitching="isStitching"
          :stitch-result-url="stitchResultUrl"
          @remove-clip="removeClipFromStitch"
          @stitch="onStitchRequest"
        />
      </div>

      <div class="col-span-1 overflow-y-auto">
        <WorkflowForm
          :selected-ids="selectedParentIds"
          :is-generating="isGenerating"
          @generate="handleGenerate"
          @upload="handleFileUpload"
        />
      </div>
    </main>
    <PreviewModal
      v-if="isPreviewOpen"
      :url="previewMedia.url"
      :type="previewMedia.type"
      @close="closePreview"
    />

  </div>
</template>

<script setup lang="ts">
// --- 1. 导入 Vue 核心功能 ---
import { onMounted, ref } from 'vue'

// --- 2. 导入我们的 Composable (状态和逻辑) ---
import { useWorkflow } from '@/composables/useWorkflow'

// --- 3. 导入所有子组件 ---
import WorkflowTree from './components/WorkflowTree.vue'
import WorkflowForm from './components/WorkflowForm.vue'
import StitchingPanel from './components/StitchingPanel.vue'
import PreviewModal from './components/PreviewModal.vue'

// --- 4. (核心) 初始化 Composable ---
// 这会创建所有的响应式状态 (ref, reactive) 和函数
const {
  // 状态 (State)
  statusText,
  allNodes,
  selectedParentIds,
  stitchingClips,
  isGenerating,
  isStitching,
  isPreviewOpen,
  previewMedia,

  // 逻辑 (Actions)
  loadAndRender,
  handleGenerate,
  handleFileUpload,
  handleDeleteNode,
  addClipToStitch,
  removeClipFromStitch,
  handleStitchRequest,
  openPreview,
  closePreview,
} = useWorkflow()

// --- 5. App.vue 自己的本地状态 ---
// 用于存储拼接完成后的下载 URL
const stitchResultUrl = ref<string | null>(null)

// --- 6. 事件处理包装器 ---
// (因为 handleStitchRequest 会返回一个值, 我们需要在这里接收它)
async function onStitchRequest() {
  stitchResultUrl.value = null // 1. 清除旧的 URL
  const resultUrl = await handleStitchRequest() // 2. 调用 composable 里的函数
  if (resultUrl) {
    stitchResultUrl.value = resultUrl // 3. 将返回的 URL 存入本地状态
  }
}

// --- 7. 生命周期钩子 ---
// (当 App.vue 组件被挂载到页面上时，执行一次)
onMounted(() => {
  // 调用 composable 中的函数，加载初始数据
  loadAndRender()
})
</script>