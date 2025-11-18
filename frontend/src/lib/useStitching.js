// src/composables/useStitching.js
import { ref, computed, nextTick } from 'vue'
// d3 其实不再强依赖了，但如果你后面想用 scale 可以保留这一行
// import * as d3 from 'd3'

export function useStitching(props, emit) {
  /* ---------------- 1. 基础状态 ---------------- */
  // 唯一真理：所有“秒 -> 像素”都用这个系数
  const pixelsPerSecond = ref(40)

  const draggedClip = ref(null)              // { track: 'video' | 'audio', index }
  const draggedOver = ref(null)              // { track: 'video' | 'audio', index }
  const isDraggingOverContainer = ref(null)  // 'video' | 'audio' | null

  /* ---------------- 2. clip 宽度（直接用秒*pps） ---------------- */

  const videoClipWidths = computed(() =>
    (props.clips || []).map(c =>
      `${Math.max(50, (c.duration || 0) * pixelsPerSecond.value)}px`
    )
  )

  const audioClipWidths = computed(() =>
    (props.audioClips || []).map(c =>
      `${Math.max(30, (c.duration || 0) * pixelsPerSecond.value)}px`
    )
  )

  /* ---------------- 3. 时间轴绘制：0.01 / 0.1 / 1s 三层刻度 ---------------- */
  function drawTimeline() {
    nextTick(() => {
      const container = document.getElementById('timeline-ruler')
      if (!container) return

      const wrapper = container.parentElement
      const wrapperWidth = wrapper?.getBoundingClientRect().width || 300

      const clips = props.clips || []
      const audio = props.audioClips || []

      // 计算真实时长
      const totalVideo = clips.reduce((s, c) => s + (c.duration || 0), 0)
      const totalAudio = audio.reduce((s, c) => s + (c.duration || 0), 0)
      const totalDuration = Math.max(totalVideo, totalAudio)  // 重要：这里没有最小值1

      // 核心：宽度至少等于父容器宽度
      const timelineWidth =
        Math.max(
          wrapperWidth,
          (totalDuration || 0) * pixelsPerSecond.value
        )

      const height = 30

      // 更新容器尺寸
      container.innerHTML = ''
      container.style.width = timelineWidth + 'px'
      container.style.height = height + 'px'
      container.style.position = 'relative'
      container.style.background = '#fafafa'
      container.style.overflow = 'hidden'

      // ===== 下面开始画刻度（后面你需要的 0.01 / 0.1 / 1s） =====
      const SMALL_STEP = 0.01
      const EPS = 1e-6

      const maxT = Math.max(totalDuration, wrapperWidth / pixelsPerSecond.value)
      const maxIndex = Math.round(maxT / SMALL_STEP)

      // baseline
      const baseline = document.createElement('div')
      baseline.style.position = 'absolute'
      baseline.style.left = '0'
      baseline.style.right = '0'
      baseline.style.bottom = '0'
      baseline.style.height = '1px'
      baseline.style.background = '#e5e7eb'
      container.appendChild(baseline)

      // 绘制所有 0.01s 小刻度
      for (let i = 0; i <= maxIndex; i++) {
        const t = i * SMALL_STEP
        const x = t * pixelsPerSecond.value
        let level = 'small'

        if (Math.abs(t - Math.round(t)) < EPS) {
          level = 'major'
        } else if (Math.abs(t * 10 - Math.round(t * 10)) < EPS) {
          level = 'medium'
        }

        const tick = document.createElement('div')
        tick.style.position = 'absolute'
        tick.style.left = `${x}px`
        tick.style.bottom = '0'

        const line = document.createElement('div')
        line.style.width = '1px'

        if (level === 'small') {
          line.style.height = '4px'
          line.style.background = '#eee'
        } else if (level === 'medium') {
          line.style.height = '7px'
          line.style.background = '#ccc'
        } else {
          line.style.height = '10px'
          line.style.background = '#999'
          const label = document.createElement('div')
          label.textContent = `${t.toFixed(1)}s`
          label.style.position = 'absolute'
          label.style.bottom = '12px'
          label.style.left = '50%'
          label.style.transform = 'translateX(-50%)'
          label.style.fontSize = '10px'
          label.style.color = '#555'
          tick.appendChild(label)
        }

        tick.appendChild(line)
        container.appendChild(tick)
      }
    })
  }

  /* ---------------- 4. 缩放：滚轮只改 pixelsPerSecond ---------------- */

  function handleZoom(e) {
    const factor = e.deltaY > 0 ? 0.9 : 1.1
    pixelsPerSecond.value = Math.max(
      5,
      Math.min(800, pixelsPerSecond.value * factor)
    )
    // ⚠️ 不在这里直接调用 drawTimeline，
    // 重绘在 StitchingPanel.vue 里通过 watch(pixelsPerSecond) 完成，
    // clip 宽度和时间轴一起更新。
  }

  /* ---------------- 5. 拖拽逻辑（保留你原来的） ---------------- */

  function handleDragStart(trackType, index, e) {
    draggedClip.value = { track: trackType, index }
    if (e?.dataTransfer) {
      e.dataTransfer.effectAllowed = 'move'
      e.dataTransfer.setData('text/plain', String(index))
    }
  }

  function handleDragOverItem(trackType, index) {
    draggedOver.value = { track: trackType, index }
    isDraggingOverContainer.value = null
  }

  function handleDragLeaveItem() {
    draggedOver.value = null
  }

  function handleDropOnItem(targetTrack, targetIndex) {
    const src = draggedClip.value
    if (!src || src.track !== targetTrack) {
      console.warn('跨轨道拖放无效。')
      return
    }
    if (src.index === targetIndex) return

    const isVideo = src.track === 'video'
    const list = isVideo ? [...(props.clips || [])] : [...(props.audioClips || [])]
    const emitEvent = isVideo ? 'update:clips' : 'update:audioClips'

    const [moved] = list.splice(src.index, 1)
    if (moved) list.splice(targetIndex, 0, moved)

    emit(emitEvent, list)
    draggedOver.value = null
  }

  function handleDragEnd() {
    draggedClip.value = null
    draggedOver.value = null
    isDraggingOverContainer.value = null
  }

  function handleDragOverContainer(trackType) {
    if (draggedOver.value === null) {
      isDraggingOverContainer.value = trackType
    }
  }

  function handleDragLeaveContainer() {
    isDraggingOverContainer.value = null
  }

  function handleDropContainer(targetTrack) {
    const src = draggedClip.value
    if (
      !src ||
      src.track !== targetTrack ||
      isDraggingOverContainer.value !== targetTrack
    ) {
      console.warn('容器拖放无效。')
      return
    }

    const isVideo = src.track === 'video'
    const list = isVideo ? [...(props.clips || [])] : [...(props.audioClips || [])]
    const emitEvent = isVideo ? 'update:clips' : 'update:audioClips'

    const [moved] = list.splice(src.index, 1)
    if (moved) list.push(moved)

    emit(emitEvent, list)
  }

  /* ---------------- 6. 导出 ---------------- */

  return {
    pixelsPerSecond,
    videoClipWidths,
    audioClipWidths,

    draggedClip,
    draggedOver,
    isDraggingOverContainer,

    drawTimeline,
    handleZoom,
    handleDragStart,
    handleDragOverItem,
    handleDragLeaveItem,
    handleDropOnItem,
    handleDragEnd,
    handleDragOverContainer,
    handleDragLeaveContainer,
    handleDropContainer,
  }
}
