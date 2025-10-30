<template>
  <div id="chart-wrapper" class="bg-white rounded shadow p-3 flex-1 min-h-0" style="position: relative;">
    <svg ref="svgContainer" class="w-full h-full"></svg>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as d3 from 'd3'
import * as dagre from 'dagre'
// 导入我们
import type { AppNode } from '@/composables/useWorkflow'
import { workflowTypes } from '@/composables/useWorkflow'

// --- 1. Props (由 App.vue 传入) ---
const defaultLinkColor = '#9ca3af';

interface DagrePoints {
  x: number;
  y: number;
}

const lineGenerator = d3.line<DagrePoints>()
  .x(d => d.x)
  .y(d => d.y)
  .curve(d3.curveBasis); // <-- (关键) d3.curveBasis 提供了平滑的 B-spline 曲线

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
  (e: 'open-generation', node: AppNode): void; 
  (e: 'open-generation', node: AppNode, defaultModuleId: string, workflowType:'preprocess' | 'image' | 'video'): void;
  (e: 'toggle-collapse', nodeId: string): void; 
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

/*function updateSelectionStyles(svgElement: SVGSVGElement, selectedIds: string[]) {
  // 1. (安全检查) 确保 D3 节点存在
  const nodes = d3.select(svgElement).selectAll<SVGGElement, d3.HierarchyNode<any>>('.node');
  nodes.each(function(d) {
    // 确保 d 和 d.data 存在
    if (d && d.data) {
      const nodeId = d.data.id;
      // 2. 找到这个节点对应的卡片
      const card = d3.select(this).select<HTMLDivElement>('.node-card');
      if (selectedIds.includes(nodeId)) {
        // 3. 如果 ID 在列表中，添加 'selected'
        card.classed('selected', true);
      } else {
        // 4. 否则，移除 'selected'
        card.classed('selected', false);
      }
    }
  });
}*/

/** (v60) 递归查找所有子孙节点 ID (用于收缩) */
function findDescendants(
  nodeId: string,
  hierarchy: Map<string, AppNode & { children: AppNode[] }>
): string[] {
  const node = hierarchy.get(nodeId);
  if (!node || !node.children || node.children.length === 0) {
    return [];
  }
  let descendants: string[] = [];
  node.children.forEach(child => {
    descendants.push(child.id);
    descendants = descendants.concat(findDescendants(child.id, hierarchy)); // 递归
  });
  return descendants;
}

/** (v60) 计算可见节点和连线 (用于收缩) */
function getVisibleNodesAndLinks(allNodes: AppNode[]): {
  visibleNodes: AppNode[],
  visibleLinks: { source: string, target: string }[] 
} {
  if (!allNodes || allNodes.length === 0) {
    return { visibleNodes: [], visibleLinks: [] };
  }
  // 1. 构建临时的父子层级关系
  const nodeMap = new Map(allNodes.map(n => [n.id, { ...n, children: [] as AppNode[] }]));
  allNodes.forEach(n => {
    if (n.originalParents) { // (v66) 使用 originalParents
      n.originalParents.forEach(parentId => {
        const parent = nodeMap.get(parentId);
        if (parent) {
          parent.children.push(n);
        }
      });
    }
  });

  // 2. 找出所有需要隐藏的节点 ID
  const hiddenNodeIds = new Set<string>();
  allNodes.forEach(node => {
    if (node._collapsed) {
      const descendants = findDescendants(node.id, nodeMap);
      descendants.forEach(id => hiddenNodeIds.add(id));
    }
  });

  // 3. 过滤出可见节点
  const visibleNodes = allNodes.filter(node => !hiddenNodeIds.has(node.id));
  const visibleNodeIds = new Set(visibleNodes.map(n => n.id));

  // 4. 构建可见连线
  const visibleLinks: { source: string, target: string }[] = [];
  visibleNodes.forEach(node => { // (v71 修复) 只遍历可见节点
    if (node.originalParents) { // (v66)
      node.originalParents.forEach(parentId => {
        // 源节点也必须可见
        if (visibleNodeIds.has(parentId)) {
          visibleLinks.push({ source: parentId, target: node.id });
        }
      });
    }
  });

  return { visibleNodes, visibleLinks };
}

// (v33) 快速样式更新函数
function updateSelectionStyles(svgElement: SVGSVGElement, selectedIds: string[]) {
  // ... (v33 的代码保持不变) ...
  d3.select(svgElement).selectAll<SVGGElement, d3.HierarchyNode<any>>('.node')
    .each(function(d) {
      if (d && d.id) { // (v71 修复) d3.forceSimulation 是 d, d3.tree 是 d.data.id
        const nodeId = d.id;
        const card = d3.select(this).select<HTMLDivElement>('.node-card');
        card.classed('selected', selectedIds.includes(nodeId));
      }
    });
}




function renderTree(svgElement: SVGSVGElement, allNodesData: AppNode[], selectedIds: string[]) {
  // --- A. 数据准备 ---
  const wrapper = d3.select(svgElement);
  wrapper.html('');

  console.log(
    `%c[Debug 1] 传入 renderTree 的原始数据 (allNodesData):`,
    "color: #FFA500; font-weight: bold;",
    allNodesData // (请展开这个数组)
  );

  // (v60) 1. 过滤出可见节点和连线
  const { visibleNodes, visibleLinks } = getVisibleNodesAndLinks(allNodesData);

  // VVVV 添加这个日志 VVVV
  console.log(
    `%c[Debug 2] 过滤后的可见连线 (visibleLinks):`,
    "color: #FF69B4; font-weight: bold;",
    visibleLinks // (请展开这个数组)
  );
  // ^^^^ 添加这个日志 ^^^^

  if (visibleNodes.length === 0) {
    wrapper.append('text')
      .attr('x', '50%')
      .attr('y', '50%')
      .attr('text-anchor', 'middle')
      .attr('fill', '#9ca3af')
      .text('暂无数据，请从右侧开始生成...')
    return;
  }

  // --- B. (核心 v71) Dagre 布局计算 ---

  // 1. 创建 Dagre 图
  const g = new dagre.graphlib.Graph();
  // 2. 设置布局为 "LR" (Left-to-Right)
  g.setGraph({ rankdir: 'LR', nodesep: 100, ranksep: 120 }); // nodesep: 节点Y间距, ranksep: 层X间距
  // 3. 设置默认边样式
  g.setDefaultEdgeLabel(() => ({}));

  // 4. (关键) 告诉 Dagre *所有*可见节点的尺寸
  visibleNodes.forEach(node => {
    // (v71) 我们使用固定的 140x140 尺寸
    g.setNode(node.id, { label: node.module_id, width: 140, height: 140 });
  });

  // 5. (关键) 告诉 Dagre 所有的连线
  visibleLinks.forEach(link => {
    g.setEdge(link.source, link.target);
  });

  // 6. (关键) 运行布局！
  dagre.layout(g);

  console.log(
    `%c[Debug 3] Dagre 实际处理的连线 (g.edges()):`,
    "color: #00BFFF; font-weight: bold;",
    g.edges() // (请展开这个数组)
  );


  // 7. (关键) 从 Dagre 获取 计算好 的节点，并存入 Map 方便查找
  const dagreNodes = new Map(g.nodes().map(nodeId => [nodeId, g.node(nodeId)]));

  const dagreEdges = g.edges().map(edgeObj => {
      const edgeData = g.edge(edgeObj); // { points: [ {x,y}, {x,y}, ... ] }
      return { v: edgeObj.v, w: edgeObj.w, points: edgeData.points };
  });
  // --- C. D3 渲染 (现在只负责“画”) ---
  const width = svgElement.clientWidth || 1200;
  const height = svgElement.clientHeight || 600;
  const svg = wrapper
    .attr('viewBox', `0 0 ${width} ${height}`)
    .attr('preserveAspectRatio', 'xMidYMid meet');
  // (v45) 箭头定义
   const defs = svg.append('defs');
  // 1. 定义我们所有的颜色
  const colorsToDefine = [
    { id: 'red', color: workflowTypes.red.color },
    { id: 'yellow', color: workflowTypes.yellow.color },
    { id: 'green', color: workflowTypes.green.color },
    { id: 'default', color: defaultLinkColor } // (v65) 灰色
  ];

  // 2. 循环并为每种颜色创建一个 marker
  colorsToDefine.forEach(c => {
    defs.append('marker')
      .attr('id', `arrowhead-${c.id}`) // <-- 唯一 ID (例如 "arrowhead-red")
      .attr('viewBox', '-0 -5 10 10')
      .attr('refX', 10) // (v77 修复)
      .attr('refY', 0)
      .attr('orient', 'auto')
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('xoverflow', 'visible')
    .append('svg:path')
      .attr('d', 'M 0,-5 L 10 ,0 L 0,5')
      .style('fill', c.color) // <-- (核心 v78) 使用对应的颜色
      .style('stroke', 'none');
  });

  // (v71) 我们需要一个 <g> 来容纳 Dagre 的布局
  const layoutGroup = svg.append('g');

  // (v45) 创建 links 和 nodes 的容器 <g>
  const linkGroup = layoutGroup.append('g').attr('class', 'links');
  const nodeGroup = layoutGroup.append('g').attr('class', 'nodes');

  // (v45/v71) Zoom 逻辑
  const zoom = d3.zoom<SVGSVGElement, unknown>()
    .scaleExtent([0.1, 2.5])
    .on('zoom', (event) => {
      layoutGroup.attr('transform', event.transform); // (v71) 缩放 layoutGroup
    });
  svg.call(zoom);
  // (v71) 尝试计算初始缩放和平移以使图居中
  const graphWidth = g.graph().width || width;
  const graphHeight = g.graph().height || height;
  const initialScale = Math.min(1, Math.min(width / graphWidth, height / graphHeight) * 0.9);
  const initialTranslateX = (width - (graphWidth * initialScale)) / 2;
  const initialTranslateY = (height - (graphHeight * initialScale)) / 2;
  svg.call(zoom.transform as any, d3.zoomIdentity.translate(initialTranslateX, initialTranslateY).scale(initialScale));

  // (v31/v71) 背景点击 (原生)
  const svgDomElement = svg.node()!;
  svgDomElement.addEventListener('click', (event) => {
    if (event.target === svgDomElement) {
        console.log("--- 1. 背景被点击 --- (立即取消全选)");
        svgElement.querySelectorAll('.node-card').forEach(card => {
          card.classList.remove('selected');
        });
        emit('update:selectedIds', [])
    }
  });

  // 1. 渲染 Links (不再用物理模拟)
  function getLinkStyle(d: any) {
    // (d.w 是 dagre 边的目标 ID)
    const targetNode = allNodesData.find(n => n.id === d.w);
    const linkColor = targetNode?.linkColor; // (v60)

    if (linkColor === workflowTypes.red.color) {
      return { color: workflowTypes.red.color, id: 'url(#arrowhead-red)' };
    }
    if (linkColor === workflowTypes.yellow.color) {
      return { color: workflowTypes.yellow.color, id: 'url(#arrowhead-yellow)' };
    }
    if (linkColor === workflowTypes.green.color) {
      return { color: workflowTypes.green.color, id: 'url(#arrowhead-green)' };
    }
    // 默认情况
    return { color: defaultLinkColor, id: 'url(#arrowhead-default)' };
  }

  // 2. 渲染 Links (v78 动态版)
  const linkElements = linkGroup.selectAll('path.link')
    .data(dagreEdges)
    .enter().append('path')
      .attr('class', 'link') // (确保 style.css 有 fill: none)
      // (核心 v78)
      // 使用 .each() 来同时设置 stroke 和 marker-end
      .each(function(d) {
        const style = getLinkStyle(d);
        d3.select(this)
          .style('stroke', style.color)
          .attr('marker-end', style.id);
      })
      .attr('d', (d: any) => lineGenerator(d.points));

  // 2. 渲染 Nodes (不再用物理模拟)
  const nodeElements = nodeGroup.selectAll('.node')
    .data(visibleNodes, (d: any) => d.id)
    .enter().append('g')
      .attr('class', 'node')
      // (核心 v71) 从 Dagre 读取坐标
      .attr('transform', (d: any) => {
        const node = dagreNodes.get(d.id)!;
        return `translate(${node.x},${node.y})`;
      });

  // (v68 修复) node.each(...) 循环
  // 包含 fo, div, divNode, 选中逻辑(v39), 删除(×), 三色圆点(v52), 收缩(+/-)(v60)
  // 媒体(+), 标签, Tooltip
  nodeElements.each(function (d: any) {
    const gElement = d3.select(this);
    const fo = gElement.append('foreignObject')
      .attr('width', 140)
      .attr('height', 140)
      .attr('x', -70) // (v71) 中心定位
      .attr('y', -70) // (v71) 中心定位
      .style('overflow', 'visible');

    // (v23) 拦截 mousedown，阻止 zoom
    fo.on('mousedown', (event) => {
      event.stopPropagation();
    });

    const div = fo.append('xhtml:div')
      .attr('class', 'node-card group')
      .style('cursor', 'pointer')
      .style('position','relative'); // (v50 修复)
    const divNode = div.node()! as HTMLDivElement;
    // (v39/v68) 卡片白边 mousedown 和 click 监听器
    divNode.addEventListener('mousedown', (event) => {
      event.stopPropagation();
    });
    divNode.addEventListener('click', (event) => {
      console.log("--- 2. 节点卡片被点击 --- (v39 多选)");
      event.stopPropagation();
      const nodeId = d.id; // (v67 修复)
      const currentSelectedIds = [...props.selectedIds];
      const index = currentSelectedIds.indexOf(nodeId);
      if (index > -1) {
        currentSelectedIds.splice(index, 1);
        divNode.classList.remove('selected');
      } else {
        if (currentSelectedIds.length < 2) { // (v39 限制)
            currentSelectedIds.push(nodeId);
            divNode.classList.add('selected');
        } else {
            console.warn("最多只能选择 2 个父节点。");
        }
      }
      emit('update:selectedIds', currentSelectedIds);
    });

    // (v33) 更新选中样式
    div.classed('selected', selectedIds.includes(d.id));

    // (v52/v68) 删除按钮 "×"
    if (d.module_id !== 'Init' && d.module_id !== 'ROOT') {
      const deleteBtn = div.append('xhtml:button')
        .attr('class', 'bg-red-500 text-white ...') // (v52 样式)
        .style('font-size', '11px')
        .style('position', 'absolute')
        .style('top', '4px')
        .style('left', '4px')
        .text('X')
        .node()! as HTMLButtonElement;
      deleteBtn.addEventListener('click', (event) => {
        event.stopPropagation();
        emit('delete-node', d.id);
      });
    }

    // (v52/v68) 三色圆点
    const dotsContainer = div.append('xhtml:div')
      .attr('class', `
        absolute top-0 right-1 h-full        flex flex-col items-center justify-center space-y-1
        opacity-0 group-hover:opacity-100 transition-opacity duration-150 z-10
      `); // (v51 样式)
    (['red', 'yellow', 'green'] as const).forEach((colorKey, index) => {
      const workflowInfo = workflowTypes[colorKey];
      const dotBtn = dotsContainer.append('xhtml:button')
        .attr('class', `hover:scale-125 transition-transform`) // (v52 样式)
        .style('background-color', workflowInfo.color)
        .style('width', '16px')      // (v52 样式)
        .style('height', '16px')     // (v52 样式)
        .style('border-radius', '50%') // (v52 样式)
        .style('border', 'none')       // (v52 样式)
        .style('padding', '0')         // (v52 样式)
        .style('cursor', 'pointer')    // (v52 样式)
        .attr('title', `Start ${workflowInfo.type} workflow`)
        .node()! as HTMLButtonElement;
      dotBtn.addEventListener('mousedown', (event) => {
        event.stopPropagation();
      });
      dotBtn.addEventListener('click', (event) => {
        event.stopPropagation();
        emit('open-generation', d, workflowInfo.defaultModuleId, workflowInfo.type as 'preprocess' | 'image' | 'video');
      });
    });

    // (新 v60) 添加 "+/-" 收缩/展开按钮
    const tempNodeMap = new Map(allNodesData.map(n => [n.id, { ...n, children: [] as AppNode[] }]));
    allNodesData.forEach(n => {
      if (n.originalParents) {
        n.originalParents.forEach((pId: string) => {
          const parent = tempNodeMap.get(pId);
          if (parent) {
            parent.children.push(n);
          }
        });
      }
    });
    const nodeInMap = tempNodeMap.get(d.id); // (v66 修复)
    const hasChildren = nodeInMap ? nodeInMap.children.length > 0 : false; // (v66 修复)

    if (hasChildren) {
      const collapseBtn = div.append('xhtml:button')
        .attr('class', 'absolute bottom-0 left-0 bg-gray-400 text-white rounded-full w-4 h-4 text-xs leading-4 text-center font-bold z-10 hover:bg-gray-600')
        .style('transform', 'translate(-25%, 25%)')
        .text(d._collapsed ? '+' : '-') // 根据状态显示 +/-
        .node()! as HTMLButtonElement;
      collapseBtn.addEventListener('mousedown', (event) => {
        event.stopPropagation(); // 阻止 zoom
      });
      collapseBtn.addEventListener('click', (event) => {
        event.stopPropagation(); // 阻止选中
        emit('toggle-collapse', d.id); // 触发收缩/展开
      });
    }

    // (v68 修复) 渲染媒体和 "+" 添加按钮
    if (d.media && d.media.rawPath) {
      const mediaUrl = d.media.url;
      const isVideo = d.media.type === 'video';
      const canAddToStitch = true; 

      if (isVideo) {
          // --- 视频的 "+" 按钮 ---
          if (canAddToStitch) {
              const addVideoBtn = div.append('xhtml:button')
                .attr('class', 'bg-blue-500 text-white ...') // (v50 样式)
                .text('+')
                .style('position','absolute')
                .style('bottom','4px')
                .style('right','4px')
                .node()! as HTMLButtonElement;
              addVideoBtn.addEventListener('click', (event) => {
                  event.stopPropagation();
                  emit('add-clip', d, 'video'); // (v67 修复)
              });
          }
          // --- 视频元素 ---
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
          videoEl.addEventListener('mousedown', (ev) => { ev.stopPropagation(); }); // (v24)
          videoEl.addEventListener('click', (ev) => {
            ev.stopPropagation();
            emit('open-preview', mediaUrl, d.media.type); // (v67 修复)
          });

      } else {
          // --- 图片的 "+" 按钮 ---
          if (canAddToStitch) {
              const addImageBtn = div.append('xhtml:button')
                .attr('class', 'bg-blue-500 text-white ...') // (v50 样式)
                .text('+')
                .style('position','absolute')
                .style('bottom','4px')
                .style('right','4px')
                .node()! as HTMLButtonElement;
              addImageBtn.addEventListener('click', (event) => {
                  event.stopPropagation();
                  emit('add-clip', d, 'image'); // (v67 修复)
              });
          }
          // --- 图片元素 ---
          const imgEl = div.append('xhtml:img')
            .attr('class', 'thumb')
            .attr('src', mediaUrl)
            .attr('alt', d.module_id || 'thumb') // (v67 修复)
            .node()! as HTMLImageElement;
          imgEl.addEventListener('mousedown', (ev) => { ev.stopPropagation(); }); // (v24)
          imgEl.addEventListener('click', (ev) => {
            ev.stopPropagation();
            emit('open-preview', mediaUrl, d.media.type); // (v67 修复)
          });
      }
    } else {
        // (无缩略图的占位符)
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
      .attr('class', 'node-label')
      .text(d.module_id || '(节点)'); // (v67 修复)
    // 11. Tooltip
    // (v67 修复)
    const titleText = (d.module_id || '') + (d.created_at ? ' · ' + d.created_at : '') + (d.status ? ' · ' + d.status : '');
    d3.select(this).attr('title', titleText);
  });
}


// --- 5. Vue 生命周期钩子 ---

// (核心) 监听 props 的变化，并在变化时重绘 D3
watch(
  () => props.nodes, // <-- 只监听 nodes
  (newNodes) => {
    console.log("%c[Tree] WATCH (Nodes) -> 重绘整棵树", "color: red; font-weight: bold;");
    if (svgContainer.value) {
      renderTree(svgContainer.value, newNodes, props.selectedIds)
    }
  },
  { deep: true } 
);

// (核心修复 v33)
// 监听器 2: (快)  <-- 你很可能缺少这个！
// 只在 选中ID(selectedIds) 变化时，才调用*快速*的样式更新函数
watch(
  () => props.selectedIds, // <-- 只监听 selectedIds
  (newSelectedIds) => {
    // VVVV 这是你想要的日志 VVVV
    console.log(
      `%c[Tree]2. WATCH (selectedIds) -> 正在更新样式`,
      "color: #209CEE; font-weight: bold;",
      newSelectedIds // 打印出它收到的新数组
    );
    // ^^^^ 这是你想要的日志 ^^^^
    if (svgContainer.value) {
      updateSelectionStyles(svgContainer.value, newSelectedIds);
    }
  },
  { deep: true }
);

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