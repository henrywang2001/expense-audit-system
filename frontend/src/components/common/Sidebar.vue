<template>
  <aside class="app-sidebar" :class="{ collapsed: isCollapsed }">
    <!-- Brand -->
    <div class="sidebar-brand">
      <div class="brand-icon">
        <el-icon :size="28"><Money /></el-icon>
      </div>
      <div class="brand-text" v-show="!isCollapsed">
        <span class="brand-title">财务报销审核</span>
        <span class="brand-subtitle">AI Agent</span>
      </div>
    </div>

    <!-- Decorative line -->
    <div class="sidebar-divider"></div>

    <!-- Menu -->
    <div class="app-sidebar__menu">
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapsed"
        :collapse-transition="false"
        router
      >
        <template v-for="item in menuItems" :key="item.path">
          <el-menu-item :index="item.path">
            <el-icon>
              <component :is="item.icon" />
            </el-icon>
            <template #title>{{ item.title }}</template>
          </el-menu-item>
        </template>
      </el-menu>
    </div>

    <!-- Bottom Status -->
    <div class="sidebar-footer" v-show="!isCollapsed">
      <div class="sidebar-footer__status">
        <span class="status-dot"></span>
        <span class="status-text">系统运行中</span>
      </div>
      <div class="sidebar-footer__version">v1.0.0</div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const userStore = useUserStore()

const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/expense/detail')) return '/expense/list'
  return path
})

const isCollapsed = computed(() => false)

const menuItems = computed(() => userStore.menuItems)
</script>

<style scoped lang="scss">
@import '@/styles/variables.scss';

.app-sidebar {
  width: $sidebar-width;
  background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
  overflow-y: auto;
  overflow-x: hidden;
  transition: width 0.3s;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
    position: relative;

  &::-webkit-scrollbar {
    width: 4px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(0, 212, 255, 0.3);
    border-radius: 2px;

    &:hover {
      background: rgba(0, 212, 255, 0.5);
    }
  }

  &::before {
    content: '';
    position: absolute;
    right: 0;
    top: 0;
    width: 1px;
    height: 100%;
    background: linear-gradient(to bottom, transparent, rgba(0, 212, 255, 0.3), transparent);
  }

  &.collapsed {
    width: $sidebar-collapsed-width;
  }
}

// Brand section
.sidebar-brand {
  display: flex;
  align-items: center;
  padding: 24px 20px 20px;
  gap: 12px;
}

.brand-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: rgba(0, 212, 255, 0.12);
  border: 1px solid rgba(0, 212, 255, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #00d4ff;
  box-shadow: 0 0 20px rgba(0, 212, 255, 0.1);
  flex-shrink: 0;
}

.brand-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.brand-title {
  font-size: 14px;
  font-weight: 600;
  color: #f0f4fa;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.brand-subtitle {
  font-size: 11px;
  color: #b0b8d0;
  letter-spacing: 1px;
  text-transform: uppercase;
}

// Divider
.sidebar-divider {
  height: 1px;
  margin: 0 16px 8px;
  background: linear-gradient(to right, transparent, rgba(0, 212, 255, 0.2), transparent);
}

// Menu
.app-sidebar__menu {
  flex: 1;
  padding: 0 8px;
}

:deep(.el-menu-item) {
  border-radius: 8px;
  margin: 2px 0;
  height: 44px;
  line-height: 44px;
  transition: all 0.3s ease;
    position: relative;

  &::-webkit-scrollbar {
    width: 4px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(0, 212, 255, 0.3);
    border-radius: 2px;

    &:hover {
      background: rgba(0, 212, 255, 0.5);
    }
  }
  color: #b0b8d0 !important;

  .el-icon {
    font-size: 18px;
    transition: all 0.3s ease;
  }

  &:hover {
    background: rgba(0, 212, 255, 0.08) !important;
    color: #c8d8f0 !important;

    .el-icon {
      filter: drop-shadow(0 0 6px rgba(0, 212, 255, 0.4));
    }
  }

  &.is-active {
    background: rgba(0, 212, 255, 0.12) !important;
    color: #00d4ff !important;

    &::before {
      content: '';
      position: absolute;
      left: 0;
      top: 50%;
      transform: translateY(-50%);
      width: 3px;
      height: 20px;
      background: #00d4ff;
      border-radius: 0 3px 3px 0;
      box-shadow: 0 0 10px rgba(0, 212, 255, 0.5);
    }

    .el-icon {
      filter: drop-shadow(0 0 6px rgba(0, 212, 255, 0.4));
    }
  }
}

// Footer
.sidebar-footer {
  padding: 16px 20px;
  border-top: 1px solid rgba(0, 212, 255, 0.1);

  &__status {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
  }
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.5);
  animation: statusPulse 2s ease-in-out infinite;
}

@keyframes statusPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-text {
  font-size: 12px;
  color: #b0b8d0;
}

.sidebar-footer__version {
  font-size: 11px;
  color: #4a5568;
  padding-left: 16px;
}
</style>
