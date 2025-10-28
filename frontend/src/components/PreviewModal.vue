<template>
  <div
    class="overlay fixed inset-0 flex items-center justify-center bg-black/60 z-50"
    @click.self="handleClose"
  >
    <div class="modal bg-white rounded-lg max-w-[90%] max-h-[90%] p-3 shadow-xl overflow-auto">
      <div class="text-right mb-2">
        <button
          @click="handleClose"
          class="px-3 py-1 bg-gray-200 hover:bg-gray-300 rounded-md text-sm font-medium transition-colors"
        >
          关闭
        </button>
      </div>
      <img
        v-if="props.type === 'image'"
        :src="props.url"
        alt="preview"
        class="block max-w-full max-h-[80vh] mx-auto"
      />
      <video
        v-else
        :src="props.url"
        controls
        autoplay
        loop
        class="block max-w-full max-h-[80vh] mx-auto"
      >
        你的浏览器不支持播放此视频。
      </video>

    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'

// (1) 定义组件接收的 props
// App.vue 将通过 :url="..." 和 :type="..." 把数据传进来
const props = defineProps<{
  url: string;
  type: 'image' | 'video';
}>()

// (2) 定义组件可以触发的事件
// 当用户点击关闭时，它会触发 'close' 事件，App.vue 会监听到
const emit = defineEmits<{
  (e: 'close'): void;
}>()

// (3) 定义一个函数，用于触发 'close' 事件
function handleClose() {
  emit('close')
}

// (4) 实现了原版 JS 中的 "Escape" 键关闭功能
function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    handleClose()
  }
}

// (5) 在组件挂载时，添加键盘事件监听
onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

// (6) 在组件卸载时，移除监听，防止内存泄漏
onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>