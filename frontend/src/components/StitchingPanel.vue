<template>
  <div class="bg-white rounded shadow p-4">
    <!-- <h2 class="text-l font-semibold mb-4 text-gray-700">拼接序列</h2> -->

    <div
      id="stitching-panel-wrapper"
      class="bg-gray-100 border border-dashed border-gray-300 min-h-[80px] overflow-x-auto overflow-y-hidden"
      @wheel.prevent="handleZoom"
    >
      <!-- 时间轴：宽度由 drawTimeline 动态设定 -->
      <div
        id="timeline-ruler"
        class="border-b border-gray-200"
        style="background:#fafafa;"
      ></div>
      
      <div
        id="stitching-panel"
        class="bg-gray-100 p-4 rounded min-h-[80px]"
        :class="{ 'drag-over': isDraggingOverContainer === 'video' }"
        @dragover.prevent="handleDragOverContainer('video')"
        @dragleave="handleDragLeaveContainer"
        @drop="handleDropContainer('video')"
      >
        <div id="clips-container">
          <div
            v-for="(clip, index) in clips"
            :key="`${clip.nodeId}-${pixelsPerSecond}`"
            class="clip-item"
            :class="{ dragging: draggedClip?.track === 'video' && draggedClip?.index === index }"
            :style="{ width: videoClipWidths[index] }"
            draggable="true"
            @dragstart="handleDragStart('video', index, $event)"
            @dragover.prevent="handleDragOverItem('video', index)"
            @dragleave="handleDragLeaveItem"
            @drop.prevent.stop="handleDropOnItem('video', index)"
            @dragend="handleDragEnd"
          >
            <img v-if="clip.type === 'image'" :src="clip.thumbnailUrl" class="thumb" draggable="false" />
            <video v-else :src="clip.thumbnailUrl" class="thumb" autoplay loop muted playsinline preload="metadata" draggable="false"></video>

            <span class="remove-btn" @click.stop="removeVideo(index)">×</span>

            <div
              v-if="draggedOver?.track === 'video' && draggedOver?.index === index"
              class="absolute inset-0 bg-blue-500 opacity-50 border-2 border-blue-700 pointer-events-none"
              style="border-radius: 4px"
            ></div>
          </div>

          <span v-if="clips.length === 0" id="clips-placeholder" class="text-gray-500 italic">
            将 视频 / 图片 节点拖拽到此处...
          </span>
        </div>
      </div>

      <div
        id="audio-stitching-panel"
        class="bg-blue-100 p-4 rounded min-h-[40px]"
        style="border-top: 1px solid #d1d5db;"
        :class="{ 'drag-over': isDraggingOverContainer === 'audio' }"
        @dragover.prevent="handleDragOverContainer('audio')"
        @dragleave="handleDragLeaveContainer"
        @drop="handleDropContainer('audio')"
      >
        <div id="audio-clips-container">
          <div
            v-for="(clip, index) in audioClips"
            :key="clip.nodeId"
            class="audio-clip-item"
            :class="{ dragging: draggedClip?.track === 'audio' && draggedClip?.index === index }"
            :style="{ width: audioClipWidths[index] }"
            draggable="true"
            @dragstart="handleDragStart('audio', index, $event)"
            @dragover.prevent="handleDragOverItem('audio', index)"
            @dragleave="handleDragLeaveItem"
            @drop.prevent.stop="handleDropOnItem('audio', index)"
            @dragend="handleDragEnd"
          >
            <div class="audio-thumb">
              <span class="audio-clip-name">🎵 {{ clip.nodeId.substring(0, 8) }}...</span>
              <span class="audio-clip-duration">{{ clip.duration.toFixed(1) }}s</span>
            </div>

            <span class="remove-btn" @click.stop="removeAudio(index)">×</span>

            <div
              v-if="draggedOver?.track === 'audio' && draggedOver?.index === index"
              class="absolute inset-0 bg-blue-500 opacity-50 border-2 border-blue-700 pointer-events-none"
              style="border-radius: 4px"
            ></div>
          </div>

          <span v-if="audioClips.length === 0" id="audio-clips-placeholder" class="text-gray-500 italic">
            将 音频 节点拖拽到此处...
          </span>
        </div>
      </div>
      </div>

    <button
      id="stitch-button"
      class="mt-4 w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg transition-colors disabled:bg-gray-400"
      :disabled="clips.length === 0 || isStitching"
      @click="stitch"
    >
      {{ isStitching ? '正在拼接...' : '拼接视频' }}
    </button>

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
import { onMounted, watch } from 'vue'
import { useStitching } from '@/lib/useStitching.js'

const props = defineProps({
  clips:            { type: Array,  required: true },
  audioClips:       { type: Array,  required: true },
  isStitching:      { type: Boolean, default: false },
  stitchResultUrl:  { type: [String, null] }
})

const emit = defineEmits([
  'update:clips',
  'update:audioClips',
  'stitch',
  'remove-clip',
  'remove-audio-clip'
])

const {
  pixelsPerSecond,
  videoClipWidths,
  audioClipWidths,
  draggedClip,
  draggedOver,
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
  drawTimeline,      // ✅ 从 composable 拿到
} = useStitching(props, emit)

/* 关键：组件控制时间轴重绘逻辑 */

// 首次挂载时画一次
onMounted(() => {
  drawTimeline()
})

// 缩放 或 clips/audioClips 改变时重绘
watch(
  () => [pixelsPerSecond.value, props.clips, props.audioClips],
  () => {
    drawTimeline()
  },
  { deep: true }
)

/* 快捷方法 */
const removeVideo = index => emit('remove-clip', index)
const removeAudio = index => emit('remove-audio-clip', index)
const stitch = () => emit('stitch')
</script>

<style scoped>
/* (之前的样式) */
#stitching-panel.drag-over,
#audio-stitching-panel.drag-over { /* 【修改】 */
  border-style: solid;
  border-color: #3b82f6;
  background-color: #eff6ff;
}
.clip-item.dragging,
.audio-clip-item.dragging { /* 【修改】 */
  opacity: 0.3;
  transform: scale(0.95);
}

/* --- 【新增】音轨的样式 --- */
#clips-container,
#audio-clips-container {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  min-height: 40px;
  position: relative;
}
.audio-clip-item {
  position: relative;
  height: 40px;
  background-color: #dbdbdb;
  border-radius: 4px;
  margin-right: 4px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 8px;
  box-sizing: border-box;
}
.audio-thumb {
  display: flex;
  flex-direction: column;
  align-items: center;
  font-size: 10px;
  color: #b6b6b6;
  overflow: hidden;
  white-space: nowrap;
}
.audio-clip-name { font-weight: 500; }

.remove-btn {
  position: absolute;
  top: -5px;
  right: -5px;
  width: 16px;
  height: 16px;
  background-color: white;
  color: #ef4444; /* Red */
  border: 1px solid #ef4444;
  border-radius: 50%;
  font-size: 12px;
  line-height: 14px;
  text-align: center;
  cursor: pointer;
  z-index: 10;
  opacity: 0.8;
  transition: all 0.2s;
}
.remove-btn:hover {
  opacity: 1;
  transform: scale(1.1);
}
.clip-item:hover .remove-btn,
.audio-clip-item:hover .remove-btn {
  opacity: 1;
}
</style>