<template>
  <div class="layout-container">
    <Sidebar />
    <div class="main-container">
      <!-- Top Progress Bar -->
      <div class="route-progress" :class="{ active: isRouteChanging }"></div>
      
      <Header />
      <main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="page-transition" mode="out-in">
            <component :is="Component" :key="$route.path" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import Header from '@/components/common/Header.vue'
import Sidebar from '@/components/common/Sidebar.vue'

const route = useRoute()
const isRouteChanging = ref(false)

watch(
  () => route.path,
  () => {
    isRouteChanging.value = true
    setTimeout(() => {
      isRouteChanging.value = false
    }, 600)
  }
)
</script>

<style scoped>
.route-progress {
  position: fixed;
  top: 0;
  left: 0;
  height: 2px;
  background: linear-gradient(90deg, #00d4ff, #7c3aed, #00d4ff);
  background-size: 200% 100%;
  z-index: 9999;
  opacity: 0;
  transition: opacity 0.2s ease;
  animation: progressSlide 0.6s ease;

  &.active {
    opacity: 1;
    width: 100%;
  }
}

@keyframes progressSlide {
  0% { width: 0; left: 0; }
  50% { width: 60%; left: 20%; }
  100% { width: 100%; left: 0; }
}
</style>
