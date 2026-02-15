const app = getApp();

Component({
    properties: {
        visible: {
            type: Boolean,
            value: false,
            observer: function (newVal) {
                if (newVal) {
                    // 每次打开弹窗清空数据
                    this.resetData();
                } else {
                    this.stopRecordingLogic();
                }
            }
        },
        userId: {
            type: String,
            value: '',
            observer: function (newVal, oldVal) {
                console.log('[FeedbackModal] userId changed:', oldVal, '->', newVal);
            }
        }
    },

    data: {
        feedbackText: '', // 当前展示的总文本
        isRecording: false,
        hasRecorded: false, // 是否已有录音/内容
        recordingDuration: '00:00',
        recordingDuration: '00:00',
        audioFilePaths: [],
        uploadedVoiceUrl: null,
        canSubmit: false,

        // 内部状态
        socketOpen: false,
        timer: null,
        seconds: 0,
        recordingSessionId: 0
    },

    lifetimes: {
        created() {
            this.utterances = {};
            this.currentLocalIndex = 0;
            this.pendingAudioFrames = [];
        },
        detached() {
            this.stopRecordingLogic();
        }
    },

    methods: {
        // ==========================================
        // UI 交互
        // ==========================================

        onCancel() {
            this.stopRecordingLogic();
            this.triggerEvent('close');
            // resetData 已在 observer 中处理，这里只触发关闭即可，但关闭会触发 observer(false)，那是停止录音逻辑。
            // 实际上 observer(true) 才会清空。所以这里不用手动清空，下次打开会自动清空。
        },

        checkCanSubmit() {
            const text = this.data.feedbackText ? this.data.feedbackText.trim() : '';
            const hasAudio = this.data.audioFilePaths && this.data.audioFilePaths.length > 0;

            // 用户要求：如果没有文字（ASR未识别到或未输入），即使有录音文件也不让提交
            // 防止误触空录音
            const canSubmit = text.length > 0;

            this.setData({ canSubmit: canSubmit });
        },

        async onSubmit() {
            console.log("[Feedback] onSubmit called");

            const text = this.data.feedbackText ? this.data.feedbackText.trim() : '';
            const hasAudio = this.data.audioFilePaths && this.data.audioFilePaths.length > 0;

            if (!text) {
                console.warn("[Feedback] Submit blocked: no text content");
                return;
            }

            // 获取 userId...
            let userId = this.properties.userId;
            if (!userId) {
                userId = app.globalData.userId || wx.getStorageSync('userId');
            }

            if (!userId) {
                wx.showToast({ title: '用户ID丢失,请重新登录', icon: 'none' });
                return;
            }

            // 用户要求：不要 Loading 动画，改为 Toast 提示
            wx.showToast({ title: '提交中...', icon: 'none', duration: 20000 }); // 长时间显示直到成功/失败覆盖

            try {
                let voiceUrl = null;

                // 并发上传所有录音
                if (hasAudio) {
                    console.log("正在上传录音文件...", this.data.audioFilePaths);
                    try {
                        const uploadPromises = this.data.audioFilePaths.map(path => this.uploadAudio(path));
                        const urls = await Promise.all(uploadPromises);
                        console.log("所有录音上传成功:", urls);
                        // 转换为 JSON 字符串存入
                        voiceUrl = JSON.stringify(urls);
                    } catch (e) {
                        console.error("部分录音上传失败", e);
                        wx.hideToast(); // 隐藏提交中
                        wx.showToast({ title: '录音上传失败', icon: 'none' });
                        return;
                    }
                }

                // 提交反馈
                await new Promise((resolve, reject) => {
                    const submitData = {
                        user_id: userId,
                        feedback_content: text || '(无文本内容)',
                        feedback_voice_url: voiceUrl
                    };

                    wx.request({
                        url: app.globalData.baseUrl + '/api/feedback/submit',
                        method: 'POST',
                        data: submitData,
                        success: (res) => {
                            if (res.data.code === 200) resolve(res.data);
                            else reject(new Error(res.data.message || '提交失败'));
                        },
                        fail: reject
                    });
                });

                wx.hideToast(); // 隐藏提交中
                wx.showToast({ title: '反馈已提交，感谢！', icon: 'none' });

                setTimeout(() => {
                    this.triggerEvent('close');
                }, 1500);

            } catch (err) {
                console.error("提交反馈失败:", err);
                wx.hideLoading();
                wx.showToast({ title: '提交失败,请重试', icon: 'none' });
            }
        },

        // ==========================================
        // 录音逻辑 (重构)
        // ==========================================

        onStartRecording() {
            this.startRecordingProcess();
        },

        onCancelRecording() {
            const innerAudioContext = wx.createInnerAudioContext();
            innerAudioContext.src = '/images/sounds/cancel_recording.wav';
            innerAudioContext.play();

            this.stopRecordingLogic();
            //以此取消本次录音，不保存到 audioFilePaths
            this.setData({
                isRecording: false,
                // hasRecorded 保持不变（如果之前有录音，依然算有）
                feedbackText: this.originalText || ''
            });
            this.checkCanSubmit();
        },

        onConfirmRecording() {
            if (!this.data.isRecording) return;

            const innerAudioContext = wx.createInnerAudioContext();
            innerAudioContext.src = '/images/sounds/cancel_recording.wav'; // 用户要求播放此音效
            innerAudioContext.play();

            this.stopRecordingLogic();
        },

        onStopRecording() {
            if (!this.data.isRecording) return;
            this.stopRecordingLogic();
        },

        initRecorder() {
            if (this.recorderManager) return;
            this.recorderManager = wx.getRecorderManager();

            this.recorderManager.onStart(() => {
                console.log('Feedback: 录音开始');
            });

            this.recorderManager.onFrameRecorded((res) => {
                const { frameBuffer } = res;
                if (this.data.socketOpen && this.socket) {
                    if (this.pendingAudioFrames.length > 0) {
                        this.pendingAudioFrames.forEach(frame => this.socket.send({ data: frame }));
                        this.pendingAudioFrames = [];
                    }
                    this.socket.send({ data: frameBuffer });
                } else {
                    this.pendingAudioFrames.push(frameBuffer);
                }
            });

            this.recorderManager.onStop((res) => {
                console.log('Feedback: 录音结束', res);
                const { tempFilePath } = res;

                // 将新录音加入数组
                const newPaths = [...this.data.audioFilePaths, tempFilePath];

                this.setData({
                    isRecording: false,
                    hasRecorded: true,
                    audioFilePaths: newPaths
                });
                this.checkCanSubmit();

                if (this.data.timer) {
                    clearInterval(this.data.timer);
                    this.setData({ timer: null });
                }

                if (this.socket) {
                    this.socket.close();
                    this.socket = null;
                    this.setData({ socketOpen: false });
                }

                // 此次修改移除自动上传，统一在 Submit 时上传

                // 整理最终文本
                const indices = Object.keys(this.utterances).map(k => parseInt(k)).sort((a, b) => a - b);
                const finalText = indices.map(i => this.utterances[i]).join('');
                const previousText = this.originalText || '';
                const separator = (previousText && finalText) ? '\n' : '';
                const newTotalText = previousText + separator + finalText;
                this.setData({ feedbackText: newTotalText });
                this.checkCanSubmit();
            });
            // Error handler...
            this.recorderManager.onError((err) => {
                if (err.errMsg && err.errMsg.includes("recorder not start")) return;
                this.stopRecordingLogic();
                wx.showToast({ title: '录音失败', icon: 'none' });
            });
        },

        startRecordingProcess() {
            this.initRecorder();

            const innerAudioContext = wx.createInnerAudioContext();
            innerAudioContext.src = '/images/sounds/start_recording.wav';
            innerAudioContext.play();

            this.originalText = this.data.feedbackText || '';
            this.utterances = {};
            this.currentLocalIndex = 0;
            this.pendingAudioFrames = [];
            this.recordingSessionId++;
            this.setData({ uploadedVoiceUrl: null });

            this.connectASR();

            const options = {
                duration: 60000,
                sampleRate: 16000,
                numberOfChannels: 1,
                encodeBitRate: 48000,
                format: 'PCM',
                frameSize: 6
            };
            this.recorderManager.start(options);

            const TOTAL_SECONDS = 60;
            this.setData({
                isRecording: true,
                seconds: 0,
                recordingTime: "00:59"
            });
            this.checkCanSubmit();

            this.data.timer = setInterval(() => {
                let s = this.data.seconds + 1;
                let remaining = TOTAL_SECONDS - s;
                if (remaining < 0) {
                    this.onStopRecording();
                    return;
                }
                // 格式化 mm:ss (e.g. 00:59, 00:09)
                const mins = Math.floor(remaining / 60);
                const secs = remaining % 60;
                const timeStr = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

                this.setData({
                    seconds: s,
                    recordingTime: timeStr
                });
            }, 1000);
        },

        stopRecordingProcess() {
            if (this.recorderManager) {
                try { this.recorderManager.stop(); } catch (e) { }
            }
        },

        stopRecordingLogic() {
            if (this.recorderManager) {
                try { this.recorderManager.stop(); } catch (e) { }
            }
            if (this.socket) {
                this.socket.close();
                this.socket = null;
            }
            if (this.data.timer) {
                clearInterval(this.data.timer);
                this.setData({ timer: null });
            }
            this.setData({ isRecording: false });
        },

        connectASR() {
            // ... keeping existing implementation ...
            // Re-implementing briefly to ensure context is kept 
            if (this.socket) this.socket.close();
            let baseUrl = app.globalData.baseUrl;
            if (baseUrl.startsWith('http://')) {
                baseUrl = baseUrl.replace('http://', '');
            } else if (baseUrl.startsWith('https://')) {
                baseUrl = baseUrl.replace('https://', '');
            }
            const wsProtocol = app.globalData.baseUrl.startsWith('https') ? 'wss://' : 'ws://';
            const wsUrl = `${wsProtocol}${baseUrl}/ws/asr`;

            this.socket = wx.connectSocket({ url: wsUrl });
            this.socket.onOpen(() => this.setData({ socketOpen: true }));
            this.socket.onMessage((res) => {
                try {
                    const data = JSON.parse(res.data);
                    if (data.text) {
                        const text = data.text;
                        const isFinal = data.is_final;
                        this.utterances[this.currentLocalIndex] = text;
                        if (isFinal) this.currentLocalIndex++;
                        const indices = Object.keys(this.utterances).map(k => parseInt(k)).sort((a, b) => a - b);
                        const currentRunningText = indices.map(i => this.utterances[i]).join('');

                        const newText = (this.originalText || '') + currentRunningText;
                        this.setData({ feedbackText: newText });
                        // 实时更新时也可以检查
                        this.checkCanSubmit();
                    }
                } catch (e) { console.error(e); }
            });
        },

        uploadAudio(filePath) {
            return new Promise((resolve, reject) => {
                wx.uploadFile({
                    url: app.globalData.baseUrl + '/api/upload_feedback_audio',
                    filePath: filePath,
                    name: 'file',
                    formData: { 'user_id': this.data.userId },
                    success: (res) => {
                        try {
                            const data = JSON.parse(res.data);
                            if (data.code === 200) resolve(data.data.voice_url);
                            else reject(new Error(data.message));
                        } catch (e) { reject(e); }
                    },
                    fail: (err) => reject(err)
                });
            });
        },

        resetData() {
            this.setData({
                feedbackText: '',
                isRecording: false,
                hasRecorded: false,
                recordingDuration: '00:00',
                audioFilePaths: [], // 改为数组
                uploadedVoiceUrl: null,
                seconds: 0,
                canSubmit: false
            });
            this.utterances = {};
            this.currentLocalIndex = 0;
            this.stopRecordingLogic();
        }
    }
});
