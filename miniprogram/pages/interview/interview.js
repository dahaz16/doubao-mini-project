const app = getApp()
const recorderManager = wx.getRecorderManager()

Page({
    data: {
        status: 'idle', // idle, recording, thinking, talking
        aiMessage: "你好呀，可以给我继续讲讲当年在学校的事情吗？",
        userInput: "",
        recordingTime: "00:00",
        timer: null,
        seconds: 0,
        messages: [],
        socketOpen: false
    },

    onLoad() {
        this.setData({
            messages: [{ role: 'assistant', content: this.data.aiMessage }]
        });
        this.initSocket();
        this.initRecorder();
    },

    initSocket() {
        // Connect to Backend WebSocket
        if (!app.globalData.baseUrl) {
            console.error("BaseUrl not set");
            return;
        }

        // Use LAN IP for Real Device Preview
        const host = '192.168.3.103:8000';
        const wsUrl = `ws://${host}/ws/asr`;

        console.log("Connecting to WebSocket:", wsUrl);

        this.socket = wx.connectSocket({
            url: wsUrl,
            success: () => {
                this.logToUI('Connecting URL: ' + wsUrl);
            },
            fail: (err) => {
                this.logToUI('Connect Failed: ' + JSON.stringify(err));
            }
        });

        this.socket.onOpen(() => {
            console.log("WebSocket Connected");
            this.setData({ socketOpen: true });
        });

        this.socket.onMessage((res) => {
            console.log("ASR Message:", res.data);
            try {
                // If backend sends JSON
                const data = JSON.parse(res.data);
                if (data.text) {
                    this.setData({ userInput: data.text });
                }
            } catch (e) {
                // If backend just sends raw text string for ASR results
                this.setData({ userInput: res.data });
            }
        });

        this.socket.onClose(() => {
            console.log("WebSocket Closed");
            this.setData({ socketOpen: false });
        });

        this.socket.onError((err) => {
            console.error("WebSocket Error:", err);
        });
    },

    initRecorder() {
        recorderManager.onStart(() => {
            this.logToUI('Recorder Started');
        });

        // Real-time Frame Transmission
        recorderManager.onFrameRecorded((res) => {
            const { frameBuffer } = res;

            // Visual Feedback for User
            this.setData({
                micStatus: `🎤 录音中: 数据包 (${frameBuffer.byteLength} B)`
            });

            if (this.data.socketOpen) {
                wx.sendSocketMessage({
                    data: frameBuffer
                });
            } else {
                this.logToUI('Socket not open, frame dropped');
            }
        });

        recorderManager.onStop((res) => {
            this.logToUI(`Recorder Stopped. Size: ${res.fileSize}`);
            // Logic to handle fallback if no real-time response received
        });

        recorderManager.onError((err) => {
            this.logToUI(`Recorder Error: ${err.errMsg}`);
        });
    },

    logToUI(msg) {
        console.log(msg);
        const time = new Date().toTimeString().split(' ')[0];
        const logEntry = `[${time}] ${msg}`;
        // Fix: Use concat instead of spread syntax to avoid compilation error
        const currentLogs = this.data.debugLogs || [];
        const newLogs = [logEntry].concat(currentLogs).slice(0, 5);
        this.setData({ debugLogs: newLogs });
    },

    startRecording() {
        this.setData({
            status: 'recording',
            seconds: 0,
            recordingTime: "00:00",
            userInput: ""
        });

        // Start Timer
        this.data.timer = setInterval(() => {
            let s = this.data.seconds + 1;
            let min = Math.floor(s / 60).toString().padStart(2, '0');
            let sec = (s % 60).toString().padStart(2, '0');
            this.setData({
                seconds: s,
                recordingTime: `${min}:${sec}`
            });
        }, 1000);

        // Start Recorder (Settings optimized for ASR)
        const options = {
            duration: 60000,
            sampleRate: 16000, // Standard for ASR
            numberOfChannels: 1,
            encodeBitRate: 48000,
            format: 'mp3', // Switch to MP3 for better compatibility
            frameSize: 1 // KB: 1KB approx 32ms. Ensures frequent callbacks.
        }
        recorderManager.start(options);
    },

    cancelRecording() {
        recorderManager.stop();
        clearInterval(this.data.timer);
        this.setData({ status: 'idle', userInput: "" });
    },

    finishRecording() {
        recorderManager.stop();
        clearInterval(this.data.timer);

        this.setData({ status: 'thinking' });

        // Delay slightly to ensure backend processed final chunks
        setTimeout(() => {
            const finalInput = this.data.userInput;

            if (!finalInput || finalInput.trim() === "") {
                // Mock Fallback if ASR didn't work (for user testing when no microphone)
                // Or better: prompt error.
                // wx.showToast({ title: '没有听到声音哦', icon: 'none' });
                // this.setData({ status: 'idle' });
                // return;

                // DEV MODE: If silent, use a default fallback to keep flow moving
                console.log("No input, using fallback for dev flow");
                this.setData({ userInput: "（未检测到语音，自动填充测试文本）" });
            }

            // Call Backend Logic
            // We use the current display text as the input.
            const textToSend = this.data.userInput || "（无声）";
            const newHistory = this.data.messages.concat({ role: 'user', content: textToSend });
            this.setData({ messages: newHistory });

            this.getAIResponse(newHistory);
        }, 1000);
    },

    getAIResponse(messages) {
        wx.request({
            url: 'http://192.168.3.103:8000/chat',
            method: 'POST',
            data: {
                messages: messages
            },
            success: (res) => {
                if (res.statusCode === 200) {
                    const reply = res.data.reply;
                    const audioUrl = res.data.audio_url;

                    const updatedHistory = messages.concat({ role: 'assistant', content: reply });
                    this.setData({
                        aiMessage: reply,
                        status: 'idle',
                        messages: updatedHistory,
                        userInput: ""
                    });

                    if (audioUrl) {
                        this.playResponse(audioUrl);
                    }
                } else {
                    wx.showToast({ title: 'AI 出错啦', icon: 'none' });
                    this.setData({ status: 'idle' });
                }
            },
            fail: (err) => {
                console.error(err);
                wx.showToast({ title: '网络连接失败', icon: 'none' });
                this.setData({ status: 'idle' });
            }
        });
    },

    playAudio(url) {
        if (!url) return;

        const innerAudioContext = wx.createInnerAudioContext({
            useWebAudioImplement: false
        });
        innerAudioContext.src = url;

        innerAudioContext.play();

        innerAudioContext.onPlay(() => {
            console.log('Start playing audio');
        });
        innerAudioContext.onError((res) => {
            console.error('Audio Play Error', res);
        });
    }
})
