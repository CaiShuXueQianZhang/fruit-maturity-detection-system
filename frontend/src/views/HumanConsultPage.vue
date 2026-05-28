<template>
  <div class="consult-page">
    <div class="consult-wrapper">
      <div class="consult-header">
        <div class="header-left">
          <el-icon class="header-icon"><ChatDotRound /></el-icon>
          <div class="header-title">咨询顾问正在和您进行对话..</div>
        </div>
        <el-button type="text" class="end-btn" @click="endChat">结束对话</el-button>
      </div>

      <div class="chat-card">
        <div class="chat-messages" ref="messagesWrap">
          <div
            v-for="msg in messages"
            :key="msg.id"
            :class="['chat-message', msg.from === 'user' ? 'user' : 'agent']"
          >
            <div class="avatar" v-if="msg.from !== 'user'">
              <el-avatar size="36">顾</el-avatar>
            </div>

            <div class="bubble">{{ msg.text }}</div>

            <div class="avatar" v-if="msg.from === 'user'">
              <el-avatar size="36">我</el-avatar>
            </div>

            <div class="msg-time">{{ msg.time }}</div>
          </div>
        </div>

        <div class="chat-input">
          <el-input
            v-model="inputText"
            placeholder="请输入..."
            type="textarea"
            :rows="2"
            class="text-input"
          />
          <div class="input-actions">
            <div class="left-actions">
              <el-button type="text" @click="attachImage">上传图片</el-button>
              <el-button type="text" @click="attachFile">上传文件</el-button>
            </div>
            <el-button type="primary" @click="sendMessage" :disabled="!inputText.trim()">发送</el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from "vue";
import { ChatDotRound } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";

const messages = ref([
  {
    id: 1,
    from: "agent",
    text: "您好，国家认可专业第三方检测机构，权威资质认证；面向公检法、企事业单位提供检测、测试、鉴定、分析服务。",
    time: "10:00:45",
  },
  { id: 2, from: "agent", text: "您好", time: "10:01:45" },
  { id: 3, from: "agent", text: "您是要做样品 检测吗？", time: "10:01:52" },
  { id: 4, from: "agent", text: "您是什么需要检测呢？", time: "10:01:54" },
]);

const inputText = ref("");
const messagesWrap = ref(null);

const scrollBottom = () => {
  if (messagesWrap.value) {
    messagesWrap.value.scrollTop = messagesWrap.value.scrollHeight;
  }
};

onMounted(() => {
  nextTick(scrollBottom);
});

const sendMessage = () => {
  const text = inputText.value && inputText.value.trim();
  if (!text) return;
  messages.value.push({ id: Date.now(), from: "user", text, time: new Date().toLocaleTimeString() });
  inputText.value = "";
  nextTick(scrollBottom);

  // 模拟人工顾问回复（占位），实际接入客服系统或 websocket
  setTimeout(() => {
    messages.value.push({ id: Date.now() + 1, from: "agent", text: "感谢您的咨询，我们的顾问正在处理，请稍等。", time: new Date().toLocaleTimeString() });
    nextTick(scrollBottom);
  }, 800);
};

const attachImage = () => {
  ElMessage.info("图片上传功能待接入");
};
const attachFile = () => {
  ElMessage.info("文件上传功能待接入");
};

const endChat = () => {
  ElMessage.success("对话已结束");
};
</script>

<style scoped>
.consult-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 20px 40px;
}

.consult-header {
  width: 100%;
  max-width: 1100px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #6c63ff;
  color: #fff;
  padding: 12px 18px;
  border-radius: 8px 8px 0 0;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.06);
  margin-bottom: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-icon { color: #fff; }
.header-title { font-weight: 600; font-size: 16px; }
.end-btn { color: rgba(255,255,255,0.9); }

.chat-card {
  width: 100%;
  max-width: 1100px;
  background: #fff;
  border-radius: 0 0 8px 8px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.06);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.chat-messages {
  height: 520px;
  overflow-y: auto;
  padding: 20px;
  background: #f4f6fb;
}

.chat-message {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  margin-bottom: 12px;
  max-width: 80%;
}

.chat-message.agent { flex-direction: row; }
.chat-message.user { flex-direction: row-reverse; margin-left: auto; }

.bubble {
  padding: 10px 14px;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 1px 0 rgba(0,0,0,0.04);
  line-height: 1.5;
}

.chat-message.user .bubble { background: #3b82f6; color: #fff; }
.avatar { width: 36px; height: 36px; }
.msg-time { font-size: 12px; color: #9aa0b4; margin-left: 8px; }

.chat-input { padding: 14px 18px; border-top: 1px solid #eef2f6; background: #fff; display: flex; flex-direction: column; gap: 8px; }
.text-input { width: 100%; }
.input-actions { display: flex; justify-content: space-between; align-items: center; }
.left-actions { display: flex; gap: 8px; }

@media (max-width: 1200px) {
  .consult-header, .chat-card { max-width: 920px; }
}

@media (max-width: 768px) {
  .consult-header, .chat-card { max-width: 100%; }
  .chat-messages { height: 360px; }
}
</style>
