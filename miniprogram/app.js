App({
    globalData: {
        // 使用本机回环地址，适合模拟器测试
        baseUrl: 'http://127.0.0.1:8000'
    },
    onLaunch: function () {
        console.log('App Launch')
    }
})
