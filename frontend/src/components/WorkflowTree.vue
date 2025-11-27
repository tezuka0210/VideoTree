<template>
  <div id="chart-wrapper" class="bg-white rounded shadow p-3 flex-1 min-h-0" style="position: relative;">
    <svg ref="svgContainer" class="w-full h-full"></svg>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { workflowTypes } from '@/composables/useWorkflow'

import * as d3 from 'd3'

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
  'refresh-node',
  'upload-media',
  'update-node-media-from-parent'
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

// 移除类型注解
function isAssetsEqual(newAssets, oldAssets) {
  if (!newAssets && !oldAssets) return true;
  if (!newAssets || !oldAssets) return false;

  const inputEqual = isMediaGroupEqual(newAssets.input, oldAssets.input);
  const outputEqual = isMediaGroupEqual(newAssets.output, oldAssets.output);

  return inputEqual && outputEqual;
}

function isMediaGroupEqual(newGroup, oldGroup) {
  if (!newGroup && !oldGroup) return true;
  if (!newGroup || !oldGroup) return false;

  const imagesEqual = arraysEqual(newGroup.images || [], oldGroup.images || []);
  const videosEqual = arraysEqual(newGroup.videos || [], oldGroup.videos || []);
  const audioEqual = arraysEqual(newGroup.audio || [], oldGroup.audio || []);

  return imagesEqual && videosEqual && audioEqual;
}

function arraysEqual(a, b) {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (a[i] !== b[i]) return false;
  }
  return true;
}

watch(
  () => props.nodes,
  (newNodes, oldNodes) => {
    console.log('完整 oldNodes:', oldNodes?.map(n => ({id: n.id, module_id: n.module_id})) || []);
    console.log('完整 newNodes:', newNodes.map(n => ({id: n.id, module_id: n.module_id})));
    if (!svgContainer.value) return;

    let structureChanged = false;

    // 1. 先判断节点数量是否变化（数量变了肯定是结构变化）
    if (!oldNodes || newNodes.length !== oldNodes.length) {
      structureChanged = true;
    } else {
      // 优化：构建 oldNodes 的 ID 映射表（O(n) 预处理，后续查询 O(1)）
      const oldNodeMap = new Map(oldNodes.map(n => [n.id, n]));
      
      // 2. 检查是否有节点新增/删除（ID 不存在于旧节点中）
      for (const newNode of newNodes) {
        if (!oldNodeMap.has(newNode.id)) {
          structureChanged = true;
          break;
        }
      }

      // 3. 检查节点属性变化（module_id、assets 等关键字段）
      if (!structureChanged) {
        for (const newNode of newNodes) {
          const oldNode = oldNodeMap.get(newNode.id);
          if (!oldNode) {
            structureChanged = true;
            break; // 理论上不会进入这里，因为前面已经检查过 ID 存在
          }

          // 3.1 模块变化（属于结构变化）
          if (newNode.module_id !== oldNode.module_id) {
            structureChanged = true;
            break;
          }

          // 3.2 Assets 变化（属于结构变化，用更精确的比较）
          if (!isAssetsEqual(newNode.assets, oldNode.assets)) {
            structureChanged = true;
            break;
          }

          // 3.3 其他可能的结构变化字段（比如 parent_ids 变化，根据你的需求添加）
          // if (JSON.stringify(newNode.parent_ids) !== JSON.stringify(oldNode.parent_ids)) {
          //   structureChanged = true;
          //   break;
          // }
        }
      }
    }


    if (structureChanged) {
      console.log('[WorkflowTree] 节点结构变化，调用 renderTree');
      let currentViewState = null;
      if (svgContainer.value) {
        const svg = d3.select(svgContainer.value);
        // 选择 zoom-container 并检查是否存在
        const zoomContainer = svg.select('.zoom-container');
        if (!zoomContainer.empty()) { // 关键：检查元素是否存在
          const transform = zoomContainer.attr('transform');
          if (transform) {
            const scaleMatch = transform.match(/scale\(([^)]+)\)/);
            const translateMatch = transform.match(/translate\(([^,]+),([^)]+)\)/);
            if (scaleMatch && translateMatch) {
              currentViewState = {
                k: parseFloat(scaleMatch[1]),
                x: parseFloat(translateMatch[1]),
                y: parseFloat(translateMatch[2])
              };
            }
          }
        }
      }
      renderTree(
        svgContainer.value,
        newNodes,
        props.selectedIds,
        graphEmit,
        workflowTypes,
        currentViewState
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
