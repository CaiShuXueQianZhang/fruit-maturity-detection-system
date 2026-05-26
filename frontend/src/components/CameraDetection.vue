<template>
  <div class="camera-detection">
    <div class="camera-container">
      <!-- 视频元素 -->
      <video ref="videoRef" autoplay playsinline class="video-preview"></video>
      <!-- 覆盖层 canvas，用于绘制检测框 -->
      <canvas ref="canvasRef" class="overlay-canvas"></canvas>
      <!-- 隐藏 canvas，用于截图发送 -->
      <canvas ref="captureCanvasRef" style="display:none"></canvas>
    </div>

    <!-- 控制栏 -->
    <div class="camera-controls">
      <el-button type="primary" @click="startCamera" :disabled="isRunning" :loading="isStarting">
        <el-icon><VideoCamera /></el-icon> 开启摄像头
      </el-button>
      <el-button type="danger" @click="stopCamera" :disabled="!isRunning">
        <el-icon><VideoCameraFilled /></el-icon> 关闭摄像头
      </el-button>
      <el-button @click="togglePause" :disabled="!isRunning">
        <el-icon><VideoPause /></el-icon> {{ isPaused ? '恢复' : '暂停' }}
      </el-button>
      <el-slider v-model="inferenceInterval" :min="1" :max="10" style="width: 200px; margin-left: 16px" />
      <span class="stats">
        帧率: {{ fps.toFixed(1) }} fps | 目标数: {{ totalObjects }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, onUnmounted } from 'vue'


import { ElMessage } from 'element-plus'
import { VideoCamera, VideoCameraFilled, VideoPause } from '@element-plus/icons-vue'
import { detectFrame } from '../api/detection'

const emit = defineEmits(['update:running']);
const videoRef = ref(null)
const canvasRef = ref(null)
const captureCanvasRef = ref(null)

let videoStream = null
let animationFrameId = null
let detectionFrameId = null

const isRunning = ref(false)
const isPaused = ref(false)
const isStarting = ref(false)
const fps = ref(0)
const totalObjects = ref(0)
const inferenceInterval = ref(2)  // 每2帧检测一次
const currentBoxes = ref([])

let lastDetectionTime = 0
let frameCount = 0
let lastFpsTime = 0

// 颜色映射（根据类别）
const getBoxColor = (className) => {
  const colors = {
    Raw_Banana: '#FFA500',
    Raw_Mango: '#FFD700',
    Ripe_Banana: '#FFD700',
    Ripe_Mango: '#32CD32'
  }
  return colors[className] || '#00BFFF'
}

// 启动摄像头
const startCamera = async () => {
  if (isRunning.value) return
  isStarting.value = true
  try {
    videoStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 30 } },
      audio: false
    })
    if (videoRef.value) {
      videoRef.value.srcObject = videoStream
      await new Promise(resolve => { videoRef.value.onloadedmetadata = resolve })
      // 初始化 canvas 尺寸
      const video = videoRef.value
      const canvas = canvasRef.value
      const captureCanvas = captureCanvasRef.value
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      captureCanvas.width = video.videoWidth
      captureCanvas.height = video.videoHeight
      // 启动循环
      isRunning.value = true
      emit('update:running', true);
  emit('update:running', true)
      isPaused.value = false
      lastDetectionTime = performance.now()
      lastFpsTime = performance.now()
      frameCount = 0
      startDrawingLoop()
      startDetectionStream()
    }
  } catch (error) {
    handleCameraError(error)
  } finally {
    isStarting.value = false
  }
}

// 停止摄像头
const stopCamera = () => {
  if (videoStream) {
    videoStream.getTracks().forEach(track => track.stop())
    videoStream = null
  }
  if (videoRef.value) videoRef.value.srcObject = null
  if (animationFrameId) cancelAnimationFrame(animationFrameId)
  if (detectionFrameId) cancelAnimationFrame(detectionFrameId)
  isRunning.value = false
  emit('update:running', false);
  emit('update:running', false)
  isPaused.value = false
  currentBoxes.value = []
  fps.value = 0
  totalObjects.value = 0
  // 清空 canvas
  const ctx = canvasRef.value?.getContext('2d')
  if (ctx) ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
}

// 绘制循环（绘制检测框）
const startDrawingLoop = () => {
  const draw = () => {
    if (!isRunning.value) return
    if (canvasRef.value && videoRef.value) {
      const ctx = canvasRef.value.getContext('2d')
      const video = videoRef.value
      ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
      // 绘制检测框
      const scaleX = canvasRef.value.width / video.videoWidth
      const scaleY = canvasRef.value.height / video.videoHeight
      for (const box of currentBoxes.value) {
        const x1 = box.x1 * scaleX
        const y1 = box.y1 * scaleY
        const x2 = box.x2 * scaleX
        const y2 = box.y2 * scaleY
        const w = x2 - x1
        const h = y2 - y1
        ctx.strokeStyle = getBoxColor(box.class_name)
        ctx.lineWidth = 2
        ctx.strokeRect(x1, y1, w, h)
        ctx.fillStyle = getBoxColor(box.class_name)
        ctx.globalAlpha = 0.1
        ctx.fillRect(x1, y1, w, h)
        ctx.globalAlpha = 1
        const label = `${box.chinese_name} ${(box.confidence * 100).toFixed(0)}%`
        ctx.font = '12px Arial'
        ctx.fillStyle = getBoxColor(box.class_name)
        const labelWidth = ctx.measureText(label).width + 8
        if (y1 >= 16) {
          ctx.fillRect(x1, y1 - 16, labelWidth, 16)
          ctx.fillStyle = '#ffffff'
          ctx.fillText(label, x1 + 4, y1 - 4)
        } else {
          ctx.fillRect(x1, y1 + h, labelWidth, 16)
          ctx.fillStyle = '#ffffff'
          ctx.fillText(label, x1 + 4, y1 + h + 12)
        }
      }
    }
    animationFrameId = requestAnimationFrame(draw)
  }
  draw()
}

// 检测流（发送帧）
const startDetectionStream = () => {
  const sendFrame = async () => {
    if (!isRunning.value) return
    const now = performance.now()
    // 帧率统计
    frameCount++
    if (now - lastFpsTime >= 1000) {
      fps.value = frameCount / ((now - lastFpsTime) / 1000)
      frameCount = 0
      lastFpsTime = now
    }
    // 检测间隔
    const intervalMs = inferenceInterval.value * 33  // 约30fps，2帧约66ms
    if (!isPaused.value && (now - lastDetectionTime) >= intervalMs) {
      if (videoRef.value && captureCanvasRef.value) {
        const captureCanvas = captureCanvasRef.value
        const ctx = captureCanvas.getContext('2d')
        ctx.drawImage(videoRef.value, 0, 0, captureCanvas.width, captureCanvas.height)
        const imageData = captureCanvas.toDataURL('image/jpeg', 0.7)
        try {
          const response = await detectFrame({ image: imageData })
          if (response.success) {
            currentBoxes.value = response.data.boxes || []
            totalObjects.value = response.data.total_objects || 0
            lastDetectionTime = now
          } else {
            console.warn('检测失败:', response.message)
          }
        } catch (err) {
          console.error('检测请求失败:', err)
        }
      }
    }
    detectionFrameId = requestAnimationFrame(sendFrame)
  }
  sendFrame()
}

const togglePause = () => {
  isPaused.value = !isPaused.value
  ElMessage.info(isPaused.value ? '检测已暂停' : '检测已恢复')
}

const handleCameraError = (error) => {
  console.error('摄像头错误:', error)
  switch (error.name) {
    case 'NotAllowedError': ElMessage.error('摄像头权限被拒绝'); break
    case 'NotFoundError': ElMessage.error('未检测到摄像头设备'); break
    case 'NotReadableError': ElMessage.error('摄像头被其他应用占用'); break
    default: ElMessage.error('无法访问摄像头')
  }
  stopCamera()
}

onUnmounted(() => {
  stopCamera()
})
</script>

<style scoped>
.camera-detection {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.camera-container {
  position: relative;
  width: 100%;
  background: #000;
  border-radius: 12px;
  overflow: hidden;
}
.video-preview, .overlay-canvas {
  width: 100%;
  height: auto;
  display: block;
}
.overlay-canvas {
  position: absolute;
  top: 0;
  left: 0;
}
.camera-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.stats {
  font-size: 14px;
  color: #666;
  margin-left: auto;
}
</style>
