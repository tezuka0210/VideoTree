<template>
  <div id="workflow-form" class="space-y-4">
    <!-- 父节点提示 -->
    <div v-if="props.selectedIds.length === 0">
      <label class="block text-sm font-medium text-gray-600 mb-1">父节点</label>
      <input
        type="text"
        value="未选择 (将创建根节点)"
        class="w-full bg-gray-100 border border-gray-300 rounded-md p-2 text-gray-500 text-sm"
        readonly
      >
    </div>

    <div v-else-if="props.selectedIds.length === 1">
      <label class="block text-sm font-medium text-gray-600 mb-1">父节点:</label>
      <input
        type="text"
        :value="`节点: ${parentNode1Id?.substring(0, 8)}...`"
        class="w-full bg-gray-100 border border-gray-300 rounded-md p-2 text-gray-500 text-sm"
        readonly
      >
    </div>

    <div v-else-if="props.selectedIds.length === 2" class="space-y-2">
      <p v-if="moduleId === 'ImageMerging'" class="text-xs font-medium text-green-600">合并就绪</p>
      <div>
        <label class="block text-sm font-medium text-gray-600 mb-1">父节点 1:</label>
        <input
          type="text"
          :value="`节点: ${parentNode1Id?.substring(0, 8)}...`"
          class="w-full bg-gray-100 border border-gray-300 rounded-md p-2 text-gray-500 text-sm"
          readonly
        >
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-600 mb-1">父节点 2:</label>
        <input
          type="text"
          :value="`节点: ${parentNode2Id?.substring(0, 8)}...`"
          class="w-full bg-gray-100 border border-gray-300 rounded-md p-2 text-gray-500 text-sm"
          readonly
        >
      </div>
    </div>

    <!-- 模块选择 -->
    <div>
      <label for="module-select" class="block text-sm font-medium text-gray-600 mb-1">选择模块</label>
      <select
        id="module-select"
        v-model="moduleId"
        class="w-full bg-white border border-gray-300 rounded-md p-2"
      >
        <option
          v-for="module in availableModules"
          :key="module.id"
          :value="module.id"
        >
          {{ module.name }}
        </option>
      </select>
    </div>

    <!-- 动态参数 -->
    <div
      v-for="param in currentParameters"
      :key="param.id"
      class="parameter-item"
    >
      <label :for="param.id" class="block text-sm font-medium text-gray-600 mb-1">
        {{ param.label }}
      </label>

      <input
        v-if="param.type === 'number'"
        type="number"
        :id="param.id"
        v-model.number="parameterValues[param.id]"
        :step="param.step"
        :min="param.min"
        :max="param.max"
        :placeholder="param.placeholder"
        @keydown.enter.prevent
        class="w-full bg-white border border-gray-300 rounded-md p-2"
      />

      <input
        v-else-if="param.type === 'text'"
        type="text"
        :id="param.id"
        v-model="parameterValues[param.id]"
        :placeholder="param.placeholder"
        class="w-full bg-white border border-gray-300 rounded-md p-2"
      />

      <textarea
        v-else-if="param.type === 'textarea'"
        :id="param.id"
        rows="4"
        v-model="parameterValues[param.id]"
        :placeholder="param.placeholder"
        class="w-full bg-white border border-gray-300 rounded-md p-2"
      ></textarea>

      <select
        v-else-if="param.type === 'select'"
        :id="param.id"
        v-model="parameterValues[param.id]"
        class="w-full bg-white border border-gray-300 rounded-md p-2"
      >
        <option
          v-for="option in param.options"
          :key="option"
          :value="option"
        >
          {{ option }}
        </option>
      </select>
    </div>

    <!-- 图片上传 -->
    <div>
      <label for="image-upload" class="block text-sm font-medium text-gray-600 mb-1">图片输入 (可选)</label>
      <input
        type="file"
        id="image-upload"
        ref="fileInputRef"
        :disabled="isGenerating"
        @change="onFileChange"
        accept="image/*"
        class="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-100 file:text-blue-700 hover:file:bg-blue-200"
      >
      <p class="text-xs text-gray-500 mt-1">提示：上传新图将覆盖父节点图像。</p>
    </div>

    <!-- 生成按钮 -->
    <div class="pt-2">
      <button
        id="generate-btn"
        :disabled="isGenerating"
        @click="onGenerateClick"
        class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg flex items-center justify-center transition-colors disabled:bg-gray-400"
      >
        <span id="button-text">{{ isGenerating ? '生成中...' : '开始生成' }}</span>
        <div
          id="button-loader"
          :class="['loader ease-linear rounded-full border-4 border-t-4 border-gray-200 h-6 w-6 ml-3', { 'hidden': !isGenerating }]"
        ></div>
      </button>
    </div>
  </div>
</template>

<script setup>

import { ref, toRefs, computed } from 'vue'
import { useWorkflowForm } from '@/lib/useWorkflowForm.js'

const props = defineProps({
  selectedIds: { type: Array, default: () => [] },
  isGenerating: { type: Boolean, default: false },
  initialModuleId: { type: [String,undefined] },
  initialWorkflowType: { type: [String,undefined] }
})

const emit = defineEmits(['generate', 'upload'])

/* 逻辑全部委托给 useWorkflowForm */
const {
  moduleId,
  parameterValues,
  availableModules,
  currentParameters
} = useWorkflowForm(props)

/* 父节点展示用 */
const parentNode1Id = computed(() => props.selectedIds[0] ?? null)
const parentNode2Id = computed(() => props.selectedIds[1] ?? null)

/* 文件上传 */
const fileInputRef = ref(null)
function onFileChange (e) {
  const file = e.target.files?.[0]
  if (file) emit('upload', file)
  if (fileInputRef.value) fileInputRef.value.value = ''
}

/* 生成按钮 */
function onGenerateClick () {
  /* 把最终 moduleId 与参数 emit 出去 */
  emit('generate', moduleId.value, { ...parameterValues })
}
</script>