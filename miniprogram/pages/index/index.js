Page({
    data: {
        showModal: false,
        isLowEnd: false
    },

    onLoad() {
        // 检测设备性能
        this.checkDevicePerformance();
    },

    /**
     * 检测设备性能，决定是否使用静态背景
     */
    checkDevicePerformance() {
        try {
            const systemInfo = wx.getSystemInfoSync();
            const { platform, benchmarkLevel } = systemInfo;

            // iOS 设备通常性能较好，使用动画
            if (platform === 'ios') {
                this.setData({ isLowEnd: false });
                return;
            }

            // 微信提供的性能等级：-1=未知, 0=低端, 1=中端, 2=高端
            if (benchmarkLevel !== undefined && benchmarkLevel <= 0) {
                this.setData({ isLowEnd: true });
                console.log('[性能检测] 低端设备，使用静态背景');
            } else {
                this.setData({ isLowEnd: false });
                console.log('[性能检测] 性能良好，使用动画背景');
            }
        } catch (error) {
            console.error('[性能检测] 失败，默认使用动画背景', error);
            this.setData({ isLowEnd: false });
        }
    },

    /**
     * 点击"开始讲述"按钮
     */
    onStartInterview() {
        wx.navigateTo({
            url: '/pages/interview/interview'
        });
    },

    /**
     * 点击"查看回忆"按钮
     */
    onViewMemories() {
        this.setData({ showModal: true });
    },

    /**
     * 关闭弹窗
     */
    onCloseModal() {
        this.setData({ showModal: false });
    },

    /**
     * 阻止事件冒泡（点击弹窗内容区不关闭）
     */
    stopPropagation() {
        // 空函数，仅用于阻止冒泡
    }
});
