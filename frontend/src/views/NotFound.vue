<template>
  <div class="not-found-page">
    <div class="not-found-page__code">404</div>
    <div class="not-found-page__text">抱歉，您访问的页面不存在</div>
    <el-button type="primary" size="large" :icon="HomeFilled" @click="$router.push('/dashboard')">
      返回首页
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { HomeFilled } from '@element-plus/icons-vue'
</script>
