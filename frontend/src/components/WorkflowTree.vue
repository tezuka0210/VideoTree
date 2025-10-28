<template>
  <div id="chart-wrapper" class="bg-white rounded shadow p-3 flex-1 min-h-0" style="position: relative;">
    <svg ref="svgContainer" class="w-full h-full"></svg>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as d3 from 'd3'
// 导入我们
import type { AppNode } from '@/composables/useWorkflow'

// --- 1. Props (由 App.vue 传入) ---

const props = defineProps<{
  nodes: AppNode[];       // 所有的节点数据 (平铺数组)
  selectedIds: string[];  // 当前选中的节点ID数组
}>()

// --- 2. Emits (向 App.vue 传出) ---

const emit = defineEmits<{
  (e: 'update:selectedIds', ids: string[]): void; // 用于 v-model
  (e: 'delete-node', nodeId: string): void;
  (e: 'add-clip', node: AppNode, type: 'image' | 'video'): void;
  (e: 'open-preview', url: string, type: 'image' | 'video'): void;
}>()

// --- 3. 本地 Ref ---

// 创建一个 Vue ref 来引用 <svg> DOM 元素
const svgContainer = ref<SVGSVGElement | null>(null)

// 存储 ResizeObserver 实例，用于响应式缩放
let resizeObserver: ResizeObserver | null = null

// --- 4. 核心：D3 渲染函数 ---

/**
 * 核心渲染函数。它会清空并重绘整个 D3 树状图。
 * @param svgElement D3 绘制的目标 <svg> 元素
 * @param allNodesData 所有的节点数据 (来自 props.nodes)
 * @param selectedIds 选中的节点ID (来自 props.selectedIds)
 */
function renderTree(svgElement: SVGSVGElement, allNodesData: AppNode[], selectedIds: string[]) {
  // --- A. 数据准备 ---
  // 1. 清空之前的 SVG 内容
  const wrapper = d3.select(svgElement)
  wrapper.html('') // 清空

  if (allNodesData.length === 0) {
    // 如果没有数据，显示提示文本
    wrapper.append('text')
      .attr('x', '50%')
      .attr('y', '50%')
      .attr('text-anchor', 'middle')
      .attr('fill', '#9ca3af') // text-gray-400
      .text('暂无数据，请从右侧开始生成...')
    return
  }

  // 2. 将平铺的 allNodesData 转换为 D3 hierarchy 需要的树状结构
  const nodeMap: { [key: string]: AppNode & { children: AppNode[] } } = {}
  allNodesData.forEach(n => {
    nodeMap[n.id] = { ...n, children: [] }
  })
  // 3. 创建一个虚拟根节点，以支持多根树
  const fakeRoot: { id: string; module_id: string; children: any[] } = {
    id: '__ROOT__',
    module_id: 'ROOT',
    children: []
  }

  Object.values(nodeMap).forEach(n => {
    if (n.parent_id) {
      // 1. 先把父节点明确地取出来
      const parentNode = nodeMap[n.parent_id];
      // 2. 再次确认这个父节点真的存在
      if (parentNode) {
        parentNode.children.push(n);
      }
    } else if (!n.parent_id) {
      // 没有父ID的，都是根节点
      fakeRoot.children.push(n)
    }
  })

  // --- B. D3 布局与缩放设置 ---
  // 1. 获取 SVG 容器的尺寸
  const width = svgElement.clientWidth || 1200
  const height = svgElement.clientHeight || 600

  const svg = wrapper
    .attr('viewBox', `0 0 ${width} ${height}`)
    .attr('preserveAspectRatio', 'xMidYMid meet')

  const g = svg.append('g').attr('transform', `translate(80, ${height / 2})`) // 初始位置

  // 2. 设置缩放
  const zoom = d3.zoom<SVGSVGElement, unknown>()
    .scaleExtent([0.1, 2.5])
    .on('zoom', (event) => {
      g.attr('transform', event.transform)
    })
     // 添加一个 .filter() 来解决 Zoom 和 Click 的冲突
    .filter((event) => {
      // 1. 如果是滚轮事件 (wheel)，总是允许缩放
      if (event.type === 'wheel') {
        return true;
      }
      // 2. 检查事件的目标 (target)
      // .closest('.node-card') 会检查被点击的元素
      // 或者它的任何父元素，是否是一个 .node-card
      const target = event.target as Element;
      if (target && typeof target.closest === 'function' && target.closest('.node-card')) {
        // 如果点击发生在 .node-card 内部，
        // 阻止 d3.zoom 运行 (return false)
        return false;
      }
      // 3. 否则 (比如点击在 SVG 背景上)，允许 d3.zoom 运行
      return true;
    })
  svg.call(zoom)

  // 3. (重要) SVG 背景点击事件 -> 清空所有选择
  svg.on('click', (event) => {
    // 确保点击的是 SVG 背景，而不是子元素 (因为子元素会 stopPropagation)
    /*if (event.target === svgElement) {
      emit('update:selectedIds', [])
    }*/
    emit('update:selectedIds', [])
  })

  // 4. D3 树状图布局
  const root = d3.hierarchy(fakeRoot, d => d.children)
  const treeLayout = d3.tree<{ id: string; module_id: string; children: any[] }>()                          
                          .nodeSize([180, 220]);
  treeLayout(root)

  // --- C. 渲染 Links (连线) ---
  g.selectAll('.link')
    .data(root.links().filter(d => d.source.data.id !== '__ROOT__'))
    .enter()
    .append('path')
    .attr('class', 'link') // 使用 style.css 中的 .link 样式
    .attr('d', (d: any) => `M${d.source.y + 140},${d.source.x} C${d.source.y + 180},${d.source.x} ${d.target.y - 40},${d.target.x} ${d.target.y},${d.target.x}`)

  // --- D. 渲染 Nodes (节点) ---
  const node = g.selectAll('.node')
    .data(root.descendants().filter(d => d.data.id !== '__ROOT__'))
    .enter()
    .append('g')
    .attr('class', 'node')
    .attr('transform', (d: any) => `translate(${d.y}, ${d.x - 70})`) // 节点位置

  // 1. 使用 foreignObject 来嵌入 HTML
  node.each(function (d: any) { // (d.data 现在是 AppNode)
    const fo = d3.select(this)
      .append('foreignObject')
      .attr('width', 140)
      .attr('height', 140)
      .style('overflow', 'visible')

    const div = fo.append('xhtml:div')
      .attr('class', 'node-card group') // 使用 style.css 中的 .node-card
      .style('cursor', 'pointer')
      .style('position','relative')

    // 2. (核心) 根据 props.selectedIds 更新选中样式
    div.classed('selected', selectedIds.includes(d.data.id))

    // 3. (核心) 节点点击事件 -> 更新选中
    div.on('click', function (event) {
      event.stopPropagation() // 阻止事件冒泡到 SVG 背景
      const nodeId = d.data.id
      // (Vue 方式) 创建一个新数组来触发响应式
      const newSelectedIds = [...selectedIds]
      const index = newSelectedIds.indexOf(nodeId)
      if (index > -1) {
        newSelectedIds.splice(index, 1) // 已选中，取消
      } else {
        newSelectedIds.push(nodeId) // 未选中，添加
      }
      // (核心) emit 事件，通知 App.vue 更新 v-model
      emit('update:selectedIds', newSelectedIds)
    })

    // D3 的 .on('click', ...) 在 foreignObject 中不可靠
    // 使用原生的 addEventListener 来替代它
    // 1. 获取 div 的 DOM 节点
    /*const divNode = div.node()! as HTMLDivElement; 
    // 2. 在 DOM 节点上添加原生点击事件
    divNode.addEventListener('click', (event) => {
      event.stopPropagation(); // 阻止冒泡到 SVG 背景
      const nodeId = d.data.id;

      // (正确) 我们从 props 读取当前的 ID
      const currentSelectedIds = [...props.selectedIds];
      const index = currentSelectedIds.indexOf(nodeId);

      if (index > -1) {
        currentSelectedIds.splice(index, 1);
      } else {
        currentSelectedIds.push(nodeId);
      }
      // (正确) emit 更新
      emit('update:selectedIds', currentSelectedIds);
    });*/
    // 4. 删除按钮
    if (d.data.module_id !== 'Init' && d.data.module_id !== 'ROOT') {
      div.append('xhtml:button')
        // (Tailwind) 这是你原 CSS 中按钮的样式
        .attr('class', 'bg-red-500 text-white rounded-full w-5 h-5 text-xs leading-5 text-center font-bold opacity-0 group-hover:opacity-70 hover:opacity-100 z-10 transition-opacity duration-150')
        .style('font-size', '11px')
        .text('X')
        .on('click', (event) => {
          event.stopPropagation()
          emit('delete-node', d.data.id) // (核心) emit 删除事件
        })
    }

     // 5. 渲染媒体 (图片/视频) (1:1 恢复版)
    if (d.data.media && d.data.media.rawPath) {
      const mediaUrl = d.data.media.url
      const isVideo = d.data.media.type === 'video'
      const canAddToStitch = true; 

      if (isVideo) {
          // --- 视频的 "+" 按钮 (来自 index.html) ---
          if (canAddToStitch) {
              div.append('xhtml:button')
              .attr('class', 'bg-blue-500 text-white rounded-full w-5 h-5 text-xs leading-5 text-center font-bold opacity-0 group-hover:opacity-80 hover:opacity-100 transition-opacity duration-150')
              .text('+')
              .style('position','absolute')
              .style('bottom','4px')
              .style('right','4px')
              .on('click', (event) => {
                  event.stopPropagation();
                  emit('add-clip', d.data, 'video');
              });
          }
          // --- 视频元素 (完完全全来自 index.html) ---
          const videoEl = div.append('xhtml:video')
            .attr('class', 'thumb')
            .attr('muted', true)
            .attr('playsinline', true)
            .attr('preload', 'metadata')
            .node()! as HTMLVideoElement; 
          videoEl.autoplay = true;
          videoEl.loop = true;
          videoEl.muted = true;
          videoEl.playsInline = true;
          videoEl.src = mediaUrl;
          videoEl.addEventListener('click', (ev) => {
            ev.stopPropagation();
            emit('open-preview', mediaUrl, 'video'); 
          });

      } else {
          // --- 图片的 "+" 按钮 (来自 index.html) ---
          if (canAddToStitch) {
              div.append('xhtml:button')
              .attr('class', 'bg-blue-500 text-white rounded-full w-5 h-5 text-xs leading-5 text-center font-bold opacity-0 group-hover:opacity-80 hover:opacity-100 transition-opacity duration-150')
              .text('+')
              .style('position','absolute')
              .style('bottom','4px')
              .style('right','4px')
              .on('click', (event) => {
                  event.stopPropagation();
                  emit('add-clip', d.data, 'image');
              });
          }
          // --- 图片元素 (完完全全来自 index.html) ---
          const imgEl = div.append('xhtml:img')
            .attr('class', 'thumb')
            .attr('src', mediaUrl)
            .attr('alt', d.data.module_id || 'thumb')
            .node()! as HTMLImageElement;
          imgEl.addEventListener('click', (ev) => {
            ev.stopPropagation();
            emit('open-preview', mediaUrl, 'image'); 
          });
      }
    } else {
        // (无缩略图的占位符，保持不变)
        div.append('xhtml:div')
            .attr('class', 'thumb')
            .style('display', 'flex')
            .style('align-items', 'center')
            .style('justify-content', 'center')
            .style('font-size', '12px')
            .style('color', '#6b7280')
            .text('无缩略图')
    }

    // 10. 节点标签
    div.append('xhtml:div')
      .attr('class', 'node-label') // 使用 style.css 中的 .node-label
      .text(d.data.module_id || '(节点)')
    // 11. Tooltip (鼠标悬停提示)
    const titleText = (d.data.module_id || '') + (d.data.created_at ? ' · ' + d.data.created_at : '') + (d.data.status ? ' · ' + d.data.status : '')
    d3.select(this).attr('title', titleText)
  })
}


// --- 5. Vue 生命周期钩子 ---

// (核心) 监听 props 的变化，并在变化时重绘 D3
watch(
  [() => props.nodes, () => props.selectedIds],
  ([newNodes, newSelectedIds]) => {
    if (svgContainer.value) {
      // 当 allNodes 或 selectedParentIds 变化时，
      // 使用新数据重新调用 D3 渲染函数
      renderTree(svgContainer.value, newNodes, newSelectedIds)
    }
  },
  { deep: true } // 深度监听 nodes 数组内部的变化
)

onMounted(() => {
  const container = svgContainer.value
  if (!container) return

  // 1. 初始渲染
  renderTree(container, props.nodes, props.selectedIds)
  // 2. (重要) 设置 ResizeObserver 来实现响应式
  // 我们观察 SVG 的父元素 (#chart-wrapper)
  /*const wrapperEl = container.parentElement
  if (wrapperEl) {
    resizeObserver = new ResizeObserver(() => {
      // 当父元素尺寸变化时，重新渲染
      renderTree(container, props.nodes, props.selectedIds)
    })
    resizeObserver.observe(wrapperEl)
  }*/
})

onUnmounted(() => {
  // 3. (重要) 组件卸载时，停止观察，防止内存泄漏
  /*if (resizeObserver) {
    resizeObserver.disconnect()
  }*/
})
</script>