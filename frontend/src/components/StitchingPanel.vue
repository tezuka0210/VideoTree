<template>
  <div class="bg-white rounded shadow p-4">
    <h2 class="text-l font-semibold mb-4 text-gray-700">视频拼接序列</h2>
    <div
      id="stitching-panel-wrapper"
      class="bg-gray-100 border border-dashed border-gray-300 min-h-[100px]"
      @wheel.prevent="handleZoom" >
      <canvas id="timeline-ruler" style="width: 100%; height: 30px; background: #fafafa;"></canvas>
      <div
        id="stitching-panel"
        class="bg-gray-100 p-4 rounded border border-dashed border-gray-300 min-h-[100px]"
        @dragover.prevent="handleDragOverContainer"
        @dragleave="handleDragLeaveContainer"
        @drop="handleDropContainer"
        :class="{ 'drag-over': isDraggingOverContainer }"
      >
        <div id="clips-container">
          <div
            v-for="(clip, index) in clips"
            :key="clip.nodeId"
            class="clip-item"
            :class="{ 'dragging': draggedClipIndex === index }"
            :style="{ width: getClipWidth(clip) }"
            draggable="true"
            @dragstart="handleDragStart(index, $event)"
            @dragover.prevent="handleDragOverItem(index)"
            @dragleave="handleDragLeaveItem"
            @drop.prevent="handleDropOnItem(index)"
            @dragend="handleDragEnd"
          >
            <img
              v-if="clip.type === 'image'"
              :src="clip.thumbnailUrl"
              class="thumb"
              draggable="false"
            />
            <video
              v-else
              :src="clip.thumbnailUrl"
              class="thumb"
              autoplay loop muted playsinline
              preload="metadata"
              draggable="false"
            ></video>

            <span class="remove-btn" @click.stop="onRemoveClick(index)">×</span>
            <div
              class="clip-controls"
              style="padding: 4px; font-size: 10px; background: #f9f9f9;"
              @mousedown.stop
            >
              <div v-if="clip.type === 'image'">
                <label>时长:
                  <input
                    type="number"
                    :value="clip.duration"
                    @change="onTimeChange(clip, 'duration', $event)"
                    step="0.1" min="0.1" class="w-full"
                  />
                </label>
              </div>
              <div v-else>
                <label>开始:
                  <input
                    type="number"
                    :value="clip.startTime"
                    @change="onTimeChange(clip, 'startTime', $event)"
                    step="0.1" min="0" :max="clip.totalDuration" class="w-full"
                  />
                </label>
                <label>结束:
                  <input
                    type="number"
                    :value="clip.endTime"
                    @change="onTimeChange(clip, 'endTime', $event)"
                    step="0.1" min="0" :max="clip.totalDuration" class="w-full"
                  />
                </label>
              </div>
            </div>

            <div
              v-if="draggedOverIndex === index"
              class="absolute inset-0 bg-blue-500 opacity-50 border-2 border-blue-700 pointer-events-none"
              style="border-radius: 4px;"
            ></div>

          </div>
          <span v-if="clips.length === 0" id="clips-placeholder" class="text-gray-500 italic">
            从上方历史树中添加视频片段到此区域...
          </span>
        </div>
      </div>
    </div>
    <button
      id="stitch-button"
      class="mt-4 w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg transition-colors disabled:bg-gray-400"
      :disabled="clips.length === 0 || props.isStitching"
      @click="onStitchClick"
    >
      {{ props.isStitching ? '正在拼接...' : '拼接视频' }}
    </button>
    <div id="stitch-result" class="mt-3 text-center">
      <a
        v-if="props.stitchResultUrl"
        :href="props.stitchResultUrl"
        target="_blank"
        class="text-blue-500 hover:underline ml-2"
      >
        拼接完成！点击下载/预览
      </a>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import type { StitchingClip, ImageClip, VideoClip } from '@/composables/useWorkflow'
import * as VideoEditingTimeline from 'video-editing-timeline'

// --- 1. Props (由 App.vue 传入) ---
const clips = defineModel<StitchingClip[]>('clips', { required: true })
const props = defineProps<{
  isStitching: boolean;
  stitchResultUrl: string | null;
}>()

// --- 2. Emits (向 App.vue 传出) ---
const emit = defineEmits<{
  (e: 'remove-clip', index: number): void;
  (e: 'stitch'): void;
}>()

// --- 3. 本地状态 (用于拖拽) ---
const draggedClipIndex = ref<number | null>(null)
const draggedOverIndex = ref<number | null>(null)
const isDraggingOverContainer = ref(false)

// --- 4. 样式计算 (核心修改) ---

// (响应式) 缩放状态
const pixelsPerSecond = ref(20) // 初始值：每秒 20 像素

/**
- 根据片段时长计算其在时间轴上的宽度 (现在是动态的)
*/
function getClipWidth(clip: StitchingClip): string {
  let clipDuration: number;
  if (clip.type === 'video') {
    clipDuration = clip.endTime - clip.startTime
  } else {
    clipDuration = clip.duration
  }
  return `${Math.max(50, clipDuration * pixelsPerSecond.value)}px`
}


// --- 5. 时间轴标尺 (Timeline Ruler) 逻辑 (核心修改) ---

// (获取构造函数) 
const Constructor = (VideoEditingTimeline as any).default || VideoEditingTimeline

/**
- (新) 绘制/重绘时间轴的函数
- 这是解决问题的关键。我们不再存储实例，而是每次都重新创建它。
*/
function drawTimeline(pxPerSec: number) {
  const canvasEl = document.getElementById('timeline-ruler') as HTMLCanvasElement
  if (!canvasEl) {
    console.error('Canvas #timeline-ruler not found')
    return
  }

  // 动态调整刻度，让其更智能
  let newScaleTime = 1;
  let newScalePx = pxPerSec;

  if (pxPerSec > 100) { // 放大时，刻度更密
    newScaleTime = 0.5;
    newScalePx = pxPerSec * 0.5;
  } else if (pxPerSec < 10) { // 缩小时，刻度更疏
    newScaleTime = 5;
    newScalePx = pxPerSec * 5;
  }
  // 每次都创建一个 新 的实例。
  // 这会清除旧的 canvas 并绘制新的。
  new Constructor({
    el: '#timeline-ruler', // <-- 关键：确保这和你 <template> 中的 ID 一致
    canvasWidth: canvasEl.clientWidth,
    canvasHeight: 30,
    minimumScale: newScalePx,
    minimumScaleTime: newScaleTime,
  })
}

onMounted(() => {
  // 初始绘制
  drawTimeline(pixelsPerSecond.value)
})

watch(pixelsPerSecond, (newPxPerSec) => {
  // 缩放时重绘
  drawTimeline(newPxPerSec)
})
// --- 5. 事件处理器 ---

function onRemoveClick(index: number) {
  emit('remove-clip', index)
}

function onStitchClick() {
  emit('stitch')
}

/**
 * (重要) 处理时间输入框的更改，包含验证逻辑
 */
function onTimeChange(
  clip: StitchingClip,
  field: 'duration' | 'startTime' | 'endTime',
  event: Event
) {
  const target = event.target as HTMLInputElement
  let value = parseFloat(target.value)

  if (isNaN(value) || value < 0) {
    value = 0
  }

  // A. 验证逻辑
  if (clip.type === 'image' && field === 'duration') {
    if (value < 0.1) value = 0.1
    clip.duration = value // 直接修改 prop
  }
  else if (clip.type === 'video') {
    if (field === 'startTime') {
      if (value >= clip.endTime) value = clip.endTime - 0.1
      clip.startTime = value // 直接修改 prop
    }
    if (field === 'endTime') {
      if (value <= clip.startTime) value = clip.startTime + 0.1
      if (value > clip.totalDuration) value = clip.totalDuration
      clip.endTime = value // 直接修改 prop
    }
  }

  // B. 将验证后的值写回输入框，防止UI与数据不同步
  target.value = value.toFixed(field === 'duration' ? 1 : 2)
}
/**
- (新) 处理缩放的事件
*/
function handleZoom(event: WheelEvent) {
  // event.deltaY > 0 是缩小, < 0 是放大
  const zoomFactor = event.deltaY > 0 ? 0.9 : 1.1
  const newPixelsPerSecond = pixelsPerSecond.value * zoomFactor
  // 限制缩放范围
  pixelsPerSecond.value = Math.max(5, Math.min(500, newPixelsPerSecond))
}

// --- 6. 拖拽与排序 (Drag and Drop) 逻辑 ---

function handleDragStart(index: number, event: DragEvent) {
  draggedClipIndex.value = index
  event.dataTransfer!.effectAllowed = 'move'
  event.dataTransfer!.setData('text/plain', index.toString())
  // 延迟添加 dragging 类，以允许浏览器捕获拖拽快照
  setTimeout(() => {
    const el = document.querySelector(`[data-index="${index}"]`)
    if(el) el.classList.add('dragging')
  }, 0)
}

function handleDragOverItem(targetIndex: number) {
  draggedOverIndex.value = targetIndex
  isDraggingOverContainer.value = false
}

function handleDragLeaveItem() {
  draggedOverIndex.value = null
}

function handleDragOverContainer() {
  // 仅在拖到容器空白处时才高亮容器
  if (draggedOverIndex.value === null) {
    isDraggingOverContainer.value = true
  }
}

function handleDragLeaveContainer() {
  isDraggingOverContainer.value = false
}

/**
 * (核心) 当在另一个片段上松开时
 */
function handleDropOnItem(targetIndex: number) {
  if (draggedClipIndex.value === null) return

  const sourceIndex = draggedClipIndex.value
  if (sourceIndex === targetIndex) return

  // (重要) Vue 3 v-model 方式:
  // 1. 复制数组
  const newList = [...clips.value]
  // 2. 从数组中移除拖拽的元素
  const [itemToMove] = newList.splice(sourceIndex, 1)
  // 3. 将元素插入到目标位置
  if (itemToMove) {     
    newList.splice(targetIndex, 0, itemToMove)   
  }      

  // 4. (核心) 更新 v-model
  clips.value = newList
  draggedOverIndex.value = null
}

/**
 * (核心) 当在容器的空白处松开时 (移动到末尾)
 */
function handleDropContainer() {
  if (draggedClipIndex.value === null) return
  if (!isDraggingOverContainer.value) return // 确保是拖到空白处

  const sourceIndex = draggedClipIndex.value
  const newList = [...clips.value]
  const [itemToMove] = newList.splice(sourceIndex, 1)
  
  if (itemToMove) {     
    newList.push(itemToMove) // 添加到末尾   
  }      
  clips.value = newList
}

function handleDragEnd() {
  // 清理所有状态
  draggedClipIndex.value = null
  draggedOverIndex.value = null
  isDraggingOverContainer.value = false
}
</script>

<style scoped>
/* 我们在这里只放局部的拖拽样式。
  .clip-item, .thumb, .remove-btn 等样式
  都已在全局的 src/style.css 中定义。
*/

/* 拖拽时，被拖拽的那个元素的占位符样式 (原版 .dragging) */
.clip-item.dragging {
  opacity: 0.3;
  transform: scale(0.95);
}

/* 拖拽时，目标容器的样式 (原版 .drag-over) */
#stitching-panel.drag-over {
  border-style: solid;
  border-color: #3b82f6; /* Blue-500 /
  background-color: #eff6ff; / Blue-50 */
}
</style>