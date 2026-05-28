<template>
  <div class="qa-page">
    <div class="page-header">
      <h1 class="page-title">AI 智能问答</h1>
      <p class="page-subtitle">关于果园水果检测的任何问题，都可以问我</p>
    </div>

    <div class="chat-container">
      <div ref="messagesContainer" class="chat-messages">
        <div
          v-for="(message, index) in messages"
          :key="index"
          :class="['message', message.role === 'user' ? 'user-message' : 'ai-message']"
        >
          <div class="message-avatar">
            <el-icon v-if="message.role === 'user'"><User /></el-icon>
            <el-icon v-else><ChatDotRound /></el-icon>
          </div>
          <div class="message-content">
            <div v-if="message.role === 'assistant' && message.loading" class="loading-indicator">
              <span class="loading-dot"></span>
              <span class="loading-dot"></span>
              <span class="loading-dot"></span>
            </div>
            <span v-else>{{ message.content }}</span>
          </div>
        </div>
      </div>

      <div class="chat-input">
        <el-input
          v-model="question"
          placeholder="请输入你的问题..."
          :rows="3"
          @keyup.enter="sendMessage"
        />
        <el-button type="primary" class="send-btn" :loading="sending" @click="sendMessage">
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from "vue";
import { ChatDotRound, User } from "@element-plus/icons-vue";
import request from "../utils/request";

const question = ref("");
const sending = ref(false);
const messagesContainer = ref(null);

// 消息列表
const messages = ref([
  {
    role: "assistant",
    content:
      "你好！我是果园水果检测AI助手。我可以帮你解答关于香蕉、芒果等水果识别、成熟度判断、病虫害检测等问题，也可以为你提供检测结果的详细分析。",
    loading: false,
  },
]);

// 历史对话记录（用于多轮对话）
const history = ref([]);

// 发送消息
const sendMessage = async () => {
  const text = question.value.trim();
  if (!text || sending.value) return;

  // 添加用户消息
  messages.value.push({
    role: "user",
    content: text,
    loading: false,
  });

  // 清空输入框
  question.value = "";

  // 添加加载中的AI消息
  messages.value.push({
    role: "assistant",
    content: "",
    loading: true,
  });

  // 滚动到底部
  await nextTick();
  scrollToBottom();

  try {
    sending.value = true;

    // 调用后端API
    const response = await request.post("/qa/chat", {
      question: text,
      history: history.value,
    });

    if (response.success) {
      // 更新历史记录
      history.value = response.history || [];

      // 更新AI消息
      const lastMessage = messages.value[messages.value.length - 1];
      lastMessage.content = response.answer;
      lastMessage.loading = false;
    }
  } catch (error) {
    // 更新AI消息显示错误
    const lastMessage = messages.value[messages.value.length - 1];
    lastMessage.content = "抱歉，问答服务暂时不可用，请稍后重试。";
    lastMessage.loading = false;
  } finally {
    sending.value = false;
    // 滚动到底部
    await nextTick();
    scrollToBottom();
  }
};

// 滚动到底部
const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
};
</script>

<style scoped lang="scss">
.qa-page {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;

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

  .chat-container {
    flex: 1;
    background-color: var(--card-bg);
    border-radius: 10px;
    box-shadow: var(--card-shadow);
    display: flex;
    flex-direction: column;
    overflow: hidden;

    .chat-messages {
      flex: 1;
      padding: 20px;
      overflow-y: auto;

      .message {
        display: flex;
        margin-bottom: 20px;
        animation: fadeIn 0.3s ease;

        .message-avatar {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          background-color: var(--primary-color);
          color: white;
          display: flex;
          align-items: center;
          justify-content: center;
          margin-right: 12px;
          flex-shrink: 0;
        }

        .message-content {
          background-color: var(--muted-bg);
          padding: 12px 16px;
          border-radius: 0 12px 12px 12px;
          max-width: 70%;
          line-height: 1.6;
          font-size: 14px;

          .loading-indicator {
            display: flex;
            gap: 6px;
            padding: 8px 0;

            .loading-dot {
              width: 8px;
              height: 8px;
              border-radius: 50%;
              background-color: var(--primary-color);
              animation: loadingBounce 1.4s infinite ease-in-out;

              &:nth-child(1) {
                animation-delay: -0.32s;
              }

              &:nth-child(2) {
                animation-delay: -0.16s;
              }
            }
          }
        }

        &.user-message {
          flex-direction: row-reverse;

          .message-avatar {
            margin-right: 0;
            margin-left: 12px;
            background-color: var(--info);
          }

          .message-content {
            background-color: var(--primary-light);
            border-radius: 12px 0 12px 12px;
          }
        }
      }
    }

    .chat-input {
      padding: 20px;
      border-top: 1px solid var(--border-color);
      display: flex;
      gap: 12px;

      :deep(.el-input) {
        flex: 1;

        textarea {
          resize: none;
        }
      }

      .send-btn {
        width: 100px;
        height: auto;
        align-self: flex-end;
      }
    }
  }
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes loadingBounce {
  0%,
  80%,
  100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}
</style>
