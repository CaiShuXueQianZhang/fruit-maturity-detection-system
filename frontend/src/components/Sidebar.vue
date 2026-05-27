<template>
  <div class="sidebar-container">
    <div class="logo-section">
      <div class="logo-icon">
        <Monitor style="color: white; font-size: 20px" />
      </div>
      <div class="logo-text">
        <div class="logo-title">果园水果检测系统</div>
        <div class="logo-subtitle">多场景果园影像·精准检测</div>
      </div>
    </div>

    <div class="nav-menu">
      <div
        v-for="item in menuList"
        :key="item.path"
        class="nav-item"
        :class="{ active: currentPath === item.path }"
        @click="handleMenuClick(item)"
      >
        <el-icon :size="18" class="nav-icon"><component :is="item.icon" /></el-icon>
        <span class="nav-text">{{ item.name }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useRouter, useRoute } from "vue-router";
import {
  Monitor,
  Picture,
  Clock,
  ChatDotRound,
  DataLine,
  User,
} from "@element-plus/icons-vue";

const router = useRouter();
const route = useRoute();

const menuList = [
  {
    name: "智能检测",
    icon: Picture,
    path: "/detection",
  },
  {
    name: "历史记录",
    icon: Clock,
    path: "/history",
  },
  {
    name: "人工咨询",
    icon: ChatDotRound,
    path: "/consult",
  },
  {
    name: "AI 问答",
    icon: ChatDotRound,
    path: "/qa",
  },
  {
    name: "水果库",
    icon: DataLine,
    path: "/targets",
  },
  {
    name: "个人中心",
    icon: User,
    path: "/profile",
  },
  
];

const currentPath = computed(() => route.path);

const handleMenuClick = (item) => {
  router.push(item.path);
};
</script>

<style scoped>
.sidebar-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.logo-section {
  height: 84px;
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.03);
}

.logo-icon {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--primary-color), var(--accent));
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
  flex-shrink: 0;
}

.logo-text {
  overflow: hidden;
}

.logo-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.1;
}

.logo-subtitle {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 2px;
  line-height: 1.1;
}

.nav-menu {
  flex: 1;
  padding: 14px 12px;
  overflow: auto;
}


.nav-item {
  display: flex;
  align-items: center;
  flex-direction: row;
  padding: 12px 12px;
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: background 0.12s, transform 0.12s;
  text-align: left;
  border-left: 3px solid transparent;
}

.nav-item:hover {
  background: rgba(0,230,118,0.04);
  transform: translateY(-2px);
}

.nav-item.active {
  background: linear-gradient(90deg, rgba(0,230,118,0.06), rgba(0,188,212,0.02));
  border-left: 3px solid var(--primary-color);
  color: var(--primary-color);
  font-weight: 600;
}

.nav-item.active .nav-icon {
  color: var(--primary-color);
}

.nav-icon {
  font-size: 18px;
  margin-right: 12px;
  color: var(--text-secondary);
  flex-shrink: 0;
}

.nav-text {
  font-size: 14px;
  line-height: 1.4;
}
</style>
