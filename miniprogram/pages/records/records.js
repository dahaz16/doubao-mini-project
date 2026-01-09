Page({
    data: {
        records: [],
        isLoading: true
    },

    onShow: function () {
        this.fetchRecords();
    },

    fetchRecords: function () {
        wx.showLoading({ title: '加载中' });
        wx.request({
            url: getApp().globalData.baseUrl + '/records',
            method: 'GET',
            success: (res) => {
                if (res.statusCode === 200) {
                    this.setData({
                        records: res.data
                    });
                }
            },
            fail: (err) => {
                console.error('Fetch records failed', err);
                wx.showToast({
                    title: '加载失败',
                    icon: 'none'
                });
            },
            complete: () => {
                wx.hideLoading();
                this.setData({ isLoading: false });
            }
        });
    }
})
