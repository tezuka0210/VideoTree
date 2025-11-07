<template>
  <div class="bg-white rounded shadow p-4">
    <h2 class="text-l font-semibold mb-4 text-gray-700">视频拼接序列</h2>

    <!-- 时间尺 + 画布 -->
    <div
      id="stitching-panel-wrapper"
      class="bg-gray-100 border border-dashed border-gray-300 min-h-[100px]"
      @wheel.prevent="handleZoom"
    >
      <canvas
        id="timeline-ruler"
        style="width: 100%; height: 30px; background: #fafafa"
      ></canvas>

      <!-- 拖放容器 -->
      <div
        id="stitching-panel"
        class="bg-gray-100 p-4 rounded border border-dashed border-gray-300 min-h-[100px]"
        :class="{ 'drag-over': isDraggingOverContainer }"
        @dragover.prevent="handleDragOverContainer"
        @dragleave="handleDragLeaveContainer"
        @drop="handleDropContainer"
      >
        <div id="clips-container">
          <div
            v-for="(clip, index) in clips"
            :key="`${clip.nodeId}-${pixelsPerSecond}`"
            class="clip-item"
            :class="{ dragging: draggedClipIndex === index }"
            :style="{ width: clipWidths[index] }"
            draggable="true"
            @dragstart="handleDragStart(index, $event)"
            @dragover.prevent="handleDragOverItem(index)"
            @dragleave="handleDragLeaveItem"
            @drop.prevent.stop="handleDropOnItem(index)"
            @dragend="handleDragEnd"
          >
            <!-- 缩略图 -->
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
              autoplay
              loop
              muted
              playsinline
              preload="metadata"
              draggable="false"
            ></video>

            <!-- 删除按钮 -->
            <span class="remove-btn" @click.stop="remove(index)">×</span>

            <!-- 拖拽占位蓝条 -->
            <div
              v-if="draggedOverIndex === index"
              class="absolute inset-0 bg-blue-500 opacity-50 border-2 border-blue-700 pointer-events-none"
              style="border-radius: 4px"
            ></div>
          </div>

          <!-- 空态 -->
          <span v-if="clips.length === 0" id="clips-placeholder" class="text-gray-500 italic">
            Add video clips from the history tree...
          </span>
        </div>
      </div>
    </div>

    <!-- 拼接按钮 -->
    <button
      id="stitch-button"
      class="mt-4 w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg transition-colors disabled:bg-gray-400"
      :disabled="clips.length === 0 || isStitching"
      @click="stitch"
    >
      {{ isStitching ? '正在拼接...' : '拼接视频' }}
    </button>

    <!-- 结果链接 -->
    <div id="stitch-result" class="mt-3 text-center">
      <a
        v-if="stitchResultUrl"
        :href="stitchResultUrl"
        target="_blank"
        class="text-blue-500 hover:underline ml-2"
      >
        拼接完成！点击下载/预览
      </a>
    </div>
  </div>
</template>

<script setup>

import { toRefs, onMounted, watch } from 'vue'
import { useStitching } from '@/lib/useStitching.js'

const props = defineProps({
  clips:            { type: Array,  required: true },        // v-model
  isStitching:      { type: Boolean, default: false },
  stitchResultUrl:  { type: [String, null] }
})

const emit = defineEmits(['update:clips', 'stitch'])

/* 全部逻辑下沉到 useStitching */
const {
  pixelsPerSecond,
  clipWidths,
  draggedClipIndex,
  draggedOverIndex,
  isDraggingOverContainer,
  handleZoom,
  handleDragStart,
  handleDragOverItem,
  handleDragLeaveItem,
  handleDropOnItem,
  handleDragEnd,
  handleDragOverContainer,
  handleDragLeaveContainer,
  handleDropContainer,
  drawTimeline
} = useStitching(props, emit)

/* 挂载时画一次标尺 */
onMounted(() => drawTimeline(pixelsPerSecond.value))

/* 缩放变化时重绘 */
watch(pixelsPerSecond, drawTimeline)

/* 快捷方法 */
const remove = index => emit('remove-clip', index)
const stitch = () => emit('stitch')
</script>

<style scoped>
#stitching-panel.drag-over {
  border-style: solid;
  border-color: #3b82f6;
  background-color: #eff6ff;
}
.clip-item.dragging {
  opacity: 0.3;
  transform: scale(0.95);
}
</style>