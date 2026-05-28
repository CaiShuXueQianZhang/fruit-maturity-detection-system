<template>
  <div class="detection-page">
    <div class="container">
      <!-- 华丽页眉 -->
      <header class="hero">
        <div class="hero-left">
          <div class="breadcrumb">
            <span>工作台</span>
            <span class="separator">›</span>
            <span class="active">智能检测</span>
          </div>
          <h1 class="page-title">上传水果图像，立即识别成熟度</h1>
          <p class="page-subtitle">支持香蕉 / 芒果等多种水果检测 · 高精度检测模型</p>
        </div>
        <div class="hero-right">
          <div class="model-selector">
            <el-select v-model="selectedModel" size="large" style="width: 220px">
              <el-option label="mab-yolo11m" value="mab-yolo11m" />
            </el-select>
          </div>
        </div>
      </header>

      <!-- 功能选项卡 -->
      <div class="function-tabs">
        <div
          v-for="tab in functionTabs"
          :key="tab.key"
          class="function-tab"
          :class="{ active: activeTab === tab.key, 'drag-over': dragOverTab === tab.key }"
          :data-key="tab.key"
          @click="handleTabClick(tab.key)"
          @dragover.prevent
          @dragenter.prevent="handleDragEnter($event, tab.key)"
          @dragleave.prevent="handleDragLeave($event, tab.key)"
          @drop.prevent="handleDrop($event, tab.key)"
        >
          <input
            v-if="tab.key !== 'ciname'"
            type="file"
            :accept="tab.accept"
            :multiple="tab.multiple"
            class="file-input"
            @change="handleFileChange($event, tab.key)"
            @click.stop
            ref="fileInputs"
          />

          <div class="tab-inner">
            <el-icon :size="22" class="tab-icon">
              <component :is="tab.icon"></component>
            </el-icon>
            <div class="tab-info">
              <div class="tab-title">{{ tab.name }}</div>
              <div class="tab-desc">{{ tab.desc }}</div>
            </div>
          </div>

          <div class="tab-bottom-indicator" v-if="activeTab === tab.key"></div>
        </div>
      </div>

      <!-- 主内容区域 -->
      <div class="main-content">
      <!-- 左侧检测结果区域 -->
      <div class="left-panel">
        <div class="panel-header">
          <span class="panel-title">检测预览</span>
          <el-tag
            :type="hasImage && detectionResult ? 'success' : 'info'"
            effect="light"
            class="result-tag"
          >
            <el-icon class="el-icon--left" v-if="hasImage && detectionResult"><Check /></el-icon>
            <el-icon class="el-icon--left" v-else><Upload /></el-icon>
            {{ hasImage && detectionResult ? "检测完成" : "等待上传" }}
          </el-tag>
        </div>

        <!-- 工具栏 -->
        <div class="toolbar">
          <el-button
            :class="{ active: compareMode === 'side' }"
            size="small"
            @click="compareMode = 'side'"
          >
            <el-icon><Minus /></el-icon>
            并排对比
          </el-button>
          <el-button
            :class="{ active: compareMode === 'grid' }"
            size="small"
            @click="compareMode = 'grid'"
          >
            <el-icon><Grid /></el-icon>
            栅格对比
          </el-button>
        </div>

        <!-- 图片/视频/摄像头对比区域 -->
        <div class="image-compare">
          <div class="image-card">
            <!-- 原始：支持单图、批量选中项、视频与摄像头 -->
            <template v-if="activeTab === 'video'">
              <template v-if="originalVideo">
                <video :src="originalVideo" controls class="compare-image"></video>
              </template>
              <template v-else>
                <div class="image-placeholder">
                  <el-icon class="placeholder-icon"><Upload /></el-icon>
                  <p class="placeholder-text">请上传视频</p>
                </div>
              </template>
            </template>

            <template v-else-if="activeTab === 'ciname'">
              <video ref="cameraVideo" autoplay muted playsinline class="compare-image camera-video"></video>
            </template>

            <template v-else>
              <template v-if="activeTab === 'batch'">
                <div class="batch-list-compare">
                  <div
                    v-for="(item, idx) in batchResults"
                    :key="idx"
                    class="batch-row"
                    :class="{ selected: selectedBatchIndex === idx }"
                    @click="selectBatch(idx)"
                  >
                    <img :src="item.preview || item.image_url" class="batch-compare-img" />
                    <div class="row-overlay">{{ item.filename || ('检测 ' + (idx+1)) }}</div>
                  </div>
                </div>
              </template>
              <template v-else>
                <template v-if="hasImage && originalImage">
                  <img :src="originalImage" alt="原始图片" class="compare-image" />
                </template>
                <template v-else>
                  <div class="image-placeholder">
                    <el-icon class="placeholder-icon"><Upload /></el-icon>
                    <p class="placeholder-text">请上传图片</p>
                    <p class="placeholder-desc">支持 jpg、png 格式</p>
                  </div>
                </template>
              </template>
            </template>

            <div class="image-label">原始</div>
          </div>

          <div class="image-card">
            <!-- 结果：图片、视频或摄像头实时框选预览 -->
            <template v-if="activeTab === 'video'">
              <template v-if="resultVideo">
                <video :src="resultVideo" controls class="compare-image"></video>
              </template>
              <template v-else>
                <div class="image-placeholder">
                  <el-icon class="placeholder-icon"><View /></el-icon>
                  <p class="placeholder-text">检测结果将在此展示</p>
                </div>
              </template>
            </template>

            <template v-else>
              <template v-if="activeTab === 'ciname'">
                <div class="camera-result-wrap">
                  <video ref="cameraResultVideo" autoplay muted playsinline class="compare-image camera-video"></video>
                  <div class="camera-box-layer" v-if="cameraBoxes.length">
                    <div
                      v-for="(box, index) in cameraBoxes"
                      :key="index"
                      class="camera-box"
                      :style="getCameraBoxStyle(box)"
                    >
                      <span class="camera-box-label">{{ formatCameraBoxLabel(box) }}</span>
                    </div>
                  </div>
                  <div class="camera-status">{{ cameraStatusText }}</div>
                </div>
              </template>
              <template v-else-if="activeTab === 'batch'">
                <div class="batch-list-compare">
                  <div
                    v-for="(item, idx) in batchResults"
                    :key="idx"
                    class="batch-row"
                    :class="{ selected: selectedBatchIndex === idx }"
                    @click="selectBatch(idx)"
                  >
                    <img :src="item.result_image_url" class="batch-compare-img" />
                    <div class="row-overlay">检测结果</div>
                  </div>
                </div>
              </template>
              <template v-else>
                <template v-if="hasImage && resultImage">
                  <div class="compare-image-wrap">
                    <img :src="resultImage" alt="检测结果" class="compare-image" />
                    <div class="boxes-overlay" v-if="topBoxes && topBoxes.length">
                      <div
                        v-for="(b, i) in topBoxes"
                        :key="i"
                        class="box-tag"
                        :style="{ borderLeftColor: getClassColor(b.class_name || b.class || b.className) }"
                      >
                        <div class="tag-name">{{ b.class_name || b.class || b.className }}</div>
                        <div class="tag-conf">{{ ((b.confidence||0)*100).toFixed(1) }}%</div>
                      </div>
                    </div>
                  </div>
                  <div class="detection-mark" v-if="detectionResult"></div>
                </template>
                <template v-else>
                  <div class="image-placeholder">
                    <el-icon class="placeholder-icon"><View /></el-icon>
                    <p class="placeholder-text">检测结果将在此展示</p>
                    <p class="placeholder-desc">上传图片后开始检测</p>
                  </div>
                </template>
              </template>
            </template>

            <div class="image-label">检测结果</div>
          </div>
        </div>
      </div>

      <!-- 右侧信息面板 -->
      <div class="right-panel">
        <!-- 仪表盘小卡 -->
        <div class="info-card stat-cards">
          <div class="stat-card">
            <div class="stat-title">检测总数</div>
            <div class="stat-value">{{ detectionTotalCount }}</div>
            <div class="stat-sub">总计识别目标数</div>
          </div>
          <div class="stat-card">
            <div class="stat-title">平均置信度</div>
            <div class="stat-value">{{ averageConfidence.toFixed(1) }}%</div>
            <div class="stat-sub">近次检测平均</div>
          </div>
          <div class="stat-card">
            <div class="stat-title">平均耗时</div>
            <div class="stat-value">{{ averageProcessingTime }}s</div>
            <div class="stat-sub">每图处理耗时</div>
          </div>
        </div>

        <!-- 识别清单 -->
        <div class="result-card">
          <div class="card-header">
            <el-icon><List /></el-icon>
            <span class="card-title">识别清单</span>
          </div>
          <div v-if="!hasImage" class="empty-state">
            <el-icon class="empty-icon"><Upload /></el-icon>
            <p class="empty-text">请上传图片开始检测</p>
            <p class="empty-desc">上传果园影像以识别水果</p>
          </div>
          <div
            v-else-if="!detectionResult || detectionResult.total_objects === 0"
            class="empty-state"
          >
            <el-icon class="empty-icon"><CircleCheck /></el-icon>
            <p class="empty-text">未检测到水果</p>
            <p class="empty-desc">影像中未检测到水果</p>
          </div>
          <div v-else-if="activeTab === 'batch'">
            <div v-if="batchResults.length === 0" class="empty-state">
              <el-icon class="empty-icon"><Upload /></el-icon>
              <p class="empty-text">等待批量检测结果</p>
              <p class="empty-desc">请通过批量上传发起检测</p>
            </div>
            <div v-else class="batch-list">
              <div
                v-for="(item, idx) in batchResults"
                :key="idx"
                class="detection-item batch-item"
                :class="{ selected: selectedBatchIndex === idx }"
                @click="selectBatch(idx)"
              >
                <div class="thumbs">
                  <img :src="item.preview || item.image_url" class="thumb-img" alt="orig" />
                  <img :src="item.result_image_url" class="thumb-img" alt="result" />
                </div>
                <div style="display:flex;flex-direction:column">
                  <div style="font-weight:600">{{ item.filename || ('检测 ' + (idx+1)) }}</div>
                  <div style="font-size:12px;color:var(--text-secondary)">目标: {{ item.total_objects || 0 }}</div>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="detection-list">
            <div
              v-for="(box, index) in detectionResult.boxes"
              :key="index"
              class="detection-item list-row"
            >
              <div class="list-left">
                <div class="item-name">{{ box.class_name || box.class || box.className }}</div>
                <div class="progress-bar">
                  <div class="progress-fill" :style="{ width: ((box.confidence||0)*100) + '%', background: getClassColor(box.class_name || box.class) }"></div>
                </div>
              </div>
              <div class="list-right">{{ ((box.confidence||0)*100).toFixed(1) }}%</div>
            </div>
          </div>
        </div>

        <!-- AI诊断建议 -->
        <div class="result-card">
          <div class="card-header">
            <el-icon><ChatDotRound /></el-icon>
            <span class="card-title">AI 诊断建议</span>
          </div>
          <div class="diagnosis-content">
            <p v-if="!hasImage">上传图片后将自动生成诊断建议</p>
            <p v-else-if="!detectionResult">未检测到指定水果</p>
            <p v-else>
              检测到 {{ detectionResult.total_objects }} 个水果，耗时
              {{ detectionResult.detection_time }}s。 模型:
              {{ detectionResult.model_name }}
            </p>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="action-buttons">
          <el-button
            size="default"
            class="btn-secondary"
            @click="handleRedetect"
          >
            <el-icon><Refresh /></el-icon>
            重新检测
          </el-button>
          <el-button type="primary" size="default" class="btn-primary" @click="openReport">
            查看完整报告
          </el-button>
        </div>
      </div>
    </div>
  </div>
  
  <!-- 报告弹窗 -->
  <el-dialog v-model="reportDialogVisible" width="1100px" title="检测报告">
    <div v-if="activeTab === 'batch' && reportData && Array.isArray(reportData)">
      <div class="batch-report-grid">
        <div v-for="(r, i) in reportData" :key="i" class="report-pair">
          <div class="pair-images">
            <img :src="r.preview || r.image_url" class="report-thumb" />
            <img :src="r.result_image_url" class="report-thumb" />
          </div>
          <div class="pair-meta">
            <div class="meta-title" style="font-weight:700">{{ r.filename || ('检测 ' + (i+1)) }}</div>
            <div class="meta-row">目标: {{ r.total_objects || 0 }}</div>
            <div class="meta-row">耗时: {{ r.detection_time || '-' }}s</div>
          </div>
        </div>
      </div>
    </div>
    <div v-else>
      <div style="display:flex;gap:16px">
        <div style="flex:1">
          <template v-if="reportImageSrc()">
            <img :src="reportImageSrc()" style="width:100%;height:auto;border-radius:8px" />
          </template>
          <template v-else>
            <div style="height:300px;display:flex;align-items:center;justify-content:center;color:#999">无可显示的结果图像</div>
          </template>
        </div>
        <div style="width:320px">
          <h3>检测信息</h3>
          <div style="margin-bottom:8px">检测 ID: {{ (reportData && (reportData.detection_id || reportData.detectionId)) || '-' }}</div>
          <div style="margin-bottom:8px">模型: {{ (reportData && (reportData.model_name || reportData.modelName)) || '-' }}</div>
          <div style="margin-bottom:8px">耗时: {{ (reportData && (reportData.detection_time || reportData.detectionTime)) || 0 }}s</div>
          <h4>检测目标 ({{ (reportData && (reportData.total_objects || reportData.totalObjects)) || 0 }})</h4>
          <div v-if="reportData && reportData.boxes && reportData.boxes.length > 0">
            <div v-for="(b, i) in reportData.boxes" :key="i" style="margin-bottom:10px;padding-bottom:6px;border-bottom:1px dashed #eee">
              <div style="font-weight:600">{{ b.class_name || b.class || b.className }}</div>
              <div style="font-size:12px;color:#666">置信度: {{ ((b.confidence||b.confidence||0)*100).toFixed(1) }}%</div>
              <div style="font-size:12px;color:#666">坐标: {{ b.x1?.toFixed(0) || '-' }}, {{ b.y1?.toFixed(0) || '-' }} - {{ b.x2?.toFixed(0) || '-' }}, {{ b.y2?.toFixed(0) || '-' }}</div>
            </div>
          </div>
          <div v-else style="color:#666">未检测到目标</div>
        </div>
      </div>
    </div>
    <template #footer>
      <el-button @click="reportDialogVisible = false">关闭</el-button>
    </template>
  </el-dialog>
  </div>
</template>

<script setup>
import { ref, onBeforeUnmount, nextTick, computed } from "vue";
import { ElMessage, ElLoading } from "element-plus";
import {
  Picture,
  Plus,
  Folder,
  Monitor,
  Check,
  Grid,
  List,
  CircleCheck,
  ChatDotRound,
  Refresh,
  Minus,
  Upload,
  View,
} from "@element-plus/icons-vue";
import { detectSingleImage, detectBatchImages, detectVideo, detectFrame } from "../api/detection";

const selectedModel = ref("mab-yolo11m");
const activeTab = ref("single");
const compareMode = ref("side");
const originalImage = ref(null);
const resultImage = ref(null);
const detectionResult = ref(null);
const isDetecting = ref(false);
const hasImage = ref(false);

// 批量结果
const batchResults = ref([]);
const batchOriginalPreviews = ref([]);
const selectedBatchIndex = ref(0);
const dragOverTab = ref(null);

// 视频结果
const originalVideo = ref(null);
const resultVideo = ref(null);

// 摄像头相关
const cameraStream = ref(null);
const cameraVideo = ref(null);
const cameraResultVideo = ref(null);
let cameraTimer = null;
const cameraIntervalMs = 700;
const cameraRunning = ref(false);
const cameraDetecting = ref(false);
const cameraBoxes = ref([]);
const cameraFrameSize = ref({ width: 0, height: 0 });
const cameraCanvas = document.createElement("canvas");
// 报告弹窗状态
const reportDialogVisible = ref(false);
const reportData = ref(null);

const detectionTotalCount = computed(() => {
  if (activeTab.value === 'batch' && batchResults.value && batchResults.value.length) {
    return batchResults.value.reduce((sum, r) => sum + (r.total_objects || 0), 0);
  }
  return detectionResult.value ? (detectionResult.value.total_objects || 0) : 0;
});

const averageConfidence = computed(() => {
  let boxes = [];
  if (activeTab.value === 'batch' && batchResults.value && batchResults.value.length) {
    batchResults.value.forEach((r) => { if (r.boxes) boxes = boxes.concat(r.boxes); });
  } else if (detectionResult.value && detectionResult.value.boxes) {
    boxes = detectionResult.value.boxes;
  }
  if (!boxes || boxes.length === 0) return 0;
  const sum = boxes.reduce((s, b) => s + (b.confidence || 0), 0);
  return (sum / boxes.length) * 100;
});

const averageProcessingTime = computed(() => {
  if (activeTab.value === 'batch' && batchResults.value && batchResults.value.length) {
    const times = batchResults.value.map((r) => r.detection_time || 0).filter(Boolean);
    if (times.length === 0) return '-';
    return (times.reduce((a,b)=>a+b,0)/times.length).toFixed(2);
  }
  return detectionResult.value ? (detectionResult.value.detection_time || '-') : '-';
});

const topBoxes = computed(() => {
  return detectionResult.value && detectionResult.value.boxes ? (detectionResult.value.boxes.slice(0,6)) : [];
});

const cameraStatusText = computed(() => {
  if (!cameraRunning.value) return "摄像头未开启";
  if (cameraDetecting.value) return "正在检测当前画面";
  if (cameraBoxes.value.length > 0) return `识别到 ${cameraBoxes.value.length} 个目标`;
  return "实时预览中";
});

const colorMap = {
  mango: '#F59E0B',
  banana: '#FACC15',
  apple: '#EF4444',
  default: 'var(--primary-color)'
};

const getClassColor = (name) => {
  if (!name) return colorMap.default;
  const key = name.toString().toLowerCase();
  for (const k of Object.keys(colorMap)) {
    if (key.includes(k)) return colorMap[k];
  }
  return colorMap.default;
};

const clampPercent = (value) => Math.min(100, Math.max(0, value));

const getCameraBoxStyle = (box) => {
  const width = cameraFrameSize.value.width || cameraVideo.value?.videoWidth || 1;
  const height = cameraFrameSize.value.height || cameraVideo.value?.videoHeight || 1;
  const left = clampPercent((box.x1 / width) * 100);
  const top = clampPercent((box.y1 / height) * 100);
  const right = clampPercent((box.x2 / width) * 100);
  const bottom = clampPercent((box.y2 / height) * 100);
  return {
    left: `${left}%`,
    top: `${top}%`,
    width: `${Math.max(0, right - left)}%`,
    height: `${Math.max(0, bottom - top)}%`,
    borderColor: getClassColor(box.class_name || box.className || box.class),
  };
};

const formatCameraBoxLabel = (box) => {
  const name = box.chinese_name || box.class_name || box.className || box.class || "目标";
  const confidence = Number(box.confidence || 0) * 100;
  return `${name} ${confidence.toFixed(1)}%`;
};

const handleDragEnter = (e, tabKey) => {
  dragOverTab.value = tabKey;
};

const handleDragLeave = (e, tabKey) => {
  dragOverTab.value = null;
};

const handleDrop = (e, tabKey) => {
  dragOverTab.value = null;
  const files = e.dataTransfer && e.dataTransfer.files ? e.dataTransfer.files : null;
  if (!files || files.length === 0) return;
  if (tabKey === 'single') {
    performSingleDetection(files[0]);
  } else if (tabKey === 'batch') {
    performBatchDetection(Array.from(files));
  } else if (tabKey === 'video') {
    performVideoDetection(files[0]);
  }
};

const functionTabs = [
  {
    key: "single",
    name: "单图检测",
    desc: "快速识别一张图片",
    icon: Picture,
    accept: "image/*",
    multiple: false,
  },
  {
    key: "batch",
    name: "批量检测",
    desc: "一次处理多张图片",
    icon: Plus,
    accept: "image/*",
    multiple: true,
  },
  {
    key: "ciname",
    name: "摄像头",
    desc: "打开摄像头",
    icon: Folder,
    accept: "image/*",
    multiple: true,
  },
  {
    key: "video",
    name: "视频检测",
    desc: "上传视频自动分析",
    icon: Monitor,
    accept: "video/*",
    multiple: false,
  },
];

const fileInputs = ref([]);

const handleTabClick = (key) => {
  // 如果之前是摄像头模式且切换到其他模式，则停止摄像头
  if (activeTab.value === "ciname" && key !== "ciname") {
    stopCamera();
  }

  activeTab.value = key;
  // 摄像头直接打开流
  if (key === "ciname") {
    startCamera();
    return;
  }

  const input = document.querySelector(
    `.function-tab[data-key="${key}"] .file-input`,
  );
  if (input) {
    input.click();
  }
};

const handleFileChange = async (event, tabKey) => {
  event.stopPropagation();
  event.preventDefault();
  const files = event.target.files;
  if (files && files.length > 0) {
    if (tabKey === "single") {
      await performSingleDetection(files[0]);
    } else if (tabKey === "batch") {
      await performBatchDetection(Array.from(files));
    } else if (tabKey === "video") {
      await performVideoDetection(files[0]);
    }
  }
  setTimeout(() => {
    event.target.value = "";
  }, 0);
};

const performSingleDetection = async (file) => {
  const loading = ElLoading.service({
    lock: true,
    text: "正在检测中...",
    background: "rgba(0, 0, 0, 0.7)",
  });

  try {
    isDetecting.value = true;
    hasImage.value = true;

    const formData = new FormData();
    formData.append("file", file);
    formData.append("model_name", selectedModel.value);

    originalImage.value = URL.createObjectURL(file);

    const response = await detectSingleImage(formData);
    if (response.success && response.data) {
      detectionResult.value = response.data;
      resultImage.value = response.data.result_image_url;
      ElMessage.success("检测成功！");
    } else {
      ElMessage.error(response.message || "检测失败");
    }
  } catch (error) {
    console.error("检测错误:", error);
    ElMessage.error("检测失败，请稍后重试");
  } finally {
    isDetecting.value = false;
    loading.close();
  }
};

const performBatchDetection = async (files) => {
  const loading = ElLoading.service({ lock: true, text: "批量检测中...", background: "rgba(0,0,0,0.7)" });
  try {
    isDetecting.value = true;
    hasImage.value = true;
    // 先生成本地预览图，便于在上传与检测前查看
    batchOriginalPreviews.value = Array.from(files).map((f) => ({ url: URL.createObjectURL(f), name: f.name }));
    // 先在左侧预览第一个本地图片
    if (batchOriginalPreviews.value.length > 0) {
      originalImage.value = batchOriginalPreviews.value[0].url;
      detectionResult.value = null;
      resultImage.value = null;
    }

    const formData = new FormData();
    // 使用 files[] 字段名上传多个文件
    files.forEach((f) => {
      formData.append("files[]", f);
    });
    formData.append("model_name", selectedModel.value);
    console.debug("batch upload files count:", files.length);
    console.debug("formData entries count:", formData.getAll("files[]").length);

    const resp = await detectBatchImages(formData);
    if (resp && resp.success) {
      // 将后端结果与本地 preview 按顺序关联
      const results = resp.data || [];
      batchResults.value = results.map((r, i) => {
        return Object.assign({}, r, {
          preview: batchOriginalPreviews.value[i] ? batchOriginalPreviews.value[i].url : null,
          filename: r.filename || (batchOriginalPreviews.value[i] && batchOriginalPreviews.value[i].name) || `检测_${i+1}`,
        });
      });

      if (batchResults.value.length > 0) {
        selectedBatchIndex.value = 0;
        const first = batchResults.value[0];
        originalImage.value = first.preview || first.image_url;
        resultImage.value = first.result_image_url;
        detectionResult.value = first;
      }
      ElMessage.success("批量检测完成");
    } else {
      ElMessage.error(resp?.message || "批量检测失败");
    }
  } catch (err) {
    console.error(err);
    ElMessage.error("批量检测出错");
  } finally {
    isDetecting.value = false;
    loading.close();
  }
};

const selectBatch = (idx) => {
  selectedBatchIndex.value = idx;
  const item = batchResults.value[idx];
  if (item) {
    originalImage.value = item.preview || item.image_url;
    resultImage.value = item.result_image_url;
    detectionResult.value = item;
  }
};

const performVideoDetection = async (file) => {
  const loading = ElLoading.service({ lock: true, text: "视频检测中...", background: "rgba(0,0,0,0.7)" });
  try {
    isDetecting.value = true;
    hasImage.value = true;
    const formData = new FormData();
    formData.append("file", file);
    formData.append("model_name", selectedModel.value);

    // 本地预览原视频
    originalVideo.value = URL.createObjectURL(file);

    const resp = await detectVideo(formData);
    if (resp && resp.success && resp.data) {
      resultVideo.value = resp.data.video_url || resp.data.result_video_url || resp.data.result_image_url;
      detectionResult.value = resp.data;
      ElMessage.success("视频检测完成");
    } else {
      ElMessage.error(resp?.message || "视频检测失败");
    }
  } catch (err) {
    console.error(err);
    ElMessage.error("视频检测出错");
  } finally {
    isDetecting.value = false;
    loading.close();
  }
};

const reportImageSrc = () => {
  if (!reportData.value) return "";
  // 视频模式优先返回 resultVideo
  if (activeTab.value === "video" && resultVideo.value) return resultVideo.value;
  if (reportData.value.image) return reportData.value.image;
  // support single object or batch array
  if (Array.isArray(reportData.value)) {
    return "";
  }
  return reportData.value.result_image_url || reportData.value.image_url || "";
};

const openReport = () => {
  if (activeTab.value === 'batch' && batchResults.value && batchResults.value.length > 0) {
    reportData.value = batchResults.value.slice();
    reportDialogVisible.value = true;
    return;
  }

  if (!detectionResult.value) {
    ElMessage.info("暂无检测结果");
    return;
  }
  reportData.value = detectionResult.value;
  reportDialogVisible.value = true;
};

const startCamera = async () => {
  if (cameraRunning.value) return;
  try {
    if (!window.isSecureContext && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
      ElMessage.error("当前页面不是安全上下文（需要 HTTPS 或在 localhost 上），浏览器会拒绝摄像头权限");
      return;
    }

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      ElMessage.error("当前浏览器不支持摄像头访问，请使用 Chromium/Chrome/Firefox 的安全上下文 (localhost 或 https)");
      return;
    }

    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 640 },
        height: { ideal: 480 },
        frameRate: { ideal: 30, max: 30 },
      },
      audio: false,
    });
    cameraStream.value = stream;
    await nextTick();
    if (cameraVideo.value) {
      cameraVideo.value.srcObject = stream;
      cameraVideo.value.play().catch(() => {});
    }
    if (cameraResultVideo.value) {
      cameraResultVideo.value.srcObject = stream;
      cameraResultVideo.value.play().catch(() => {});
    }
    cameraRunning.value = true;
    hasImage.value = true;
    resultImage.value = null;
    cameraBoxes.value = [];
    cameraFrameSize.value = { width: 0, height: 0 };
    detectionResult.value = null;
    scheduleCameraDetection(200);
  } catch (err) {
    console.error("打开摄像头失败", err);
    const name = err && err.name ? err.name : "Error";
    const msg = err && err.message ? err.message : "无法访问摄像头";
    ElMessage.error(`打开摄像头失败: ${name} - ${msg}`);
  }
};

const stopCamera = () => {
  if (cameraTimer) {
    clearTimeout(cameraTimer);
    cameraTimer = null;
  }
  cameraDetecting.value = false;
  cameraBoxes.value = [];
  cameraFrameSize.value = { width: 0, height: 0 };
  if (cameraVideo.value) {
    cameraVideo.value.srcObject = null;
  }
  if (cameraResultVideo.value) {
    cameraResultVideo.value.srcObject = null;
  }
  if (cameraStream.value) {
    cameraStream.value.getTracks().forEach((t) => t.stop());
    cameraStream.value = null;
  }
  cameraRunning.value = false;
};

const scheduleCameraDetection = (delay = cameraIntervalMs) => {
  if (!cameraRunning.value) return;
  if (cameraTimer) clearTimeout(cameraTimer);
  cameraTimer = setTimeout(async () => {
    await captureAndSendFrame();
    if (cameraRunning.value) {
      scheduleCameraDetection(cameraIntervalMs);
    }
  }, delay);
};

onBeforeUnmount(() => {
  stopCamera();
});

// 清理本地创建的 object URLs
onBeforeUnmount(() => {
  try {
    if (batchOriginalPreviews && batchOriginalPreviews.value) {
      batchOriginalPreviews.value.forEach((p) => {
        if (p && p.url) URL.revokeObjectURL(p.url);
      });
    }
  } catch (e) {
    // ignore
  }
});

const captureAndSendFrame = async () => {
  try {
    if (!cameraRunning.value || cameraDetecting.value || !cameraVideo.value) return;
    const videoEl = cameraVideo.value;
    if (!videoEl.videoWidth || !videoEl.videoHeight) return;
    const width = videoEl.videoWidth;
    const height = videoEl.videoHeight;
    cameraCanvas.width = width;
    cameraCanvas.height = height;
    const ctx = cameraCanvas.getContext("2d");
    ctx.drawImage(videoEl, 0, 0, width, height);

    cameraDetecting.value = true;
    const blob = await new Promise((resolve) => cameraCanvas.toBlob(resolve, "image/jpeg", 0.65));
    if (!blob) return;

    const formData = new FormData();
    formData.append("file", blob, "frame.jpg");
    formData.append("model_name", selectedModel.value);

    const resp = await detectFrame(formData);
    if (resp && resp.success && resp.data) {
      cameraBoxes.value = resp.data.boxes || [];
      cameraFrameSize.value = {
        width: resp.data.width || width,
        height: resp.data.height || height,
      };
      detectionResult.value = {
        boxes: cameraBoxes.value,
        total_objects: cameraBoxes.value.length,
        detection_time: resp.data.detection_time,
        model_name: selectedModel.value,
      };
      hasImage.value = true;
    }
  } catch (err) {
    console.error("帧发送失败", err);
  } finally {
    cameraDetecting.value = false;
  }
};

const handleRedetect = () => {
  const input = document.querySelector(
    `.function-tab[data-key="single"] .file-input`,
  );
  if (input) {
    input.click();
  }
};
</script>

<style scoped>
.detection-page {
  width: 100%;
  position: relative;
  padding: 28px 18px;
  background: linear-gradient(180deg, rgba(39,174,96,0.05) 0%, rgba(59,130,246,0.02) 100%);
}

.container {
  max-width: 1200px;
  margin: 0 auto;
}

.hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(90deg, rgba(0,230,118,0.06), rgba(0,188,212,0.03));
  padding: 28px 32px;
  border-radius: 16px;
  box-shadow: var(--card-shadow);
  margin-bottom: 18px;
}

.hero-left .breadcrumb {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.hero-left .page-title {
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.hero-left .page-subtitle {
  font-size: 14px;
  color: var(--text-secondary);
}

.hero-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.model-selector .el-select .el-input {
  border-radius: 10px;
}

/* 功能选项卡 */
.function-tabs {
  display: flex;
  gap: 14px;
  margin: 18px 0 22px 0;
}

.function-tab {
  flex: 1;
  display: flex;
  align-items: center;
  padding: 18px 22px;
  background-color: var(--card-bg);
  border-radius: 14px;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
  border: 1px solid rgba(0,0,0,0.03);
  position: relative;
}

.function-tab:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 30px rgba(16,24,40,0.06);
}

.function-tab.active {
  background: linear-gradient(90deg, rgba(39,174,96,0.08), rgba(96,165,250,0.04));
  border-color: rgba(39,174,96,0.18);
}

.tab-icon {
  font-size: 20px;
  color: var(--primary-color);
  margin-right: 14px;
  flex-shrink: 0;
}

.tab-inner { display:flex; align-items:center; gap:12px }
.tab-info { display:flex; flex-direction:column }
.tab-title { font-size:16px; font-weight:700; color:var(--text-primary) }
.tab-desc { font-size:12px; color:var(--text-secondary) }
.tab-bottom-indicator { position:absolute; left:12px; right:12px; bottom:8px; height:4px; background:linear-gradient(90deg,var(--primary-color),var(--accent)); border-radius:4px }
.function-tab.drag-over { border:2px dashed var(--primary-color); box-shadow: 0 12px 36px rgba(0,230,118,0.06); transform: translateY(-4px) }
.function-tab.active { box-shadow: 0 12px 36px rgba(0,230,118,0.04); border:1px solid rgba(0,230,118,0.08) }

/* compare image overlay */
.compare-image-wrap { position:relative; width:100%; height:100% }
.boxes-overlay { position:absolute; left:12px; top:12px; display:flex; flex-direction:column; gap:8px }
.box-tag { display:flex; align-items:center; gap:8px; padding:8px 10px; border-left:4px solid var(--primary-color); background: rgba(255,255,255,0.02); color:var(--text-primary); border-radius:8px; backdrop-filter: blur(6px); }
.tag-name { font-weight:600; font-size:13px }
.tag-conf { font-size:12px; color:var(--text-secondary) }
.camera-result-wrap { position:relative; width:100%; height:100%; background:#000; overflow:hidden }
.camera-video { object-fit:fill; background:#000 }
.camera-box-layer { position:absolute; inset:0; pointer-events:none }
.camera-box { position:absolute; border:2px solid var(--primary-color); border-radius:6px; box-shadow:0 0 0 1px rgba(0,0,0,0.35), 0 8px 20px rgba(0,0,0,0.18) }
.camera-box-label { position:absolute; left:-2px; top:-28px; max-width:180px; padding:4px 8px; border-radius:6px; background:rgba(0,0,0,0.72); color:#fff; font-size:12px; line-height:1.2; white-space:nowrap; overflow:hidden; text-overflow:ellipsis }
.camera-status { position:absolute; right:12px; top:12px; padding:6px 10px; border-radius:8px; background:rgba(0,0,0,0.58); color:#fff; font-size:12px }

/* stat cards */
.stat-cards { display:flex; gap:12px; align-items:stretch }
.stat-card { flex:1; padding:12px 14px; border-radius:10px; background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01)); border:1px solid rgba(255,255,255,0.02); box-shadow: var(--card-shadow) }
.stat-title { font-size:13px; color:var(--text-secondary); margin-bottom:6px }
.stat-value { font-size:20px; font-weight:700; color:var(--text-primary) }
.stat-sub { font-size:12px; color:var(--text-secondary); margin-top:6px }

/* detection list progress */
.list-row { display:flex; align-items:center; justify-content:space-between }
.list-left { flex:1; margin-right:10px }
.progress-bar { width:100%; height:8px; background: rgba(255,255,255,0.02); border-radius:8px; overflow:hidden; margin-top:6px }
.progress-fill { height:100%; width:0%; background:var(--primary-color); border-radius:8px }

.upload-preview-grid { display:flex; gap:6px; margin-top:10px }
.upload-preview-thumb { width:42px; height:30px; object-fit:cover; border-radius:6px; border:1px solid rgba(255,255,255,0.03) }

.tab-text { font-size: 15px; font-weight: 700; color: var(--text-primary); }
.tab-desc { font-size: 12px; color: var(--text-secondary); }

/* 主内容区域 */
.main-content {
  display: flex;
  gap: 24px;
}

.left-panel {
  flex: 1;
  background-color: var(--card-bg);
  border-radius: 16px;
  padding: 22px;
  box-shadow: var(--card-shadow);
  border: 1px solid rgba(255,255,255,0.02);
}

.panel-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:18px }
.panel-title { font-size:18px; font-weight:700; color:var(--text-primary) }
.result-tag { padding:6px 14px; border-radius:20px }

.toolbar .el-button { border-radius:8px }
.toolbar .el-button.active { background-color: transparent; color:var(--primary-color); border-color:transparent }

.image-compare { display:flex; gap:18px; height:380px }
.image-card { flex:1; position:relative; border-radius:12px; overflow:hidden; background: var(--card-bg); border:1px solid var(--border-color); box-shadow: var(--card-shadow); }
.compare-image { width:100%; height:100%; object-fit:cover; display:block }
.image-label { position:absolute; bottom:12px; left:12px; padding:6px 10px; background:rgba(0,0,0,0.45); color:#fff; border-radius:8px; font-size:13px }

.detection-mark { position:absolute; top:14px; right:14px; width:42px; height:42px; border-radius:8px; background:linear-gradient(180deg,var(--primary-color),var(--success-color)); display:flex; align-items:center; justify-content:center; color:#fff; font-weight:700 }

/* 右侧面板 */
.right-panel { width:380px; display:flex; flex-direction:column; gap:16px; }
.info-card, .result-card { background:var(--card-bg); border-radius:12px; padding:18px; box-shadow: var(--card-shadow) }

.card-header .el-icon { font-size:18px; color:var(--primary-color); margin-right:10px }
.card-title { font-size:15px; font-weight:700 }

.empty-icon { font-size:46px; color:var(--primary-color); margin-bottom:12px }
.detection-item { background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01)); padding:10px 12px; border-radius:8px; margin-bottom:10px; border:1px solid rgba(255,255,255,0.02) }

.batch-item { display:flex; gap:10px; align-items:center }
.batch-item .thumbs { display:flex; gap:6px; margin-right:8px }
.thumb-img { width:56px; height:40px; object-fit:cover; border-radius:6px; border:1px solid rgba(0,0,0,0.04) }
.batch-item.selected { box-shadow: 0 6px 18px rgba(16,24,40,0.06); border-radius:8px }

.batch-report-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap:18px; padding:8px }
.report-pair { background:var(--card-bg); padding:0; border-radius:12px; box-shadow: var(--card-shadow); display:flex; flex-direction:column; overflow:hidden }
.pair-images { display:flex; gap:8px }
.report-thumb { flex:1; height:180px; object-fit:cover; border-radius:0 }
.pair-meta { font-size:13px; padding:14px; background: linear-gradient(180deg, rgba(0,0,0,0.16), rgba(0,0,0,0.12)); color:var(--text-primary); border-bottom-left-radius:12px; border-bottom-right-radius:12px }
.pair-meta .meta-row { color: var(--text-secondary); margin-top:6px }
.pair-meta .meta-title { font-size:14px; color:var(--text-primary); margin-bottom:6px }
.pair-images .report-thumb:first-child { border-top-left-radius:12px }
.pair-images .report-thumb:last-child { border-top-right-radius:12px }

/* ensure images don't overflow dialog */
.batch-report-grid .report-pair img { display:block }

/* 批量对比两列布局 */
.batch-list-compare { height:100%; overflow:auto; display:flex; flex-direction:column; gap:12px; padding:10px }
.batch-row { position:relative; border-radius:8px; overflow:hidden; cursor:pointer }
.batch-row.selected { box-shadow: 0 8px 24px rgba(16,24,40,0.08); border:1px solid rgba(39,174,96,0.12) }
.batch-compare-img { width:100%; height:160px; object-fit:cover; display:block }
.row-overlay { position:absolute; left:10px; bottom:10px; background:rgba(0,0,0,0.45); color:#fff; padding:6px 10px; border-radius:8px; font-size:13px }

.action-buttons { display:flex; gap:12px }
.btn-secondary { flex:1; border-radius:10px }
.btn-primary { flex:2; border-radius:10px; background: linear-gradient(90deg,var(--primary-color),var(--accent)); color:#fff }

@media (max-width: 1100px) {
  .container { padding: 0 18px }
  .main-content { flex-direction:column }
  .right-panel { width:100% }
  .image-compare { height:260px }
}
</style>
