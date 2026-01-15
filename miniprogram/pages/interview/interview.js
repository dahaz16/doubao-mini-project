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
        aiMessage: "您好呀，今天就随便唠唠，说说您以前那些有意思的事儿呗。",

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
        messages: [],

        // ASR WebSocket连接状态
        socketOpen: false,

        // 音频文件计数器（用于生成唯一文件名，防止冲突）
        audioCounter: 0
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
        // 初始化对话历史（AI的开场白）
        this.setData({
            messages: [{ role: 'assistant', content: this.data.aiMessage }]
        });

        // ==================== 初始化音频播放器 ====================
        this.player = wx.createInnerAudioContext();
        this.player.onPlay(() => console.log('音频播放开始'));

        // 音频播放结束回调（只绑定一次，避免重复）
        this.player.onEnded(() => {
            console.log('音频播放结束');

            // 清理临时音频文件
            if (this.currentAudioPath && this.currentAudioPath.startsWith(wx.env.USER_DATA_PATH)) {
                wx.getFileSystemManager().unlink({
                    filePath: this.currentAudioPath,
                    success: () => console.log('🗑️ 临时文件已删除'),
                    fail: (err) => console.warn('删除临时文件失败:', err)
                });
            }

            // 标记播放结束，尝试播放下一段
            this.isPlaying = false;
            this.playNextAudio();
        });

        // 音频播放错误回调
        this.player.onError((err) => {
            console.error('音频播放错误:', err);
            this.isPlaying = false;
            this.playNextAudio();
        });

        // ==================== 初始化录音管理器 ====================
        this.initRecorderManager();

        // 注意：ASR WebSocket不在此处连接，而是在录音开始时按需连接
    },

    /**
     * 页面卸载时执行
     * 清理WebSocket连接
     */
    onUnload() {
        if (this.socket) {
            this.socket.close();
        }
        if (this.chatSocket) {
            this.chatSocket.close();
        }
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
        const wsUrl = 'ws://192.168.3.73:8000/ws/asr';

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
                    this.setData({ userInput: displayText });
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

            // 延迟发送（确保UI更新完成）
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
        this.recorderManager.stop();
        clearInterval(this.data.timer);
        this.setData({
            status: 'idle',
            userInput: '',
            recordingTime: '60'
        });
        console.log("录音已取消");
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
        // 重置ASR追踪状态
        this.utterances = [];
        this.tempUtterances = {};
        this.indexOffset = 0;

        // 连接ASR WebSocket
        console.log("🔌 为新录音连接ASR...");
        this.connectASRWebSocket();

        // 等待连接建立后开始录音
        setTimeout(() => {
            if (this.data.socketOpen) {
                this.startRecording();
            } else {
                console.error("❌ ASR连接失败");
                wx.showToast({ title: '连接失败，请重试', icon: 'none' });
                this.setData({ status: 'idle' });
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
            recordingTime: "60",
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
        this.setData({ status: 'thinking' });

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

        // 关闭已有的对话连接
        if (this.chatSocket) {
            console.log('关闭已有的对话连接');
            this.chatSocket.close();
        }

        // 创建对话WebSocket连接
        this.chatSocket = wx.connectSocket({
            url: 'ws://192.168.3.73:8000/ws/chat',
            success: () => console.log('对话WebSocket连接中...')
        });

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
                    status: 'idle',
                    scrollTop: Date.now()
                });
            }

            // 20ms后显示下一个chunk
            setTimeout(() => displayNextChunk(), 20);
        };

        // 连接成功后发送消息
        this.chatSocket.onOpen(() => {
            console.log('对话WebSocket已连接');
            this.chatSocket.send({
                data: JSON.stringify({ messages: history })
            });
        });

        // ==================== 接收服务器消息 ====================
        this.chatSocket.onMessage((res) => {
            try {
                const data = JSON.parse(res.data);

                // ----- 处理文本流 -----
                if (data.type === 'text') {
                    console.log("📝 收到文本:", data.content);

                    // 累积文本
                    if (accumulatedText === "") {
                        accumulatedText = data.content;
                    } else {
                        accumulatedText += data.content;
                    }

                    // 将chunk加入显示队列
                    this.textQueue.push(data.content);

                    // 如果当前没有在显示，启动显示
                    if (!this.isDisplaying) {
                        displayNextChunk();
                    }
                }
                // ----- 处理音频数据 -----
                else if (data.type === 'audio') {
                    console.log("📦 收到音频, 长度:", data.data.length);

                    // 将Base64转换为ArrayBuffer
                    const arrayBuffer = wx.base64ToArrayBuffer(data.data);

                    // 写入临时文件
                    const fs = wx.getFileSystemManager();
                    const tempFilePath = `${wx.env.USER_DATA_PATH}/audio_${Date.now()}_${this.data.audioCounter}.mp3`;
                    this.setData({ audioCounter: this.data.audioCounter + 1 });

                    fs.writeFile({
                        filePath: tempFilePath,
                        data: arrayBuffer,
                        encoding: 'binary',
                        success: () => {
                            console.log("✅ 音频文件已写入");
                            this.audioQueue.push(tempFilePath);
                            this.playNextAudio();
                        },
                        fail: (err) => {
                            console.error("❌ 音频文件写入失败:", err);
                        }
                    });
                }
                // ----- 处理完成信号 -----
                else if (data.type === 'text_finish') {
                    console.log("✅ 文本流结束");
                    // 音频会继续从队列中播放
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
        this.player.play();
    }
})
