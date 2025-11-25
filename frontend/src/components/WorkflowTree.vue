<template>
  <div id="chart-wrapper" class="bg-white rounded shadow p-3 flex-1 min-h-0" style="position: relative;">
    <svg ref="svgContainer" class="w-full h-full"></svg>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { workflowTypes } from '@/composables/useWorkflow'

// 从 JS 版工具库导入
import {
  renderTree,
  updateVisibility,
  updateSelectionStyles
} from '@/lib/workflowGraph.js'

// ========== Props ==========
const props = defineProps({
  nodes: { type: Array, default: () => [] },
  selectedIds: { type: Array, default: () => [] }
})

// ========== Emits ==========
const emit = defineEmits([
  'update:selectedIds',
  'delete-node',
  'add-clip',
  'open-preview',
  'open-generation',
  'create-card',
  'toggle-collapse',
  'rename-node',
  'update-node-parameters',
  'refresh-node'
])

// 传给 lib 的 emit 适配器
const graphEmit = (event, ...args) => {
  emit(event, ...args)
}

// ========== Refs ==========
const svgContainer = ref(null)

// ========== 生命周期 ==========
onMounted(() => {
  if (!svgContainer.value) return
  renderTree(
    svgContainer.value,
    props.nodes,
    props.selectedIds,
    graphEmit,
    workflowTypes
  )
})

// ========== Watchers ==========

// 监听节点变化：结构变化 -> 重绘；仅状态变化 -> 只更新可见性
watch(
  () => props.nodes,
  (newNodes, oldNodes) => {
    console.log('完整 oldNodes:', oldNodes.map(n => ({id: n.id, module_id: n.module_id})));
    console.log('完整 newNodes:', newNodes.map(n => ({id: n.id, module_id: n.module_id})));
    if (!svgContainer.value) return

    // 在 WorkflowTree.vue 的 watch(props.nodes) 中
    let structureChanged = false;
    // 1. 先判断节点数量是否变化
    if (!oldNodes || newNodes.length !== oldNodes.length) {
      structureChanged = true;
    } else {
      // 2. 判断节点ID集合是否变化
      const newIds = new Set(newNodes.map(n => n.id));
      for (const n of oldNodes) {
        if (!newIds.has(n.id)) {
          structureChanged = true;
          break;
        }
      }
      
      // 3. 新增：判断任意节点的 module_id 是否变化（关键）
      if (!structureChanged) {
        for (let i = 0; i < newNodes.length; i++) {
          const newNode = newNodes[i];
          const oldNode = oldNodes.find(n => n.id === newNode.id); // 按ID匹配旧节点
          console.log(`old module_id:${oldNode.module_id}       new module_id:${newNode.module_id}`)
          if (oldNode && newNode.module_id !== oldNode.module_id) {
            structureChanged = true;
            break;
          }
        }
      }
    }

    if (structureChanged) {
      console.log('[WorkflowTree] 节点结构变化，调用 renderTree');
      renderTree(
        svgContainer.value,
        newNodes,
        props.selectedIds,
        graphEmit,
        workflowTypes
      );
    } else {
      console.log('[WorkflowTree] 节点状态变化，调用 updateVisibility');
      updateVisibility(svgContainer.value, newNodes);
    }
  },
  { deep: true }
)

// 监听选中变化：只更新选中样式
watch(
  () => props.selectedIds,
  (ids) => {
    console.log('[WorkflowTree] props.selectedIds 变化', ids);
    if (svgContainer.value) updateSelectionStyles(svgContainer.value, ids)
  },
  { deep: true }
)
</script>
