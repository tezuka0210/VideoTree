<template>
  <!-- 外层容器 -->
  <div class="container">
    <section class="session-card">
      <!-- 头部区域 -->
      <div class="card-header">
        <div class="header-top">
          <h2 class="header-title">
            <svg class="title-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8h2a2 2 0 012 2v6a2 2 0 01-2 2h-2v4l-4-4H9a1.994 1.994 0 01-1.414-.586m0 0L11 14h4a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2v4l.586-.586z"></path>
            </svg>
            Sessions
          </h2>
          <span class="session-count">{{ sessions.length }} {{ sessions.length === 1 ? 'session' : 'sessions' }}</span>
        </div>

        <!-- 新建按钮 -->
        <button
          @click="createNewSession"
          type="button"
          class="new-session-btn"
          title="New Session"
        >
          <div class="btn-content">
            <svg class="btn-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 5v14M5 12h14"></path>
            </svg>
            <span class="btn-text">New Session</span>
          </div>
        </button>
      </div>

      <!-- 列表区域 -->
      <div class="session-list">
        <!-- 无数据状态 -->
        <div class="empty-state" v-if="sessions.length === 0">
          <svg class="empty-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
          </svg>
          <p class="empty-title">No sessions yet</p>
          <p class="empty-desc">Click "New Session" to create your first session</p>
        </div>

        <!-- 会话列表项 -->
        <div
          v-for="session in sessions"
          :key="session.id"
          @click="selectSession(session.id)"
          :class="['session-item', { 'active': currentSessionId === session.id }]"
        >
          <span class="status-dot"></span>
          <p class="session-title">{{ session.title }}</p>
          <span 
            class="delete-btn"
            @click.stop="deleteSession(session.id)"
            title="Delete session"
          >
            <svg class="delete-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
            </svg>
          </span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

// 定义会话类型接口
interface Session {
  id: number;
  title: string;
}

// 模拟数据
const sessions = ref<Session[]>([
  { id: 1, title: 'Guqin' },
  { id: 2, title: 'Three colored camel figurines carrying music' },
  { id: 3, title: 'New Exploration' }
])

const currentSessionId = ref<number>(1)

// 选择会话
function selectSession(id: number) {
  currentSessionId.value = id
}

// 创建新会话
function createNewSession() {
  const newId = Date.now()
  sessions.value.unshift({
    id: newId,
    title: 'New Session'
  })
  currentSessionId.value = newId
  
  // 滚动到顶部
  setTimeout(() => {
    const container = document.querySelector('.session-list')
    if (container) {
      container.scrollTop = 0
    }
  }, 100)
}

// 删除会话
function deleteSession(id: number) {
  // 不能删除最后一个会话
  if (sessions.value.length <= 1) return
  
  const index = sessions.value.findIndex(session => session.id === id)
  if (index !== -1) {
    sessions.value.splice(index, 1)
    
    if (currentSessionId.value === id && sessions.value.length > 0) {
      const firstSession = sessions.value[0]
      if (firstSession) {
        currentSessionId.value = firstSession.id
      }
    }
  }
}
</script>

<style scoped>
/* 全局样式重置和基础设置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  font-family: 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  border-radius: inherit;
}

/* 容器样式 */
.container {
  width: 100%;
  max-width: 380px;
  margin: 0 auto;
  padding: 24px 16px;
}

/* 卡片主体 */
.session-card {
  width: 100%;
  background: #ffffff;
  border-radius: 20px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  border: 1px solid #f0f0f0;
  overflow: hidden;
  transition: all 0.3s ease;
}

.session-card:hover {
  box-shadow: 0 6px 25px rgba(0, 0, 0, 0.08);
}

/* 卡片头部 */
.card-header {
  padding: 16px;
  border-bottom: 1px solid #f0f0f0;
  background: #f8f9fa;
  border-radius: 20px 20px 0 0;
}

.header-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.header-title {
  font-size: 14px;
  font-weight: 600;
  color: #333333;
  display: flex;
  align-items: center;
  gap: 8px;
  letter-spacing: 0.3px;
}

.title-icon {
  width: 16px;
  height: 16px;
  color: #6b7280; /* 灰色主色调 */
  background: #f3f4f6; /* 浅灰色背景 */
  border-radius: 50%;
  padding: 2px;
}

.session-count {
  font-size: 12px;
  color: #6b7280;
  background: #f3f4f6;
  padding: 2px 8px;
  border-radius: 100px;
}

/* 新建会话按钮 */
.new-session-btn {
  width: 100%;
  aspect-ratio: 5/1;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px dashed #d1d5db;
  border-radius: 16px;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.3s ease;
  transform: scale(1);
}

.new-session-btn:hover {
  border-color: #6b7280; /* 灰色 hover */
  background: #f3f4f6; /* 浅灰色背景 */
  color: #4b5563; /* 深灰色文字 */
  box-shadow: 0 2px 8px rgba(107, 114, 128, 0.1);
  transform: scale(1.01);
}

.new-session-btn:active {
  transform: scale(0.98);
}

.btn-content {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-icon {
  width: 20px;
  height: 20px;
  transition: transform 0.3s ease;
  border-radius: 50%;
  padding: 2px;
}

.new-session-btn:hover .btn-icon {
  transform: rotate(90deg);
}

.btn-text {
  font-size: 14px;
  font-weight: 500;
}

/* 会话列表区域 */
.session-list {
  flex: 1;
  min-height: 0;
  max-height: 500px;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  scroll-behavior: smooth;
}

/* 自定义滚动条 */
.session-list::-webkit-scrollbar {
  width: 6px;
}

.session-list::-webkit-scrollbar-track {
  background: #f8f8f8;
  border-radius: 3px;
  margin: 4px 0;
}

.session-list::-webkit-scrollbar-thumb {
  background: #e0e0e0;
  border-radius: 3px;
}

.session-list::-webkit-scrollbar-thumb:hover {
  background: #d0d0d0;
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 160px;
  color: #9ca3af;
  background: #f9fafb;
  border-radius: 16px;
  padding: 24px;
}

.empty-icon {
  width: 40px;
  height: 40px;
  margin-bottom: 12px;
  opacity: 0.5;
  background: #f3f4f6;
  border-radius: 50%;
  padding: 6px;
}

.empty-title {
  font-size: 14px;
  font-weight: 500;
}

.empty-desc {
  font-size: 12px;
  margin-top: 4px;
  opacity: 0.7;
}

/* 会话列表项 */
.session-item {
  padding: 14px 16px;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
  display: flex;
  align-items: center;
  gap: 12px;
  background: #f9fafb;
  color: #374151;
}

.session-item:hover {
  background: #f3f4f6;
  border-color: #e5e7eb;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.session-item.active {
  background: #6b7280; /* 灰色主色 */
  color: white;
  box-shadow: 0 4px 12px rgba(107, 114, 128, 0.3);
  border-color: #4b5563; /* 深灰色边框 */
}

.session-item:focus {
  outline: 2px solid rgba(107, 114, 128, 0.5);
  outline-offset: 2px;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #d1d5db;
}

.session-item.active .status-dot {
  background: white;
}

.session-title {
  line-height: 1.4;
  word-break: break-word;
  flex: 1;
  font-weight: 500;
  font-size: 14px;
}

/* 删除按钮 */
.delete-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  opacity: 0;
  transition: all 0.2s ease;
  transform: scale(0.9);
  background: #e5e7eb;
  color: #4b5563;
}

.session-item:hover .delete-btn {
  opacity: 1;
  transform: scale(1);
}

.delete-btn:hover {
  background: #d1d5db;
}

.session-item.active .delete-btn {
  background: rgba(255, 255, 255, 0.2);
  color: white;
}

.session-item.active .delete-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.delete-icon {
  width: 16px;
  height: 16px;
}
</style>