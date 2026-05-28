<template>
  <div class="history-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1 class="page-title">检测历史记录</h1>
      <p class="page-subtitle">查看和管理您的所有检测记录</p>
    </div>

    <!-- 搜索和筛选 -->
    <div class="search-bar">
      <el-input
        v-model="searchQuery"
        placeholder="搜索检测记录..."
        size="default"
        class="search-input"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>

      <el-select
        v-model="filterStatus"
        placeholder="状态筛选"
        size="default"
        class="filter-select"
      >
        <el-option label="全部" value="" />
        <el-option label="检测完成" value="completed" />
        <el-option label="检测中" value="processing" />
        <el-option label="失败" value="failed" />
      </el-select>

      <el-select
        v-model="filterType"
        placeholder="类型筛选"
        size="default"
        class="filter-select"
      >
        <el-option label="全部" value="" />
        <el-option label="单图检测" value="single" />
        <el-option label="批量检测" value="batch" />
        <el-option label="文件夹" value="folder" />
        <el-option label="视频检测" value="video" />
      </el-select>
    </div>

    <!-- 记录列表 -->
    <div class="history-list">
      <div
        v-for="record in filteredRecords"
        :key="record.id"
        class="history-card"
        @click="viewRecord(record)"
      >
        <div class="record-preview">
          <template v-if="record.type === 'video' && !(record.cover_image_url || record.result_image_url)">
            <video
              :src="record.video_url || record.image_url"
              class="preview-image"
              muted
              preload="metadata"
            ></video>
          </template>
          <template v-else>
            <img
              :src="record.cover_image_url || record.result_image_url || record.image_url"
              :alt="record.filename"
              class="preview-image"
            />
          </template>
          <div
            class="status-badge"
            :class="record.status"
          >
            <el-icon><component :is="getStatusIcon(record.status)" /></el-icon>
            {{ getStatusText(record.status) }}
          </div>
        </div>

        <div class="record-info">
          <div class="record-header">
            <span class="record-filename">{{ record.filename }}</span>
            <span class="record-type">{{ getTypeText(record.type) }}</span>
          </div>
          <div class="record-meta">
            <span class="meta-item">
              <el-icon><Clock /></el-icon>
              {{ record.time }}
            </span>
            <span class="meta-item">
              <el-icon><Picture /></el-icon>
              {{ record.type === 'video' ? '1 个视频' : `${record.count || 1} 张图片` }}
            </span>
            <span class="meta-item">
              <el-icon><Aim /></el-icon>
              {{ record.total_objects }} 个水果
            </span>
          </div>
          <div class="record-tags">
            <span
              v-for="tag in record.detectedTargets"
              :key="tag"
              class="detected-tag"
            >
              {{ tag }}
            </span>
          </div>
        </div>

        <div class="record-actions">
          <el-button size="small" @click.stop="viewRecord(record)">
            <el-icon><Monitor/></el-icon>
            查看
          </el-button>
          <el-button size="small" @click.stop="downloadRecord(record)">
            <el-icon><Download/></el-icon>
            下载
          </el-button>
          <el-button
            size="small"
            type="danger"
            @click.stop="deleteRecord(record)"
          >
            <el-icon><Delete/></el-icon>
            删除
          </el-button>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="filteredRecords.length === 0" class="empty-state">
      <el-icon :size="64" class="empty-icon"><Help /></el-icon>
      <p class="empty-text">暂无检测记录</p>
      <el-button type="primary" @click="goToDetection">
        <el-icon><Plus /></el-icon>
        开始检测
      </el-button>
    </div>

    <!-- 分页 -->
    <div class="pagination-wrapper">
      <el-pagination
        v-if="totalRecords > 0"
        :total="totalRecords"
        :page-size="pageSize"
        :current-page="currentPage"
        @current-change="handlePageChange"
        layout="prev, pager, next"
      />
    </div>

    # 历史记录查看
    <!-- 详情弹窗 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="检测详情"
      width="800px"
      :close-on-click-modal="false"
    >
      <div v-if="detailLoading" class="detail-loading">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>加载中...</span>
      </div>
      <div v-else-if="detailData" class="detail-content">
        <!-- 图片展示区域 -->
        <div class="detail-images">
          <div class="image-container">
            <h4>原始图片</h4>
            <img
              :src="detailData.image_url"
              :alt="detailData.filename"
              class="detail-image"
            />
          </div>
          <div class="image-container">
            <h4>检测结果</h4>
            <img
              :src="detailData.result_image_url"
              :alt="detailData.filename"
              class="detail-image"
            />
          </div>
        </div>

        <!-- 详细信息 -->
        <div class="detail-info">
          <div class="info-row">
            <span class="info-label">文件名</span>
            <span class="info-value">{{ detailData.filename }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">检测类型</span>
            <span class="info-value">{{ getTypeText(detailData.type) }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">检测时间</span>
            <span class="info-value">{{ detailData.time }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">检测状态</span>
            <span class="info-value" :class="detailData.status">{{ getStatusText(detailData.status) }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">检测到水果数量</span>
            <span class="info-value">{{ detailData.total_objects }}</span>
          </div>
        </div>

        <!-- 检测框详情 -->
        <div v-if="detailData.boxes && detailData.boxes.length > 0" class="boxes-section">
          <h4>检测框详情</h4>
          <el-table :data="detailData.boxes" border>
            <el-table-column prop="class_name" label="类别" />
            <el-table-column prop="confidence" label="置信度" />
            <el-table-column prop="x_min" label="X坐标" />
            <el-table-column prop="y_min" label="Y坐标" />
            <el-table-column prop="width" label="宽度" />
            <el-table-column prop="height" label="高度" />
          </el-table>
        </div>
      </div>
      <div v-else class="detail-empty">
        暂无详情数据
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import {
  Search,
  Clock,
  Picture,
  Aim,
  Monitor,
  Download,
  Delete,
  Plus,
  Help,
  CircleCheck,
  Loading,
  CircleClose,
} from "@element-plus/icons-vue";
import { ElMessage } from 'element-plus'
import { getDetectionHistory, deleteDetection, getDetectionDetail } from "../api/detection";

const router = useRouter();

const searchQuery = ref("");
const filterStatus = ref("");
const filterType = ref("");
const currentPage = ref(1);
const pageSize = ref(10);
const isLoading = ref(false);

const historyRecords = ref([]);
const totalRecords = ref(0);

// 详情弹窗相关
const detailDialogVisible = ref(false);
const detailLoading = ref(false);
const detailData = ref(null);

const fetchHistory = async () => {
  isLoading.value = true;
  try {
    const response = await getDetectionHistory({
      page: currentPage.value,
      page_size: pageSize.value,
    });
    if (response.success && response.data) {
      historyRecords.value = response.data;
      totalRecords.value = response.total;
    }
  } catch (error) {
    console.error("获取历史记录失败:", error);
    historyRecords.value = [];
    totalRecords.value = 0;
  } finally {
    isLoading.value = false;
  }
};

onMounted(() => {
  fetchHistory();
});

const filteredRecords = computed(() => {
  return historyRecords.value.filter((record) => {
    const matchesSearch =
      !searchQuery.value ||
      record.filename.toLowerCase().includes(searchQuery.value.toLowerCase());
    const matchesStatus = !filterStatus.value || record.status === filterStatus.value;
    const matchesType = !filterType.value || record.type === filterType.value;
    return matchesSearch && matchesStatus && matchesType;
  });
});

const getStatusIcon = (status) => {
  const icons = {
    completed: CircleCheck,
    processing: Loading,
    failed: CircleClose,
  };
  return icons[status] || CircleCheck;
};

const getStatusText = (status) => {
  const texts = {
    completed: "检测完成",
    processing: "检测中",
    failed: "失败",
  };
  return texts[status] || status;
};

const getTypeText = (type) => {
  const texts = {
    single: "单图检测",
    batch: "批量检测",
    folder: "文件夹",
    video: "视频检测",
  };
  return texts[type] || type;
};

const viewRecord = async (record) => {
  detailDialogVisible.value = true;
  detailLoading.value = true;
  detailData.value = null;
  
  try {
    const response = await getDetectionDetail(record.id);
    if (response.success && response.data) {
      detailData.value = response.data;
    }
  } catch (error) {
    console.error("获取检测详情失败:", error);
    ElMessage.error("获取详情失败，请稍后重试");
  } finally {
    detailLoading.value = false;
  }
};

const downloadRecord = async (record) => {
  try {
    // 构建下载 URL
    const downloadUrl = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'}/detection/download/${record.id}`;
    
    // 创建隐藏的下载链接
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = record.filename || `detection_${record.id}.jpg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    ElMessage.success("下载成功");
  } catch (error) {
    console.error("下载失败:", error);
    ElMessage.error("下载失败，请稍后重试");
  }
};

const deleteRecord = async (record) => {
  if (!confirm(`确定要删除记录 "${record.filename}" 吗？`)) return;
  try {
    const res = await deleteDetection(record.id);
    if (res && res.success) {
      // 成功后刷新列表或本地移除
      const index = historyRecords.value.findIndex((r) => r.id === record.id);
      if (index > -1) {
        historyRecords.value.splice(index, 1);
      } else {
        // 若未在当前页找到，尝试重新拉取
        fetchHistory();
      }
      ElMessage.success(res.message || "删除成功");
    } else {
      ElMessage.error((res && res.message) || "删除失败");
      fetchHistory();
    }
  } catch (err) {
    console.error("删除记录失败", err);
    ElMessage.error("删除失败，请稍后重试");
    fetchHistory();
  }
};

const goToDetection = () => {
  router.push("/detection");
};

const handlePageChange = (page) => {
  currentPage.value = page;
};
</script>

<style scoped lang="scss">
.history-page {
  width: 100%;

  .page-header {
    margin-bottom: 24px;

    .page-title {
      font-size: 24px;
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: 8px;
    }

    .page-subtitle {
      font-size: 14px;
      color: var(--text-secondary);
    }
  }

  .search-bar {
    display: flex;
    gap: 16px;
    margin-bottom: 24px;
    align-items: center;

    .search-input {
      flex: 1;
      max-width: 300px;
    }

    .filter-select {
      width: 140px;
    }
  }

  .history-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .history-card {
    background-color: #ffffff;
    border-radius: 12px;
    padding: 20px;
    box-shadow: var(--card-shadow);
    display: flex;
    align-items: center;
    gap: 20px;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
      transform: translateY(-2px);
    }

    .record-preview {
      position: relative;
      width: 120px;
      height: 80px;
      border-radius: 8px;
      overflow: hidden;

      .preview-image {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }

      .status-badge {
        position: absolute;
        bottom: 8px;
        left: 8px;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 12px;
        display: flex;
        align-items: center;
        gap: 4px;

        &.completed {
          background-color: rgba(34, 197, 94, 0.9);
          color: white;
        }

        &.processing {
          background-color: rgba(59, 130, 246, 0.9);
          color: white;
        }

        &.failed {
          background-color: rgba(239, 68, 68, 0.9);
          color: white;
        }
      }
    }

    .record-info {
      flex: 1;
      min-width: 0;

      .record-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 10px;

        .record-filename {
          font-size: 15px;
          font-weight: 500;
          color: var(--text-primary);
        }

        .record-type {
          padding: 3px 8px;
          background-color: #f3f4f6;
          border-radius: 4px;
          font-size: 12px;
          color: var(--text-secondary);
        }
      }

      .record-meta {
        display: flex;
        gap: 20px;
        margin-bottom: 10px;

        .meta-item {
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 13px;
          color: var(--text-secondary);

          :deep(.el-icon) {
            font-size: 14px;
          }
        }
      }

      .record-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;

        .detected-tag {
          padding: 3px 8px;
          background-color: rgba(39, 174, 96, 0.1);
          color: #27ae60;
          border-radius: 4px;
          font-size: 12px;
        }
      }
    }

    .record-actions {
      display: flex;
      gap: 8px;
    }
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 0;

    .empty-icon {
      color: #9ca3af;
      margin-bottom: 16px;
    }

    .empty-text {
      font-size: 15px;
      color: var(--text-secondary);
      margin-bottom: 24px;
    }
  }

  .pagination-wrapper {
    display: flex;
    justify-content: center;
    margin-top: 32px;
  }

  /* 详情弹窗样式 */
  .detail-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px;
  }

  .detail-content {
    .detail-images {
      display: flex;
      gap: 20px;
      margin-bottom: 24px;

      .image-container {
        flex: 1;
        text-align: center;

        h4 {
          font-size: 14px;
          font-weight: 500;
          margin-bottom: 12px;
          color: var(--text-primary);
        }

        .detail-image {
          max-width: 100%;
          max-height: 280px;
          object-fit: contain;
          border-radius: 8px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
      }
    }

    .detail-info {
      background-color: #ffffff;
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 24px;

      .info-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 0;
        border-bottom: 1px solid #f3f4f6;

        &:last-child {
          border-bottom: none;
        }

        .info-label {
          font-size: 14px;
          color: #64748b;
          font-weight: 500;
          min-width: 100px;
        }

        .info-value {
          font-size: 14px;
          color: #1e293b;
          font-weight: 400;

          &.completed {
            color: #10b981;
            font-weight: 500;
          }

          &.processing {
            color: #3b82f6;
            font-weight: 500;
          }

          &.failed {
            color: #ef4444;
            font-weight: 500;
          }
        }
      }
    }

    .boxes-section {
      h4 {
        font-size: 14px;
        font-weight: 500;
        margin-bottom: 12px;
        color: var(--text-primary);
      }

      :deep(.el-table) {
        font-size: 12px;
      }
    }
  }

  .detail-empty {
    text-align: center;
    padding: 40px;
    color: var(--text-secondary);
  }
}
</style>
