Page({
    data: {
        inputValue: '',
        result: '',
        isLoading: false
    },

    onInput: function (e) {
        this.setData({
            inputValue: e.detail.value
        })
    },

    onSummarize: function () {
        const text = this.data.inputValue;
        if (!text.trim()) {
            wx.showToast({
                title: '请输入内容',
                icon: 'none'
            });
            return;
        }

        this.setData({ isLoading: true, result: '' });

        wx.request({
            url: getApp().globalData.baseUrl + '/summarize', // 使用全局配置的局域网地址
            method: 'POST',
            header: {
                'content-type': 'application/json'
            },
            data: {
                text: text
            },
            success: (res) => {
                console.log('API Success:', res);
                if (res.statusCode === 200) {
                    this.setData({
                        result: res.data.ai_summary
                    });
                } else {
                    wx.showToast({
                        title: '请求失败: ' + res.statusCode,
                        icon: 'none'
                    });
                }
            },
            fail: (err) => {
                console.error('API Fail:', err);
                wx.showToast({
                    title: '网络请求失败，请检查后端是否启动',
                    icon: 'none'
                });
            },
            complete: () => {
                this.setData({ isLoading: false });
            }
        });
    }
})
