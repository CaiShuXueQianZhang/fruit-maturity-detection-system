<template>
  <div class="header-container">
    <div class="breadcrumbs">
      <el-icon class="breadcrumb-icon"><House /></el-icon>
      <span class="breadcrumb-separator">/</span>
      <span class="breadcrumb-text">智能检测</span>
    </div>

    <div class="header-actions">
      <el-tag type="success" effect="light" class="status-tag">
        <el-icon class="el-icon--left"><Check /></el-icon>
        检测完成
      </el-tag>

      <div class="action-icons">
        <el-icon class="action-icon"><Grid /></el-icon>
        <el-icon class="action-icon"><Bell /></el-icon>
        <el-icon class="action-icon"><QuestionFilled /></el-icon>
        <el-dropdown trigger="click" @command="handleCommand">
          <div class="user-dropdown">
            <el-avatar class="user-avatar" size="32">
              <img
                src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png"
                alt="用户头像"
              />
            </el-avatar>
            <div class="user-info">
              <div class="user-name">{{ displayName }}</div>
              <div class="user-role">{{ displayRole }}</div>
            </div>
            <el-icon class="dropdown-icon"><CaretBottom /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">个人中心</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { computed, ref } from 'vue'
import { logout } from '../api/auth'
import {
  Check,
  Grid,
  Bell,
  QuestionFilled,
  CaretBottom,
  House,
} from "@element-plus/icons-vue";

const router = useRouter()

const storedUser = ref({})
try {
  storedUser.value = JSON.parse(localStorage.getItem('user') || '{}')
} catch (e) {
  storedUser.value = {}
}

const displayName = computed(() => storedUser.value.nickname || storedUser.value.username || '用户')
const displayRole = computed(() => storedUser.value.role === 'admin' ? '管理员' : '普通用户')

const handleCommand = async (command) => {
  if (command === 'logout') {
    const token = localStorage.getItem('token')
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    router.replace('/login')
    if (token) {
      logout().catch(() => {})
    }
  } else if (command === 'profile') {
    router.push('/profile')
  }
}
</script>

<style scoped>
.header-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.breadcrumbs {
  display: flex;
  align-items: center;
}

.breadcrumb-icon {
  font-size: 14px;
  color: var(--text-secondary);
}

.breadcrumb-separator {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0 8px;
}

.breadcrumb-text {
  font-size: 14px;
  color: var(--text-primary);
}

.header-actions {
  display: flex;
  align-items: center;
}

.status-tag {
  margin-right: 20px;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 13px;
  background: linear-gradient(90deg, rgba(0,230,118,0.08), rgba(0,188,212,0.04));
  color: var(--text-primary);
  border: 1px solid rgba(0,230,118,0.08);
}

.action-icons {
  display: flex;
  align-items: center;
}

.action-icon {
  font-size: 18px;
  color: var(--text-secondary);
  margin-right: 18px;
  cursor: pointer;
  transition: color 0.12s, transform 0.12s;
}

.action-icon:hover {
  color: var(--primary-color);
  transform: translateY(-2px);
}

.user-dropdown {
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background-color 0.2s;
}

.user-dropdown:hover {
  background-color: rgba(255,255,255,0.02);
}

.user-avatar {
  margin-right: 8px;
}

.user-info {
  margin-right: 6px;
}

.user-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.user-role {
  font-size: 12px;
  margin-top: 4px;
  color: var(--text-secondary);
}

.dropdown-icon {
  font-size: 12px;
  color: var(--text-secondary);
}
</style>
