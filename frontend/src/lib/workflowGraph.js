// src/lib/workflowGraph.js
import * as d3 from 'd3'
import * as dagre from 'dagre'


const defaultLinkColor = '#9ca3af'

const lineGenerator = d3.line()
  .x(d => d.x)
  .y(d => d.y)
  .curve(d3.curveBasis)

/** 递归查找子孙（用于收缩控制） */
function findDescendants(nodeId, hierarchy) {
  const node = hierarchy.get(nodeId)
  if (!node || !node.children || node.children.length === 0) return []
  let descendants = []
  node.children.forEach(child => {
    descendants.push(child.id)
    descendants = descendants.concat(findDescendants(child.id, hierarchy))
  })
  return descendants
}

/** 基于 _collapsed 计算可见节点与连线 */
export function getVisibleNodesAndLinks(allNodes) {
  if (!allNodes || allNodes.length === 0) {
    return { visibleNodes: [], visibleLinks: [] }
  }

  const nodeMap = new Map(allNodes.map(n => [n.id, { ...n, children: [] }]))
  allNodes.forEach(n => {
    if (n.originalParents) {
      n.originalParents.forEach(parentId => {
        const p = nodeMap.get(parentId)
        if (p) p.children.push(n)
      })
    }
  })

  const hidden = new Set()
  allNodes.forEach(node => {
    if (node._collapsed) {
      findDescendants(node.id, nodeMap).forEach(id => hidden.add(id))
    }
  })

  const visibleNodes = allNodes.filter(n => !hidden.has(n.id))
  const visibleIds = new Set(visibleNodes.map(n => n.id))

  const visibleLinks = []
  visibleNodes.forEach(n => {
    if (n.originalParents) {
      n.originalParents.forEach(p => {
        if (visibleIds.has(p)) visibleLinks.push({ source: p, target: n.id })
      })
    }
  })

  return { visibleNodes, visibleLinks }
}

/** 仅更新“选中”样式 */
export function updateSelectionStyles(svgElement, selectedIds) {
  const selectedStyle = '0 0 0 3px #3b82f6'
  const defaultStyle = 'none'
  d3.select(svgElement).selectAll('.node')
    .each(function (d) {
      if (!d || !d.id) return
      const card = d3.select(this).select('.node-card')
      card.style('box-shadow', selectedIds.includes(d.id) ? selectedStyle : defaultStyle)
    })
}

/** 仅更新可见性（折叠/展开），不改变缩放与布局 */
export function updateVisibility(svgElement, allNodes) {
  const { visibleNodes, visibleLinks } = getVisibleNodesAndLinks(allNodes)
  const visibleNodeIds = new Set(visibleNodes.map(n => n.id))
  const visibleLinkIds = new Set(visibleLinks.map(l => `${l.source}->${l.target}`))

  d3.select(svgElement)
    .selectAll('.node')
    .style('display', d => visibleNodeIds.has(d.id) ? null : 'none')
    .each(function (d) {
      const btn = d3.select(this).select('button.collapse-btn')
      if (btn.size()) {
        btn.text(d._collapsed ? '+' : '-')
          .style('color', d._collapsed ? '#E4080A' : '#9ca3af')
      }
    })

  d3.select(svgElement)
    .selectAll('.link')
    .style('display', d => visibleLinkIds.has(`${d.v}->${d.w}`) ? null : 'none')
}

/** 完整重绘（重新布局 & 初始缩放） */
export function renderTree(
  svgElement,
  allNodesData,
  selectedIds,
  emit,           // (eventName, ...args) => void
  workflowTypes   // { red:{color,type,defaultModuleId}, yellow:{...}, green:{...} }
) {
  const wrapper = d3.select(svgElement)
  wrapper.html('')

  const { visibleNodes, visibleLinks } = getVisibleNodesAndLinks(allNodesData)
  if (!visibleNodes.length) {
    wrapper.append('text')
      .attr('x', '50%').attr('y', '50%')
      .attr('text-anchor', 'middle')
      .attr('fill', '#9ca3af')
      .text('暂无数据，请从右侧开始生成...')
    return
  }

  // Dagre 布局
  const g = new dagre.graphlib.Graph()
  g.setGraph({ rankdir: 'LR', nodesep: 100, ranksep: 120 })
  g.setDefaultEdgeLabel(() => ({}))

  // --- (核心修复 1) 动态计算高度 ---
  const BASE_CARD_HEIGHT = 180; // (Header + 140px图片 + Footer)
  const PROMPT_AREA_HEIGHT = 30; // (为 Prompt 额外增加的高度)

  visibleNodes.forEach(node => {
    const isInit = node.module_id === 'Init'
    const width = isInit ? 60 : 140; // 宽度保持不变

    // 重新计算 hasPrompt 逻辑
    const promptText = (node.parameters && node.parameters.positive_prompt) ? node.parameters.positive_prompt : null
    const hasPrompt = typeof promptText === 'string' && promptText.trim() !== ''

    // 计算动态高度
    const height = isInit ? 60 : (hasPrompt ? BASE_CARD_HEIGHT + PROMPT_AREA_HEIGHT : BASE_CARD_HEIGHT);

    // 把计算结果存回节点，方便后面使用
    node.calculatedHeight = height;
    node.calculatedWidth = width;

    g.setNode(node.id, {
      label: node.module_id,
      width: width,
      height: height, // <-- (修复 A) 使用动态高度
    })
  })
  visibleLinks.forEach(l => g.setEdge(l.source, l.target))
  dagre.layout(g)

  const dagreNodes = new Map(g.nodes().map(id => [id, g.node(id)]))
  const dagreEdges = g.edges().map(e => {
    const edgeData = g.edge(e)
    return { v: e.v, w: e.w, points: edgeData.points }
  })

  // SVG 容器与缩放
  const width = svgElement.clientWidth || 1200
  const height = svgElement.clientHeight || 600
  const svg = wrapper
    .attr('viewBox', `0 0 ${width} ${height}`)
    .attr('preserveAspectRatio', 'xMidYMid meet')

  const defs = svg.append('defs')
  ;[
    { id: 'red', color: workflowTypes.red.color },
    { id: 'yellow', color: workflowTypes.yellow.color },
    { id: 'green', color: workflowTypes.green.color },
    { id: 'default', color: defaultLinkColor },
  ].forEach(c => {
    defs.append('marker')
      .attr('id', `arrowhead-${c.id}`)
      .attr('viewBox', '-0 -5 10 10')
      .attr('refX', 10).attr('refY', 0)
      .attr('orient', 'auto')
      .attr('markerWidth', 6).attr('markerHeight', 6)
      .attr('xoverflow', 'visible')
      .append('path')
      .attr('d', 'M 0,-5 L 10 ,0 L 0,5')
      .style('fill', c.color)
      .style('stroke', 'none')
  })

  const layoutGroup = svg.append('g')
  const linkGroup = layoutGroup.append('g').attr('class', 'links')
  const nodeGroup = layoutGroup.append('g').attr('class', 'nodes')

  const zoom = d3.zoom()
    .scaleExtent([0.1, 2.5])
    .on('zoom', (ev) => layoutGroup.attr('transform', ev.transform))
    .filter((ev) => {
      const target = ev.target
      return !(target && target.closest && target.closest('foreignObject'))
    })
  svg.call(zoom)

  const graphWidth = g.graph().width || width
  const graphHeight = g.graph().height || height
  const s = Math.min(1, Math.min(width / graphWidth, height / graphHeight) * 0.9)
  const tx = (width - graphWidth * s) / 2
  const ty = (height - graphHeight * s) / 2
  svg.call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(s))

  // 背景点击：取消选择
  const svgDom = svg.node()
  svgDom.addEventListener('click', (ev) => {
    if (ev.target === svgDom) {
      svgElement.querySelectorAll('.node-card').forEach(el => el.classList.remove('selected'))
      emit('update:selectedIds', [])
    }
  })

  function getLinkStyle(d) {
    const target = allNodesData.find(n => n.id === d.w)
    const linkColor = target && target.linkColor
    if (linkColor === workflowTypes.red.color) return { color: workflowTypes.red.color, id: 'url(#arrowhead-red)' }
    if (linkColor === workflowTypes.yellow.color) return { color: workflowTypes.yellow.color, id: 'url(#arrowhead-yellow)' }
    if (linkColor === workflowTypes.green.color) return { color: workflowTypes.green.color, id: 'url(#arrowhead-green)' }
    return { color: defaultLinkColor, id: 'url(#arrowhead-default)' }
  }

  // Links
  linkGroup.selectAll('path.link')
    .data(dagreEdges)
    .enter().append('path')
    .attr('class', 'link')
    .each(function (d) {
      const st = getLinkStyle(d)
      d3.select(this).style('stroke', st.color).attr('marker-end', st.id)
    })
    .attr('d', d => lineGenerator(d.points))

  // Nodes
  const nodeSel = nodeGroup.selectAll('.node')
    .data(visibleNodes, d => d.id)
    .enter().append('g')
    .attr('class', 'node')
    .attr('transform', d => {
      const n = dagreNodes.get(d.id)
      return `translate(${n.x},${n.y})`
    })

  nodeSel.each(function (d) {
    const gEl = d3.select(this)

    // Init 特例
    if (d.module_id === 'Init') {
      gEl.append('circle').attr('r', 30).attr('fill', '#fff').attr('stroke', '#6b7280').attr('stroke-width', 2)
      gEl.append('text')
        .attr('text-anchor', 'middle').attr('dy', '0.35em')
        .style('font-size', '14px').style('fill', '#6b7280').style('pointer-events', 'none')
        .text('Init')
      gEl.style('cursor', 'pointer')
        .on('click', (ev) => {
          ev.stopPropagation()
          const selected = new Set(selectedIds)
          if (selected.has(d.id)) selected.delete(d.id)
          else if (selected.size < 2) selected.add(d.id)
          emit('update:selectedIds', Array.from(selected))
        })
      return
    }

    // 卡片容器
     const fo = gEl.append('foreignObject')
      .attr('width', d.calculatedWidth) // <-- (修复 B)
      .attr('height', d.calculatedHeight) // <-- (修复 B)
      .attr('x', -d.calculatedWidth / 2) // <-- (修复 C)
      .attr('y', -d.calculatedHeight / 2) // <-- (修复 C)
      .style('overflow', 'visible')

    const card = fo.append('xhtml:div')
      .attr('class', 'node-card')
      .style('width', '100%')
      .style('height', '100%')
      .style('display', 'flex').style('flex-direction', 'column')
      .style('border-width', '2px')
      .style('position', 'relative')
      .style('cursor', 'pointer')
      .style('background-color', '#ffffff')

    const border =
      d.status === 'running' ? '#3b82f6' :
      d.status === 'success' ? '#22c55e' :
      d.status === 'error'   ? '#ef4444' : '#d1d5db'
    card.style('border-color', border)
    card.style('box-shadow', selectedIds.includes(d.id) ? '0 0 0 3px #3b82f6' : 'none')

    // 选中逻辑（忽略按钮/媒体/Prompt）
    card.on('click', (ev) => {
      if (ev.target && ev.target.closest && ev.target.closest('button, img, video, .prompt-div-inner')) return
      ev.stopPropagation()
      const selected = new Set(selectedIds)
      const on = selected.has(d.id)
      if (on) selected.delete(d.id)
      else if (selected.size < 2) selected.add(d.id)
      card.style('box-shadow', on ? 'none' : '0 0 0 3px #3b82f6')
      emit('update:selectedIds', Array.from(selected))
    })

    // Hover 显示右上角按钮 + ▶
    card.on('mouseenter', function () {
      d3.select(this).selectAll('.add-clip-btn, .dots-container').style('opacity', '1')
    })
    card.on('mouseleave', function () {
      d3.select(this).selectAll('.add-clip-btn, .dots-container').style('opacity', '0')
    })

    // Header
    const header = card.append('xhtml:div')
      .style('display', 'flex')
      .style('justify-content', 'space-between')
      .style('align-items', 'center')
      .style('padding', '4px')
      .style('border-bottom', '1px solid #e5e7eb')
      .style('flex-shrink', '0')

    header.append('xhtml:h3')
      .style('font-size', '8px').style('font-weight', '700').style('color', '#1f2937')
      .style('overflow', 'hidden').style('text-overflow', 'ellipsis').style('white-space', 'nowrap')
      .style('min-width','0')
      .text(d.module_id || '(节点)')

    if (d.module_id !== 'Init' && d.module_id !== 'ROOT') {
      header.append('xhtml:button')
        .style('background-color', '#fff')
        .style('color', '#E4080A')
        .style('border-radius', '50%')
        .style('border', 'none')
        .style('width', '16px').style('height', '16px')
        .style('font-size', '16px').style('line-height', '16px').style('text-align', 'center')
        .style('cursor', 'pointer').style('flexShrink', '0')
        .html('&#xD7;')
        .on('mousedown', (ev) => ev.stopPropagation())
        .on('click', (ev) => { ev.stopPropagation(); emit('delete-node', d.id) })
    }

    // 媒体/Prompt
    const hasMedia = !!(d.media && d.media.rawPath)
    const mediaUrl = hasMedia ? d.media.url : ''
    const rawPath = hasMedia ? d.media.rawPath : ''
    const isVideo = typeof rawPath === 'string' && (rawPath.includes('.mp4') || rawPath.includes('subfolder=video'))
    const canAddToStitch = hasMedia
    const promptText = (d.parameters && d.parameters.positive_prompt) ? d.parameters.positive_prompt : null
    const hasPrompt = typeof promptText === 'string' && promptText.trim() !== ''

    // Content
    const content = card.append('xhtml:div')
      // --- (核心修复 3) ---
      .style('flex-grow', '0') // 图片区永远不拉伸
      .style('flex-shrink', '0') // 图片区永远不收缩
      .style('height', '100px') // (关键) 固定图片区高度为 140px
      // --- (修复结束) ---
      .style('min-height', '0')
      .style('position', 'relative')

    if (hasMedia) {
      if (isVideo) {
        const v = content.append('xhtml:video')
          .style('width', '100%').style('height', '100%').style('object-fit', 'contain').style('display', 'block')
          .attr('muted', true).attr('playsinline', true).attr('preload', 'metadata')
          .on('mousedown', (ev) => ev.stopPropagation())
          .on('click', (ev) => { ev.stopPropagation(); emit('open-preview', mediaUrl, d.media.type) })
        const el = v.node()
        el.autoplay = true; el.loop = true; el.muted = true; el.playsInline = true; el.src = mediaUrl
      } else {
        content.append('xhtml:img')
          .style('width', '100%').style('height', '100%').style('object-fit', 'contain').style('display', 'block')
          .attr('src', mediaUrl).attr('alt', d.module_id || 'thumb')
          .on('mousedown', (ev) => ev.stopPropagation())
          .on('click', (ev) => { ev.stopPropagation(); emit('open-preview', mediaUrl, d.media.type) })
      }
    } else {
      content.append('xhtml:div')
        .style('width', '100%').style('height', '100%')
        .style('display', 'flex').style('align-items', 'center').style('justify-content', 'center')
        .style('font-size', '12px').style('color', '#6b7280').text('无缩略图')
    }

    // 右上角三色按钮
    const dots = content.append('xhtml:div')
      .attr('class', 'dots-container')
      .style('position', 'absolute')
      .style('display', 'flex').style('flex-direction', 'column')
      .style('align-items', 'center').style('justify-content', 'center')
      .style('opacity', '0').style('transition', 'opacity 0.15s ease-in-out')
      .style('z-index', '10').style('top', '4px').style('right', '4px')
    ;(['red', 'yellow', 'green']).forEach((key, idx) => {
      const info = workflowTypes[key]
      dots.append('xhtml:button')
        .style('background-color', info.color)
        .style('width', '16px').style('height', '16px').style('border-radius', '50%')
        .style('border', 'none').style('padding', '0').style('cursor', 'pointer')
        .style('transition', 'transform 0.15s ease-in-out')
        .style('margin-top', idx > 0 ? '4px' : '0')
        .attr('title', `Start ${info.type} workflow`)
        .on('mouseenter', function () { d3.select(this).style('transform', 'scale(1.25)') })
        .on('mouseleave', function () { d3.select(this).style('transform', 'scale(1)') })
        .on('mousedown', (ev) => ev.stopPropagation())
        .on('click', (ev) => { ev.stopPropagation(); emit('open-generation', d, info.defaultModuleId, info.type) })
    })

    // Prompt 区（若有）
    if (hasPrompt) {
      const promptDiv = card.append('xhtml:div')
        .attr('class', 'prompt-div-inner')
        .style('flex-grow', '1').style('flex-shrink', '1').style('min-height', '0')
        .style('overflow-y', 'auto').style('padding', '4px')
        .style('border-top', '1px solid #e5e7eb')
        .style('font-size', '10px').style('color', '#374151')
        .style('white-space', 'pre-wrap').style('word-break', 'break-all')
        .on('mousedown', (ev) => ev.stopPropagation())
      promptDiv.append('xhtml:div').text(promptText)
    }

    // Footer：▶
    const footer = card.append('xhtml:div')
      .style('display', 'flex').style('justify-content', 'flex-end')
      .style('padding', '2px')

    if (canAddToStitch) {
      footer.append('xhtml:button')
        .attr('class', 'add-clip-btn')
        .html('&#9658;')
        .style('opacity', '0').style('transition', 'opacity 0.15s ease-in-out')
        .style('width', '20px').style('height', '20px')
        .style('display', 'flex').style('align-items', 'center').style('justify-content', 'center')
        .style('color', '#3b82f6').style('font-size', '1.125rem')
        .style('border', 'none').style('background-color', 'transparent').style('padding', '0')
        .style('cursor', 'pointer')
        .on('mousedown', (ev) => ev.stopPropagation())
        .on('click', (ev) => { ev.stopPropagation(); emit('add-clip', d, isVideo ? 'video' : 'image') })
    }

    // 收缩/展开按钮（有子节点才显示）
    const tempMap = new Map(allNodesData.map(n => [n.id, { ...n, children: [] }]))
    allNodesData.forEach(n => {
      if (n.originalParents) n.originalParents.forEach(p => tempMap.get(p)?.children.push(n))
    })
    const hasChildren = !!(tempMap.get(d.id) && tempMap.get(d.id).children.length)

    if (hasChildren) {
      card.append('xhtml:button')
        .attr('class', 'collapse-btn')
        .style('position', 'absolute').style('bottom', '8px').style('left', '0')
        .style('background-color', '#ffffff')
        .style('color', d._collapsed ? '#E4080A' : '#9ca3af')
        .style('border-radius', '50%')
        .style('width', '16px').style('height', '16px').style('fontSize', '16px')
        .style('lineHeight', '16px').style('textAlign', 'center').style('fontWeight', '700')
        .style('zIndex', '10').style('border', 'none').style('cursor', 'pointer')
        .style('transition', 'background-color 0.15s ease-in-out')
        .style('transform', 'translate(-25%, 25%)')
        .text(d._collapsed ? '+' : '-')
        .on('mouseenter', function () { d3.select(this).style('background-color', '#ffffff') })
        .on('mouseleave', function () { d3.select(this).style('background-color', '#ffffff') })
        .on('mousedown', (ev) => ev.stopPropagation())
        .on('click', (ev) => { ev.stopPropagation(); emit('toggle-collapse', d.id) })
    }

    // Tooltip
    const titleText =
      (d.module_id || '') +
      (d.created_at ? (' · ' + d.created_at) : '') +
      (d.status ? (' · ' + d.status) : '')
    gEl.attr('title', titleText)
  })
}
