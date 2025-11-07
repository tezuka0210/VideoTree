import { ref, computed, watch, nextTick } from 'vue'
import VideoEditingTimeline from 'video-editing-timeline'

/* --------------  主逻辑：返回给组件用  -------------- */
export function useStitching(props, emit) {
  /* ----- 响应式状态 ----- */
  const pixelsPerSecond = ref(40)          // 缩放级别
  const draggedClipIndex   = ref(null)     // 正被拖的索引
  const draggedOverIndex   = ref(null)     // 目标索引
  const isDraggingOverContainer = ref(false)

  /* ----- 计算属性 ----- */
  const clipWidths = computed(() =>
    props.clips.map(c =>
      `${Math.max(50, c.duration * pixelsPerSecond.value)}px`
    )
  )

  /* ----- 时间尺 ----- */
  function drawTimeline(pxPerSec) {
    nextTick(() => {              // 保证 canvas 已渲染
      const canvas = document.getElementById('timeline-ruler')
      if (!canvas) return
      const Constructor = VideoEditingTimeline.default || VideoEditingTimeline

      let newScaleTime = 1
      let newScalePx   = pxPerSec
      if (pxPerSec > 100) { newScaleTime = 0.5; newScalePx = pxPerSec * 0.5 }
      if (pxPerSec < 10)  { newScaleTime = 5;   newScalePx = pxPerSec * 5 }

      new Constructor({
        el: '#timeline-ruler',
        canvasWidth: canvas.clientWidth,
        canvasHeight: 30,
        minimumScale: newScalePx,
        minimumScaleTime: newScaleTime
      })
    })
  }

  /* ----- 缩放 ----- */
  function handleZoom(e) {
    const factor = e.deltaY > 0 ? 0.9 : 1.1
    pixelsPerSecond.value =
      Math.max(10, Math.min(800, pixelsPerSecond.value * factor))
  }

  /* ----- 拖拽核心 ----- */
  function handleDragStart(index, e) {
    console.log(`%c[DRAG START]`, 'color: blue; font-weight: bold;', `拖拽开始，索引: ${index}`);
    draggedClipIndex.value = index
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', String(index))
  }
  function handleDragOverItem(index) {
    if (draggedOverIndex.value !== index) {
    console.log(`%c[DRAG OVER ITEM]`, 'color: #999;', `悬停在 视频块 ${index} 上方`);
  }
    draggedOverIndex.value = index
    isDraggingOverContainer.value = false
  }
  function handleDragLeaveItem() {
    draggedOverIndex.value = null
  }
  function handleDropOnItem(targetIndex) {
    // console.log(`%c[DROP ON ITEM]`, 'color: green; font-weight: bold;', `在 视频块 ${targetIndex} 上松手`);
    const src = draggedClipIndex.value
    // console.log(`  - 来源索引 (src): ${src}`);
    // console.log(`  - 目标索引 (targetIndex): ${targetIndex}`);
if (src === null || src === targetIndex) {
    console.warn('  - 拖拽无效 (来源=null 或 来源=目标)，操作取消。');
    return
}

    const list = [...props.clips]
    const [moved] = list.splice(src, 1)
    if (moved) list.splice(targetIndex, 0, moved)
    // console.log('  - [准备 Emit] 新的列表:', list.map(c => c.nodeId)); // 只打印 ID 方便查看
    emit('update:clips', list)

    draggedOverIndex.value = null
  }
  function handleDragEnd() {
    // console.log(`%c[DRAG END]`, 'color: red; font-weight: bold;', '拖拽结束');
    draggedClipIndex.value = null; // (修复) 确保这里用 .value
    draggedOverIndex.value = null; // (修复) 确保这里用 .value
    isDraggingOverContainer.value = false
  }

  /* ----- 拖进空白处 ----- */
  function handleDragOverContainer() {
    if (draggedOverIndex.value === null) isDraggingOverContainer.value = true
  }
  function handleDragLeaveContainer() {
    isDraggingOverContainer.value = false
  }
  function handleDropContainer() {
    // console.log(`%c[DROP ON CONTAINER]`, 'color: green; font-weight: bold;', '在 空白容器 上松手');
    const src = draggedClipIndex.value
    if (src === null || !isDraggingOverContainer.value) {
        console.warn('  - 拖拽无效 (来源=null 或 非容器拖拽)，操作取消。');
        return
    }
    const list = [...props.clips]
    const [moved] = list.splice(src, 1)
    if (moved) list.push(moved)
    // console.log('  - [准备 Emit] 新的列表:', list.map(c => c.nodeId)); // 只打印 ID 方便查看
    emit('update:clips', list)
  }

  return {
    pixelsPerSecond,
    clipWidths,
    draggedClipIndex,
    draggedOverIndex,
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
    drawTimeline
  }
}