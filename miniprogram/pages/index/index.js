Page({
    data: {
        showModal: false
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
