<template>
  <section class="w-full h-full bg-white rounded-lg shadow-inner flex flex-col">
    <header class="px-2.5 py-2 border-b border-gray-100 flex items-center justify-between">
      <h2 class="text-xs font-semibold text-gray-700 tracking-wide">LLM Sessions</h2>
      <button
        type="button"
        class="text-[11px] px-2 py-0.5 rounded-full bg-gray-100 hover:bg-gray-200 text-gray-700"
      >
        + New
      </button>
    </header>

    <!-- 会话列表：内部滚动 -->
    <div class="flex-1 min-h-0 overflow-auto px-2.5 py-2 space-y-1.5 text-xs">
      <!-- 占位示例，将来改成 v-for -->
      <div class="px-2 py-1.5 rounded-md bg-gray-50 cursor-pointer hover:bg-gray-100">
        Default Session
      </div>
      <div class="px-2 py-1.5 rounded-md bg-gray-50 cursor-pointer hover:bg-gray-100">
        Storyboard Ideas
      </div>
      <div class="px-2 py-1.5 rounded-md bg-gray-50 cursor-pointer hover:bg-gray-100">
        Style Exploration
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
// 将来可以加 props / emits，接到真实数据和事件
</script>
