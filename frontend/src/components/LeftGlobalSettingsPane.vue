<template>
  <section class="w-full h-full bg-white rounded-lg shadow-inner flex flex-col">
    <header class="px-2.5 py-2 border-b border-gray-100">
      <h2 class="text-xs font-semibold text-gray-700 tracking-wide">Global Model Settings</h2>
    </header>

    <div class="flex-1 min-h-0 overflow-auto px-2.5 py-2 space-y-3 text-xs">
      <!-- 模型选择 -->
      <div class="space-y-1">
        <label class="block text-[11px] text-gray-500">Model</label>
        <select
          class="w-full border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:ring focus:ring-indigo-100"
        >
          <option>video-llm-1</option>
          <option>image-llm-1</option>
          <option>custom</option>
        </select>
      </div>

      <!-- 温度 -->
      <div class="space-y-1">
        <label class="block text-[11px] text-gray-500">Temperature</label>
        <input
          type="number"
          min="0"
          max="1"
          step="0.1"
          class="w-full border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:ring focus:ring-indigo-100"
          placeholder="0.7"
        />
      </div>

      <!-- 全局 system prompt -->
      <div class="space-y-1">
        <label class="block text-[11px] text-gray-500">System Prompt</label>
        <textarea
          rows="3"
          class="w-full border border-gray-200 rounded px-2 py-1 text-xs resize-none focus:outline-none focus:ring focus:ring-indigo-100"
          placeholder="You are a video workflow copilot..."
        ></textarea>
      </div>

      <!-- 按钮 -->
      <div class="pt-1 flex justify-end">
        <button
          type="button"
          class="px-3 py-1 rounded bg-indigo-500 text-white text-xs hover:bg-indigo-600"
        >
          Apply Settings
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
// 同样，将来可以接 props / emits，把这些设置同步给 App / useWorkflow
</script>
