/**
 * ============================================================================
 * 回忆录小程序 - 采访页面
 * ============================================================================
 * 
 * 功能描述:
 *   这是回忆录小程序的核心页面，实现了与用户的语音交互功能：
 *   1. 录音并实时转文字（语音识别 ASR）
 *   2. 将用户讲述发送给AI进行对话
 *   3. 播放AI回复的语音（语音合成 TTS）
 * 
 * 技术架构:
 *   - 前端：微信小程序
 *   - 录音：wx.getRecorderManager()
 *   - 音频播放：wx.createInnerAudioContext()
 *   - 通信：WebSocket（ASR、Chat两条连接）
 *   - 后端：FastAPI + 火山引擎 + 豆包AI
 * 
 * 状态流转:
 *   idle（空闲）→ recording（录音中）→ thinking（AI思考中）→ talking（AI播放语音）→ idle
 * 
 * 创建日期: 2026-01
 * ============================================================================
 */

const app = getApp()

Page({
    // ========================================================================
    // 页面数据（响应式）
    // ========================================================================
    data: {
        // 当前状态：idle（空闲）、recording（录音中）、thinking（AI思考中）、talking（AI说话中）
        status: 'idle',

        // AI显示的消息（当前AI回复）
        aiMessage: "你好呀!我叫念念,",

        // 用户输入（语音识别结果）
        userInput: "",

        // 录音倒计时（秒）
        recordingTime: "00:00",

        // 录音计时器
        timer: null,

        // 已录音秒数
        seconds: 0,

        // 对话历史消息列表
        // 格式: [{role: 'user/assistant', content: '...'}]
        userInput: '',
        aiMessage: '',
        recordingTime: '00:00',
        currentTextId: null,  // 当前对话的 user_text_id

        // ASR WebSocket连接状态
        socketOpen: false,

        // 音频文件计数器（用于生成唯一文件名，防止冲突）
        audioCounter: 0,

        // 用户字幕滚动位置
        userScrollTop: 0
    },

    // ========================================================================
    // 非响应式属性（实例变量）
    // ========================================================================

    /**
     * ASR语句追踪系统
     * 
     * 背景：
     *   火山引擎ASR返回的utterances会动态变化。当第一个句子确认后，
     *   后续返回的数据中，该句子会消失，新句子的index会重新从0开始。
     * 
     * 解决方案：
     *   使用全局索引偏移量(indexOffset)来确保每个句子存储在正确的位置。
     *   当index=0的句子确认时，offset+1，后续句子的全局索引 = offset + 本地index。
     */
    utterances: [],       // 已确认的语句数组（按全局索引存储）
    tempUtterances: {},   // 临时语句对象（按全局索引存储，尚未确认的句子）
    indexOffset: 0,       // 全局索引偏移量

    // ========================================================================
    // 生命周期函数
    // ========================================================================

    /**
     * 页面加载时执行
     * 初始化音频播放器和录音管理器
     */
    onLoad() {
        // 获取用户ID
        const userId = wx.getStorageSync('userId');

        // 调用后端接口获取最新 AI 消息
        if (userId) {
            wx.request({
                url: getApp().globalData.baseUrl + '/api/get_latest_ai_message',
                method: 'GET',
                data: { user_id: userId },
                success: (res) => {
                    if (res.data && res.data.code === 0 && res.data.data.ai_message) {
                        this.setData({ aiMessage: res.data.data.ai_message });
                        console.log("✅ 加载最新 AI 消息:", res.data.data.ai_message);
                    } else {
                        // 没有历史消息，使用默认文案
                        console.log("📭 未找到历史 AI 消息，使用默认文案");
                        this.setData({ aiMessage: "你好呀!我叫念念," });
                    }
                },
                fail: (err) => {
                    console.error("❌ 获取最新 AI 消息失败:", err);
                    // 接口失败也使用默认文案
                    this.setData({ aiMessage: "你好呀!我叫念念," });
                }
            });
        } else {
            // 没有 userId，使用默认文案
            this.setData({ aiMessage: "你好呀!我叫念念," });
        }

        // 初始化对话历史（AI的开场白）
        this.setData({
            messages: [{ role: 'assistant', content: this.data.aiMessage }]
        });

        // ==================== 初始化音频播放器 ====================
        // this.initAudioPlayer(); // 兼容旧模式
        this.initWebAudio();    // v3.4 PCM 模式

        // ==================== 初始化录音管理器 ====================
        this.initRecorderManager();

        // 注意：ASR WebSocket不在此处连接，而是在录音开始时按需连接
    },

    /**
     * 初始化音频播放实例
     * 防御式编程：确保播放器实例始终可用
     */
    initAudioPlayer() {
        if (this.player) {
            try { this.player.destroy(); } catch (e) { }
        }

        this.player = wx.createInnerAudioContext();
        this.player.onPlay(() => console.log('音频播放开始'));

        // 初始化音频队列
        this.audioQueue = this.audioQueue || [];
        this.isPlaying = false;

        // 音频播放结束回调
        this.player.onEnded(() => {
            console.log('音频播放结束');
            if (this.currentAudioPath && this.currentAudioPath.startsWith(wx.env.USER_DATA_PATH)) {
                wx.getFileSystemManager().unlink({
                    filePath: this.currentAudioPath,
                    success: () => console.log('🗑️ 临时文件已删除'),
                    fail: (err) => console.warn('删除临时文件失败:', err)
                });
            }
            this.isPlaying = false;
            this.playNextAudio();
        });

        // 音频播放错误回调
        this.player.onError((err) => {
            console.error('音频播放错误:', err);
            // 如果报错是 audioInstance is not set，自动重试初始化
            if (err.errMsg && err.errMsg.includes('audioInstance is not set')) {
                console.warn('🔄 检测到播放器实例未设置，尝试重新初始化...');
                this.initAudioPlayer();
            }
            this.isPlaying = false;
            this.playNextAudio();
        });
    },

    /**
     * ==================== WebAudio PCM 播放器初始化 (v3.4) ====================
     * 用于无缝拼接 PCM 裸流
     */
    initWebAudio() {
        if (!wx.createWebAudioContext) {
            console.error("当前微信版本不支持 WebAudioContext，将回退到普通播放模式");
            return;
        }

        console.log("初始化 WebAudioContext (PCM 模式)");
        this.audioCtx = wx.createWebAudioContext();

        // 创建增益节点（用于音量控制，后期可扩展）
        this.gainNode = this.audioCtx.createGain();
        this.gainNode.connect(this.audioCtx.destination);

        // 播放状态管理
        this.nextStartTime = 0; // 下一个音频分片的预定开始时间
        this.pcmSampleRate = 24000; // 后端下发的 PCM 采样率
    },

    /**
     * 播放收到的 PCM Base64 分片
     * @param {string} b64Data - Base64 编码的 PCM 裸流
     */
    playPCMChunk(b64Data) {
        if (!this.audioCtx) return;

        try {
            // 1. 将 Base64 转为 ArrayBuffer
            const arrayBuffer = wx.base64ToArrayBuffer(b64Data);

            // 2. 将 Int16 PCM 数据转换为 Float32 (WebAudio 要求)
            const int16View = new Int16Array(arrayBuffer);
            const float32Data = new Float32Array(int16View.length);
            for (let i = 0; i < int16View.length; i++) {
                // 归一化：将 -32768~32767 映射到 -1.0~1.0
                float32Data[i] = int16View[i] / 32768.0;
            }

            // 3. 创建 AudioBuffer
            const audioBuffer = this.audioCtx.createBuffer(1, float32Data.length, this.pcmSampleRate);
            audioBuffer.copyToChannel(float32Data, 0);

            // 4. 创建 BufferSource 并调度播放
            const source = this.audioCtx.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(this.gainNode);

            // 计算该分片的持续时间（秒）
            const duration = audioBuffer.duration;

            // 调度播放时间
            // 如果 nextStartTime 比当前时间早，说明是首包，或者播放已经赶上了。此时立即播放并对齐 currentTime。
            const currentTime = this.audioCtx.currentTime;
            let playTime = Math.max(this.nextStartTime, currentTime);

            // 如果是首包，加一小段 buffer 延迟（50ms）防止初次卡顿
            if (this.nextStartTime === 0) {
                playTime += 0.05;
            }

            source.start(playTime);

            // 记录下一段的预定开始时间（实现无缝衔接的关键！）
            this.nextStartTime = playTime + duration;

            // 状态管理：播放中
            if (this.data.status !== 'talking') {
                this.setData({ status: 'talking' });
            }

        } catch (e) {
            console.error("PCM 播放失败:", e);
        }
    },

    /**
     * 页面卸载时执行
     * 清理WebSocket连接和音频播放
     */
    onUnload() {
        console.log("📤 页面卸载,清理资源...");

        // 关闭ASR WebSocket
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }

        // 关闭对话WebSocket
        if (this.chatSocket) {
            this.chatSocket.close();
            this.chatSocket = null;
        }

        // 停止WebAudio播放
        if (this.audioCtx) {
            try {
                this.audioCtx.suspend();
                this.audioCtx.close();
                console.log("🔇 WebAudio已停止");
            } catch (e) {
                console.warn("WebAudio停止失败:", e);
            }
        }

        // 停止录音
        if (this.recorderManager && this.data.status === 'recording') {
            try {
                this.recorderManager.stop();
                console.log("🎤 录音已停止");
            } catch (e) {
                console.warn("录音停止失败:", e);
            }
        }

        // 清除定时器
        if (this.data.timer) {
            clearInterval(this.data.timer);
        }

        // 清除超时定时器
        if (this.thinkingTimeout) {
            clearTimeout(this.thinkingTimeout);
        }

        console.log("✅ 资源清理完成");
    },

    // ========================================================================
    // ASR（语音识别）WebSocket管理
    // ========================================================================

    /**
     * 连接ASR WebSocket
     * 
     * 该连接用于实时传输音频数据到后端，并接收识别结果。
     * 采用"按需连接，用完即关"的策略，避免长时间占用资源。
     */
    connectASRWebSocket() {
        // 后端ASR WebSocket地址（局域网IP，真机测试用）
        const baseUrl = getApp().globalData.baseUrl.replace('http://', '');
        const wsUrl = `ws://${baseUrl}/ws/asr`;

        console.log("正在连接ASR WebSocket:", wsUrl);

        // 如果已有连接，先关闭
        if (this.socket && this.data.socketOpen) {
            console.log("关闭已存在的ASR连接...");
            this.socket.close({ code: 1000, reason: '重新连接' });
            this.socket = null;
            this.setData({ socketOpen: false });
        }

        // 创建新的WebSocket连接
        this.socket = wx.connectSocket({
            url: wsUrl,
            success: () => console.log('ASR连接请求已发送'),
            fail: (err) => console.error('ASR连接失败:', err)
        });

        // 连接打开回调
        this.socket.onOpen(() => {
            console.log("✅ ASR WebSocket已连接");
            this.setData({ socketOpen: true });
        });

        // 连接关闭回调
        this.socket.onClose((res) => {
            console.log("ASR WebSocket已关闭:", res);
            this.setData({ socketOpen: false });
        });

        // 连接错误回调
        this.socket.onError((err) => {
            console.error("ASR WebSocket错误:", err);
        });

        // ==================== 接收ASR识别结果 ====================
        this.socket.onMessage((res) => {
            try {
                const data = JSON.parse(res.data);

                if (data.text) {
                    const text = data.text;           // 识别的文字
                    const isFinal = data.is_final || false;  // 是否为最终结果
                    const index = data.index !== undefined ? data.index : 0;  // 句子本地索引
                    const globalIndex = this.indexOffset + index;  // 计算全局索引

                    if (isFinal) {
                        // ===== 确认结果处理 =====
                        // 该句子已确认，不会再变化
                        this.utterances[globalIndex] = text;
                        delete this.tempUtterances[globalIndex];
                        console.log(`✅ ASR确认 [本地=${index}, 全局=${globalIndex}]: ${text.slice(0, 20)}...`);

                        // 关键逻辑：当index=0的句子确认时，说明ASR会"移除"这个句子
                        // 后续新句子的index会重新从0开始，所以需要增加偏移量
                        if (index === 0) {
                            this.indexOffset++;
                            console.log(`📍 偏移量增加到: ${this.indexOffset}`);
                        }
                    } else {
                        // ===== 临时结果处理 =====
                        // 该句子还在输入中，可能会变化
                        this.tempUtterances[globalIndex] = text;
                        console.log(`🟡 ASR临时 [本地=${index}, 全局=${globalIndex}]: ${text.slice(0, 20)}...`);
                    }

                    // ===== 更新显示文本 =====
                    // 拼接已确认的句子 + 临时句子
                    const confirmedText = this.utterances.filter(u => u).join('');
                    const tempText = Object.values(this.tempUtterances).join('');
                    const displayText = confirmedText + tempText;

                    // 每次都更新,使用固定大数值滚动到底部
                    this.setData({
                        userInput: displayText,
                        userScrollTop: 999999
                    });
                }
            } catch (e) {
                console.error("ASR解析错误:", e);
            }
        });
    },

    // ========================================================================
    // 录音管理器
    // ========================================================================

    /**
     * 初始化录音管理器
     * 
     * 配置录音参数并绑定各种回调事件。
     * 录音采用PCM格式，16kHz采样率，实时帧传输，适合流式ASR。
     */
    initRecorderManager() {
        try {
            this.recorderManager = wx.getRecorderManager();
        } catch (e) {
            console.error("录音管理器初始化失败:", e);
            return;
        }

        // 录音开始回调
        this.recorderManager.onStart(() => {
            console.log('录音已开始');
        });

        // ==================== 实时帧数据回调 ====================
        // 每隔一定时间触发，将音频帧通过WebSocket发送到后端
        this.recorderManager.onFrameRecorded((res) => {
            const { frameBuffer } = res;

            // 检测是否为静音数据（用于调试麦克风问题）
            const uint8View = new Uint8Array(frameBuffer);
            let isSilent = true;
            for (let i = 0; i < uint8View.length; i++) {
                if (uint8View[i] !== 0) {
                    isSilent = false;
                    break;
                }
            }

            if (isSilent) {
                console.warn('🔴 警告: 采集到静音数据!');
            }

            // 通过WebSocket发送音频帧
            if (this.data.socketOpen && this.socket) {
                this.socket.send({
                    data: frameBuffer
                });
            }
        });

        // ==================== 录音结束回调 ====================
        this.recorderManager.onStop((res) => {
            const { tempFilePath, fileSize, duration } = res;

            console.log("录音已停止，文件大小:", fileSize, "时长:", duration);

            // 关闭ASR WebSocket
            if (this.socket) {
                console.log("🔌 关闭ASR连接");
                this.socket.close({ code: 1000, reason: '录音完成' });
                this.socket = null;
                this.setData({ socketOpen: false });
            }

            // ===== 合并临时语句 =====
            // 录音结束时，将所有临时语句合并到最终结果
            Object.entries(this.tempUtterances).forEach(([idx, text]) => {
                if (text && text.trim()) {
                    this.utterances[parseInt(idx)] = text;
                }
            });
            this.tempUtterances = {};

            // 生成最终文本
            const finalText = this.utterances.filter(u => u).join('');
            this.setData({ userInput: finalText });
            console.log("📝 最终识别文本:", finalText.slice(0, 50));

            // 检查是否被取消
            if (this.isRecordingCancelled) {
                console.log("❌ 录音已取消,不上传语音");
                this.isRecordingCancelled = false;  // 重置标志位
                return;
            }

            // 保存录音文件路径待上传
            this.pendingVoicePath = tempFilePath;

            // 延迟发送（确保 UI 更新完成）
            setTimeout(() => {
                this.handleSend();
            }, 500);
        });

        // 录音错误回调
        this.recorderManager.onError((err) => {
            console.error("录音错误:", err);
        });
    },

    // ========================================================================
    // 用户交互处理
    // ========================================================================

    /**
     * 请求麦克风权限
     */
    requestMicPermission() {
        wx.authorize({
            scope: 'scope.record',
            success: () => {
                wx.showToast({ title: '麦克风已授权', icon: 'success' });
            },
            fail: () => {
                wx.showModal({
                    title: '提示',
                    content: '需要您的麦克风权限才能录音，请在设置中开启',
                    success: (res) => {
                        if (res.confirm) {
                            wx.openSetting();
                        }
                    }
                });
            }
        });
    },

    /**
     * 麦克风按钮点击处理
     * 
     * 根据当前状态切换：
     * - 空闲状态 → 开始录音
     * - 录音状态 → 停止录音并发送
     */
    handleMicToggle() {
        if (this.data.status === 'recording') {
            // 停止录音
            this.recorderManager.stop();
            clearInterval(this.data.timer);
            this.setData({ status: 'idle' });
            console.log("用户停止录音");
        } else {
            // 开始录音
            this.startRecordingLogic();
        }
    },

    /**
     * 取消录音
     * 
     * 停止录音但不发送内容，清空已识别的文字。
     */
    handleCancelRecording() {
        console.log("🚫 用户取消录音");

        // 设置取消标志位
        this.isRecordingCancelled = true;

        // 停止录音
        this.recorderManager.stop();

        // 清除计时器
        clearInterval(this.data.timer);

        // 关闭 ASR WebSocket
        if (this.socket) {
            this.socket.close({ code: 1000, reason: '用户取消' });
            this.socket = null;
            this.setData({ socketOpen: false });
        }

        // 重置状态
        this.setData({
            status: 'idle',
            userInput: '',
            recordingTime: '00:59'
        });

        // 清空 ASR 数据
        this.utterances = [];
        this.tempUtterances = {};
        this.indexOffset = 0;
    },

    /**
 * 测试功能：切换不同行数的测试文字
 * 
 * 每行16个字，生成1-6行的测试文字
 */
    handleSwitchToKeyboard() {
        const testTexts = [
            '这是一行测试文字啊', // 1行 (8字)
            '这是两行测试文字这是两行测试文字这是两行测试', // 2行 (24字)
            '这是三行测试文字这是三行测试文字这是三行测试文字这是三行测试文字这是三行测试', // 3行 (40字)
            '这是四行测试文字这是四行测试文字这是四行测试文字这是四行测试文字这是四行测试文字这是四行测试文字这是四行', // 4行 (56字)
            '这是五行测试文字这是五行测试文字这是五行测试文字这是五行测试文字这是五行测试文字这是五行测试文字这是五行测试文字这是五行测试文字这是五行', // 5行 (72字)
            '这是六行测试文字这是六行测试文字这是六行测试文字这是六行测试文字这是六行测试文字这是六行测试文字这是六行测试文字这是六行测试文字这是六行测试文字这是六行测试文字这是六行' // 6行 (88字)
        ];

        // 获取当前测试索引
        if (!this.data.testIndex) {
            this.setData({ testIndex: 0 });
        }

        // 切换到下一个测试文字
        const nextIndex = (this.data.testIndex + 1) % testTexts.length;
        this.setData({
            aiMessage: testTexts[nextIndex],
            testIndex: nextIndex,
            status: 'idle',
            scrollTop: Date.now() // 使用时间戳确保每次都是新值,触发滚动
        });

        wx.showToast({
            title: `测试：${nextIndex + 1}行文字`,
            icon: 'none',
            duration: 1000
        });
    },

    /**
     * 开始录音逻辑
     * 
     * 执行顺序：
     * 1. 重置ASR语句追踪状态
     * 2. 连接ASR WebSocket
     * 3. 等待连接建立
     * 4. 开始录音
     */
    startRecordingLogic() {
        console.log("开始录音逻辑...");

        // 先停止可能正在进行的录音
        try {
            this.recorderManager.stop();
            console.log("🛑 停止之前的录音");
        } catch (e) {
            // 如果没有录音在进行,会报错,忽略即可
        }

        // 清除计时器
        if (this.data.timer) {
            clearInterval(this.data.timer);
            this.setData({ timer: null });
        }

        // 如果 TTS 正在播放，停止播放
        if (this.chatSocket) {
            console.log("🛑 TTS 播放中，关闭对话 WebSocket");
            this.chatSocket.close();
            this.chatSocket = null;
        }

        // 停止 WebAudio 播放并清空队列
        if (this.audioCtx) {
            try {
                // 暂停并关闭音频上下文,停止所有已调度的音频
                this.audioCtx.suspend();
                this.audioCtx.close();
                console.log("🛑 停止 WebAudio 播放");

                // 重新创建音频上下文
                this.audioCtx = wx.createWebAudioContext();
                this.gainNode = this.audioCtx.createGain();
                this.gainNode.connect(this.audioCtx.destination);
                this.gainNode.gain.value = 1.0;
            } catch (e) {
                console.warn("WebAudio 停止失败:", e);
            }
            this.nextStartTime = 0;  // 重置播放时间
        }

        // 清空文本队列，防止后续显示
        if (this.textQueue) {
            this.textQueue = [];
            this.displayedText = '';
            console.log("🗑️ 清空文本队列");
        }

        // 重置 ASR 追踪状态
        this.utterances = [];
        this.tempUtterances = {};
        this.indexOffset = 0;

        // 连接 ASR WebSocket
        this.connectASRWebSocket();

        // 延迟启动录音，确保 WebSocket 已连接
        setTimeout(() => {
            if (this.data.socketOpen) {
                this.startRecording();
            } else {
                console.error("WebSocket 未连接，无法开始录音");
                wx.showToast({
                    title: '连接失败，请重试',
                    icon: 'none'
                });
            }
        }, 800);
    },

    /**
     * 开始录音
     * 
     * 配置录音参数并启动录音。
     * 参数说明：
     * - duration: 最大录音时长（毫秒）
     * - sampleRate: 采样率（16kHz适合语音识别）
     * - numberOfChannels: 声道数（单声道）
     * - encodeBitRate: 编码比特率
     * - format: 音频格式（PCM适合实时流传输）
     * - frameSize: 帧大小（KB），决定回调触发频率
     */
    startRecording() {
        this.setData({
            status: 'recording',
            seconds: 0,
            recordingTime: "00:59",
            userInput: ""
        });

        // 启动录音倒计时（60秒）
        this.data.timer = setInterval(() => {
            let s = this.data.seconds + 1;
            if (s >= 60) {
                clearInterval(this.data.timer);
                this.recorderManager.stop();
                return;
            }
            const minutes = Math.floor((60 - s) / 60);
            const secs = (60 - s) % 60;
            const formattedTime = `${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
            this.setData({
                seconds: s,
                recordingTime: formattedTime
            });
        }, 1000);

        // 录音配置
        const options = {
            duration: 60000,         // 最大60秒
            sampleRate: 16000,       // 16kHz采样率
            numberOfChannels: 1,     // 单声道
            encodeBitRate: 48000,    // 48kbps编码
            format: 'PCM',           // PCM裸音频格式
            frameSize: 6             // 约6KB/帧
        };

        // 设置音频来源为语音识别优化（如果支持）
        if (wx.canIUse('getRecorderManager.start.audioSource')) {
            options.audioSource = 'voice_recognition';
        }

        this.recorderManager.start(options);
    },

    // ========================================================================
    // 发送消息与对话
    // ========================================================================

    /**
     * 发送用户消息给AI
     * 
     * 将识别的文字发送到后端，开始AI对话。
     */
    handleSend() {
        const textToSend = this.data.userInput;
        if (!textToSend || textToSend.trim() === "") {
            wx.showToast({ title: '请先说话', icon: 'none' });
            return;
        }

        console.log("发送消息:", textToSend);
        // 注释掉状态切换，避免打断用户可能正在进行的下一轮录音
        // this.setData({ status: 'thinking' });

        // 连接对话WebSocket
        this.connectToChatSocket(textToSend);
    },

    /**
     * 连接对话WebSocket
     * 
     * 与后端建立WebSocket连接，进行流式对话。
     * 
     * 消息格式：
     * 发送: {messages: [{role: 'user', content: '...'}, ...]}
     * 接收: 
     *   - 文字: {type: 'text', content: '...'}
     *   - 音频: {type: 'audio', data: '<base64>'}
     *   - 完成: {type: 'text_finish'}
     *   - 错误: {type: 'error', message: '...'}
     * 
     * @param {string} fullTextPrompt - 用户本轮输入的完整文本
     */
    connectToChatSocket(fullTextPrompt) {
        const that = this;

        // 构建消息历史（包含本轮用户输入）
        const history = this.data.messages ? [...this.data.messages] : [];
        history.push({ role: "user", content: fullTextPrompt });

        // 在UI中添加AI回复占位符
        const newMsgList = [...history, { role: "assistant", content: "..." }];
        this.setData({
            messages: newMsgList,
            scrollTop: newMsgList.length * 100
        });

        const assistantMsgIndex = newMsgList.length - 1;

        // 关闭已有的对话连接 (v3.4.4: 增加安全性检查)
        if (this.chatSocket) {
            try {
                // 只有在非关闭状态下才尝试调用 close
                this.chatSocket.close({
                    success: () => console.log('✅ 旧对话连接已关闭'),
                    fail: (err) => console.log('⚠️ 旧对话连接关闭跳过 (可能已失效):', err.errMsg)
                });
            } catch (e) {
                console.error('❌ 关闭 Socket 异常:', e);
            }
            this.chatSocket = null; // 显式置空
        }

        // 创建对话WebSocket连接
        this.chatSocket = wx.connectSocket({
            url: getApp().globalData.baseUrl.replace('http://', 'ws://') + '/ws/interview',
            success: () => console.log('对话WebSocket连接中...')
        });

        // 设置超时保护 (30秒)
        this.thinkingTimeout = setTimeout(() => {
            if (this.data.status === 'thinking') {
                console.error('❌ 思考超时,自动恢复');
                this.setData({
                    status: 'idle',
                    aiMessage: '抱歉,我遇到了一些问题,请重试。'
                });
                if (this.chatSocket) {
                    this.chatSocket.close();
                    this.chatSocket = null;
                }
            }
        }, 30000);

        // ==================== 重置 WebAudio 状态 ====================
        if (this.audioCtx) {
            this.audioCtx.resume();
            this.nextStartTime = 0; // 重置调度时间
        }

        // ==================== 音频播放队列 ====================
        this.audioQueue = [];      // 待播放的音频文件路径队列
        this.isPlaying = false;    // 是否正在播放

        // ==================== 文本显示队列（逐字显示）====================
        this.textQueue = [];       // 待显示的文本chunk队列
        this.isDisplaying = false; // 是否正在显示文本
        this.displayedText = "";   // 已显示的文本

        // 累积的AI回复文本
        let accumulatedText = "";

        // 逐字显示函数（500ms间隔，慢10倍）
        const displayNextChunk = () => {
            if (this.textQueue.length === 0) {
                this.isDisplaying = false;
                return;
            }

            this.isDisplaying = true;
            const chunk = this.textQueue.shift();
            this.displayedText += chunk;

            // 更新UI显示
            const key = `messages[${assistantMsgIndex}].content`;
            if (this.data.messages && this.data.messages[assistantMsgIndex]) {
                this.setData({
                    [key]: this.displayedText,
                    aiMessage: this.displayedText,
                    scrollTop: Date.now()
                });
            }

            // 20ms后显示下一个chunk
            setTimeout(() => displayNextChunk(), 20);
        };

        // 连接成功后发送消息
        this.chatSocket.onOpen(() => {
            console.log('对话WebSocket已连接');

            // 获取全局 userId
            const app = getApp();
            const userId = app.globalData.userId || '2b8f1b66-b54a-4e4c-ac28-4bac4a05b8d2';  // 测试用户UUID

            console.log('发送消息（v3.3格式），userId:', userId, 'text:', fullTextPrompt);

            // 发送消息（v3.3格式）
            this.chatSocket.send({
                data: JSON.stringify({
                    user_id: userId,
                    text: fullTextPrompt,
                    has_voice: this.pendingVoicePath ? true : false
                })
            });
        });

        // ==================== 接收服务器消息 ====================
        this.chatSocket.onMessage((res) => {
            try {
                const data = JSON.parse(res.data);
                const app = getApp();
                const userId = app.globalData.userId || '2b8f1b66-b54a-4e4c-ac28-4bac4a05b8d2';

                // ----- 处理 session_id -----
                if (data.type === 'session_id') {
                    console.log("📍 收到 session_id:", data.session_id);
                    app.globalData.sessionId = data.session_id;
                }
                // ----- 处理 user_text_id -----
                else if (data.type === 'user_text_id') {
                    console.log("📍 收到 user_text_id:", data.text_id);
                    this.setData({ currentTextId: data.text_id });

                    // 收到 text_id 后上传挂起的语音文件
                    if (that.pendingVoicePath) {
                        that.uploadVoice(that.pendingVoicePath, userId, app.globalData.sessionId, data.text_id);
                    }
                }
                // ----- 处理 response_id -----
                else if (data.type === 'response_id') {
                    console.log("📍 收到 response_id:", data.response_id);
                }
                // ----- 处理文本流 -----
                else if (data.type === 'text') {
                    console.log("📝 收到文本:", data.content);

                    if (accumulatedText === "") {
                        this.setData({ status: 'thinking' });
                    }

                    accumulatedText += data.content;
                    this.textQueue.push(data.content);

                    if (!this.isDisplaying) {
                        displayNextChunk();
                    }
                }
                // ----- 处理音频数据 (PCM 模式 v3.4) -----
                else if (data.type === 'audio') {
                    // console.log("📦 收到 PCM 音频分片");
                    this.playPCMChunk(data.data);
                }
                // ----- 处理完成信号 -----
                else if (data.type === 'text_finish') {
                    console.log("✅ 文本流结束");
                    this.setData({ status: 'idle' });
                    // 清除超时定时器
                    if (this.thinkingTimeout) {
                        clearTimeout(this.thinkingTimeout);
                        this.thinkingTimeout = null;
                    }
                }
                // ----- 处理错误 -----
                else if (data.type === 'error') {
                    console.error("❌ 服务器错误:", data.message);
                    this.setData({ status: 'idle' });
                }
            } catch (e) {
                console.error("WebSocket解析错误:", e, res.data);
            }
        });

        // 连接关闭回调
        this.chatSocket.onClose(() => {
            console.log("对话WebSocket已关闭");
            // 清除超时定时器
            if (this.thinkingTimeout) {
                clearTimeout(this.thinkingTimeout);
                this.thinkingTimeout = null;
            }
        });

        // 连接错误回调
        this.chatSocket.onError((err) => {
            console.error("❌ 对话WebSocket错误:", err);
            this.setData({
                status: 'idle',
                aiMessage: '连接失败,请检查网络后重试。'
            });
            // 清除超时定时器
            if (this.thinkingTimeout) {
                clearTimeout(this.thinkingTimeout);
                this.thinkingTimeout = null;
            }
        });
    },

    // ========================================================================
    // 音频播放管理
    // ========================================================================

    /**
     * 播放下一段音频
     * 
     * 从队列中取出下一个音频文件播放。
     * 采用串行播放策略，确保音频按顺序播放。
     */
    playNextAudio() {
        // 安全检查：确保队列已初始化
        if (!this.audioQueue) {
            console.warn('⚠️ audioQueue 未初始化');
            return;
        }

        // 如果正在播放，等待当前音频结束
        if (this.isPlaying) {
            return;
        }

        // 队列为空，播放完成
        if (this.audioQueue.length === 0) {
            this.isPlaying = false;
            this.setData({ status: 'idle' });
            return;
        }

        // 取出下一个音频
        const audioSrc = this.audioQueue.shift();
        this.currentAudioPath = audioSrc;  // 保存路径用于后续清理

        // 开始播放
        this.isPlaying = true;
        this.setData({ status: 'talking' });
        console.log("▶️ 播放音频, 队列剩余:", this.audioQueue.length);

        this.player.src = audioSrc;

        // 防御：如果在 play 之前 player 被销毁或未就绪，try-catch
        try {
            if (!this.player) {
                this.initAudioPlayer();
                this.player.src = audioSrc;
            }
            this.player.play();
        } catch (e) {
            console.error("❌ 调用 player.play() 失败:", e);
            this.initAudioPlayer();
            this.isPlaying = false;
            this.playNextAudio();
        }
    },

    /**
     * 上传语音文件
     */
    uploadVoice(filePath, userId, sessionId, textId) {
        if (!filePath || !userId || !sessionId) {
            console.warn("❌ 上传语音参数缺失", { filePath, userId, sessionId });
            return;
        }

        console.log("📤 开始上传语音文件, textId:", textId);

        // 清空挂起路径，避免重复上传
        this.pendingVoicePath = null;

        wx.uploadFile({
            url: getApp().globalData.baseUrl + '/api/upload_voice',
            filePath: filePath,
            name: 'file',
            formData: {
                user_id: userId,
                session_id: sessionId,
                text_id: textId || ''
            },
            success: (res) => {
                console.log("✅ 语音上传结果:", res.data);
            },
            fail: (err) => {
                console.error("❌ 语音上传失败:", err);
            }
        });
    }
})
