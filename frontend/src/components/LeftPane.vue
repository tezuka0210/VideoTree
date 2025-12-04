<template>
  <div class="flex flex-col h-full min-h-0 space-y-3 p-2 box-border">
    <!-- 上半：会话区域，占据可用高度 -->
    <div class="flex-1 min-h-0">
      <LeftSessionsPane class="h-full" />
    </div>

    <!-- 下半：全局参数，固定高度，大概 200~260px -->
    <div class="h-64 min-h-[400px]">
      <LeftGlobalSettingsPane class="h-full" />
    </div>
  </div>
</template>

<script setup lang="ts">
import LeftSessionsPane from './LeftSessionsPane.vue'
import LeftGlobalSettingsPane from './LeftGlobalSettingsPane.vue'
</script>
