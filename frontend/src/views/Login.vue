<template>
  <div class="login-container" ref="loginContainer" @mousemove="handleMouseMove">
    <!-- Canvas Particle Background -->
    <canvas ref="particleCanvas" class="particle-canvas"></canvas>
    
    <!-- Tech Corner Decorations -->
    <div class="corner-decoration corner-tl"></div>
    <div class="corner-decoration corner-tr"></div>
    <div class="corner-decoration corner-bl"></div>
    <div class="corner-decoration corner-br"></div>
    
    <!-- Floating Data Lines -->
    <div class="data-lines">
      <div class="data-line" v-for="n in 5" :key="n" :style="{ animationDelay: n * 0.7 + 's' }"></div>
    </div>
    
    <!-- Login Card -->
    <div class="login-card" :style="cardTransform">
      <div class="login-card__header">
        <div class="login-icon-wrapper">
          <el-icon :size="52" color="#00d4ff"><Money /></el-icon>
        </div>
        <h1>AI Agent 财务报销审核系统</h1>
        <p>智能报销，高效审批，精准管理</p>
      </div>
      <div class="login-card__body">
        <el-form
          ref="formRef"
          :model="formData"
          :rules="rules"
          label-position="top"
          size="large"
        >
          <el-form-item label="用户名" prop="username">
            <el-input
              v-model="formData.username"
              placeholder="请输入用户名"
              :prefix-icon="User"
              @keyup.enter="handleLogin"
            />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input
              v-model="formData.password"
              type="password"
              placeholder="请输入密码"
              :prefix-icon="Lock"
              show-password
              @keyup.enter="handleLogin"
            />
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              :loading="loading"
              size="large"
              style="width: 100%"
              @click="handleLogin"
            >
              {{ loading ? '登录中...' : '登 录' }}
            </el-button>
          </el-form-item>
        </el-form>
        <div class="login-footer">
          <span>还没有账号？</span>
          <el-button link type="primary" @click="handleRegister">
            立即注册
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useUserStore } from '@/stores/user'
import type { LoginForm } from '@/types'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref<FormInstance>()
const loading = ref(false)
const loginContainer = ref<HTMLElement | null>(null)
const particleCanvas = ref<HTMLCanvasElement | null>(null)

// Mouse parallax
const mouseX = ref(0)
const mouseY = ref(0)

const cardTransform = computed(() => ({
  transform: `perspective(1000px) rotateX(${mouseY.value * 0.03}deg) rotateY(${mouseX.value * -0.03}deg)`
}))

function handleMouseMove(e: MouseEvent) {
  if (!loginContainer.value) return
  const rect = loginContainer.value.getBoundingClientRect()
  mouseX.value = (e.clientX - rect.left - rect.width / 2) / (rect.width / 2)
  mouseY.value = (e.clientY - rect.top - rect.height / 2) / (rect.height / 2)
}

// Canvas particles
let animationId = 0

function initParticles() {
  const canvas = particleCanvas.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  canvas.width = window.innerWidth
  canvas.height = window.innerHeight

  const particles: Array<{ x: number; y: number; vx: number; vy: number; size: number; alpha: number }> = []
  const particleCount = 80

  for (let i = 0; i < particleCount; i++) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.5,
      vy: (Math.random() - 0.5) * 0.5,
      size: Math.random() * 2 + 0.5,
      alpha: Math.random() * 0.5 + 0.1
    })
  }

  function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    particles.forEach((p, i) => {
      p.x += p.vx
      p.y += p.vy

      if (p.x < 0) p.x = canvas.width
      if (p.x > canvas.width) p.x = 0
      if (p.y < 0) p.y = canvas.height
      if (p.y > canvas.height) p.y = 0

      ctx.beginPath()
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(0, 212, 255, ${p.alpha})`
      ctx.fill()

      // Draw connections
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[j].x - p.x
        const dy = particles[j].y - p.y
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < 150) {
          ctx.beginPath()
          ctx.moveTo(p.x, p.y)
          ctx.lineTo(particles[j].x, particles[j].y)
          ctx.strokeStyle = `rgba(0, 212, 255, ${0.1 * (1 - dist / 150)})`
          ctx.lineWidth = 0.5
          ctx.stroke()
        }
      }
    })

    animationId = requestAnimationFrame(animate)
  }

  animate()
}

function handleResize() {
  const canvas = particleCanvas.value
  if (canvas) {
    canvas.width = window.innerWidth
    canvas.height = window.innerHeight
  }
}

onMounted(() => {
  initParticles()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  cancelAnimationFrame(animationId)
  window.removeEventListener('resize', handleResize)
})

const formData = reactive<LoginForm>({
  username: '',
  password: ''
})

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 50, message: '用户名长度2-50个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 50, message: '密码长度6-50个字符', trigger: 'blur' }
  ]
}

async function handleLogin() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await userStore.login({
      username: formData.username,
      password: formData.password
    })
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch (error: any) {
    console.error('Login error:', error)
  } finally {
    loading.value = false
  }
}

function handleRegister() {
  ElMessage.info('注册功能请联系管理员')
}
</script>

<style scoped lang="scss">
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0a0e27;
  background-image: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0f1729 100%);
  position: relative;
  overflow: hidden;
}

.particle-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

// Corner decorations
.corner-decoration {
  position: absolute;
  width: 120px;
  height: 120px;
  border: 1px solid rgba(0, 212, 255, 0.15);
  pointer-events: none;

  &.corner-tl {
    top: 20px;
    left: 20px;
    border-right: none;
    border-bottom: none;
  }
  &.corner-tr {
    top: 20px;
    right: 20px;
    border-left: none;
    border-bottom: none;
  }
  &.corner-bl {
    bottom: 20px;
    left: 20px;
    border-right: none;
    border-top: none;
  }
  &.corner-br {
    bottom: 20px;
    right: 20px;
    border-left: none;
    border-top: none;
  }
}

// Floating data lines
.data-lines {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  overflow: hidden;
}

.data-line {
  position: absolute;
  width: 1px;
  height: 100%;
  background: linear-gradient(to bottom, transparent, rgba(0, 212, 255, 0.08), transparent);
  animation: dataLineFloat 8s ease-in-out infinite;

  &:nth-child(1) { left: 10%; }
  &:nth-child(2) { left: 25%; }
  &:nth-child(3) { left: 50%; }
  &:nth-child(4) { left: 75%; }
  &:nth-child(5) { left: 90%; }
}

@keyframes dataLineFloat {
  0%, 100% { transform: translateY(-100%); opacity: 0; }
  50% { transform: translateY(100%); opacity: 1; }
}

// Login Card
.login-card {
  width: 440px;
  max-width: calc(100vw - 32px);
  border-radius: 16px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(0, 212, 255, 0.2);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5), 0 0 60px rgba(0, 212, 255, 0.05);
  position: relative;
  z-index: 1;
  transition: transform 0.1s ease;

  &::before {
    content: '';
    position: absolute;
    top: -2px;
    left: -2px;
    right: -2px;
    bottom: -2px;
    border-radius: 17px;
    background: linear-gradient(45deg, rgba(0, 212, 255, 0.3), transparent 40%, transparent 60%, rgba(123, 58, 237, 0.3));
    z-index: -1;
    animation: borderRotate 4s linear infinite;
  }

  &__header {
    text-align: center;
    padding: 40px 32px 20px;

    h1 {
      font-size: 24px;
      font-weight: 700;
      color: #f0f4fa;
      margin-bottom: 8px;
      text-shadow: 0 0 30px rgba(0, 212, 255, 0.3), 0 0 60px rgba(0, 212, 255, 0.1);
      animation: textPulse 3s ease-in-out infinite;
    }

    p {
      color: #b0b8d0;
      font-size: 14px;
    }
  }

  &__body {
    padding: 16px 32px 32px;
  }
}

.login-icon-wrapper {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: rgba(0, 212, 255, 0.1);
  border: 2px solid rgba(0, 212, 255, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
  box-shadow: 0 0 30px rgba(0, 212, 255, 0.15), inset 0 0 30px rgba(0, 212, 255, 0.05);
  animation: iconPulse 3s ease-in-out infinite;
}

@keyframes iconPulse {
  0%, 100% { box-shadow: 0 0 30px rgba(0, 212, 255, 0.15); }
  50% { box-shadow: 0 0 50px rgba(0, 212, 255, 0.25); }
}

@keyframes textPulse {
  0%, 100% { text-shadow: 0 0 30px rgba(0, 212, 255, 0.3); }
  50% { text-shadow: 0 0 50px rgba(0, 212, 255, 0.4); }
}

@keyframes borderRotate {
  0% { opacity: 0.5; }
  50% { opacity: 1; }
  100% { opacity: 0.5; }
}

.login-footer {
  text-align: center;
  color: #b0b8d0;
  font-size: 14px;
  padding-top: 8px;
}
</style>
