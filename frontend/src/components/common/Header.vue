<template>
  <header class="app-header">
    <div class="app-header__left">
      <div class="app-header__logo">
        <el-icon :size="22" color="#00d4ff"><Money /></el-icon>
        <span class="app-header__title">AI Agent 财务报销审核系统</span>
      </div>
    </div>
    <div class="app-header__right">
      <el-badge :value="pendingCount" :hidden="pendingCount === 0" class="header-badge">
        <el-button :icon="Bell" circle @click="handleNotifications" class="header-icon-btn" />
      </el-badge>
      <el-dropdown trigger="click" @command="handleCommand">
        <div class="user-info">
          <el-avatar :size="32" icon="UserFilled" class="user-avatar" />
          <span class="user-info__name">{{ userStore.fullName }}</span>
          <el-icon><ArrowDown /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile">
              <el-icon><User /></el-icon>
              个人信息
            </el-dropdown-item>
            <el-dropdown-item command="password">
              <el-icon><Lock /></el-icon>
              修改密码
            </el-dropdown-item>
            <el-dropdown-item divided command="logout">
              <el-icon><SwitchButton /></el-icon>
              退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
// Bell 以 `:icon="Bell"` 绑定表达式引用，<script setup> 中必须显式 import
import { Bell } from '@element-plus/icons-vue'

const userStore = useUserStore()
const pendingCount = ref(0)

function handleCommand(command: string) {
  switch (command) {
    case 'profile':
      ElMessage.info('个人信息功能开发中')
      break
    case 'password':
      ElMessage.info('修改密码功能开发中')
      break
    case 'logout':
      userStore.logout()
      break
  }
}

function handleNotifications() {
  ElMessage.info('通知功能开发中')
}
</script>

<style scoped lang="scss">
@import '@/styles/variables.scss';

.app-header {
  height: $header-height;
  background: rgba(13, 17, 23, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid $header-border;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 $spacing-lg;
  flex-shrink: 0;
  z-index: 100;

  &__left {
    display: flex;
    align-items: center;
  }

  &__logo {
    display: flex;
    align-items: center;
    gap: $spacing-sm;

    .el-icon {
      font-size: 22px;
    }
  }

  &__title {
    font-size: $font-size-lg;
    font-weight: 600;
    color: $text-primary;
    white-space: nowrap;
  }

  &__right {
    display: flex;
    align-items: center;
    gap: $spacing-md;
  }
}

.header-badge {
  cursor: pointer;
}

.header-icon-btn {
  background: rgba(255, 255, 255, 0.05) !important;
  border: 1px solid rgba(0, 212, 255, 0.2) !important;
  color: #b0b8d0 !important;
  transition: all 0.3s ease !important;

  &:hover {
    background: rgba(0, 212, 255, 0.1) !important;
    color: #00d4ff !important;
    box-shadow: 0 0 15px rgba(0, 212, 255, 0.15) !important;
  }
}

.user-info {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  cursor: pointer;
  padding: $spacing-xs $spacing-sm;
  border-radius: $border-radius-sm;
  transition: all 0.3s ease;

  &:hover {
    background: rgba(0, 212, 255, 0.08);
  }

  &__name {
    font-size: $font-size-base;
    color: $text-primary;
    max-width: 120px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.user-avatar {
  border: 1px solid rgba(0, 212, 255, 0.3);
  box-shadow: 0 0 10px rgba(0, 212, 255, 0.1);
}
</style>
