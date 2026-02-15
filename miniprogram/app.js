App({
    globalData: {
        // 本地开发地址 (日常开发使用)
        baseUrl: 'http://192.168.3.73:8000',
        // 云端服务器地址 (部署后使用)
        // baseUrl: 'http://62.234.150.82:8001',
        // 用户ID（登录后设置）
        userId: null,
        // 用户信息（登录后设置）
        userInfo: null,
        // 会话ID（对话时设置）
        sessionId: null
    },

    onLaunch: function () {
        console.log('App Launch')

        // 检查本地是否有 userId
        const userId = wx.getStorageSync('userId')
        const userInfo = wx.getStorageSync('userInfo')

        if (userId) {
            // 已登录，直接使用
            this.globalData.userId = userId
            this.globalData.userInfo = userInfo || null
            console.log('✅ 用户已登录:', userId)
        } else {
            console.log('⚠️ 用户未登录，等待用户操作触发登录')
            // 不再自动登录，由首页按钮触发
            // this.doWeChatLogin()
        }
    },

    /**
     * 执行微信登录
     */
    /**
     * 执行微信登录 (Promise 版本)
     * @returns {Promise} 返回包含 userId 的 Promise
     */
    doWeChatLogin: function () {
        const that = this
        return new Promise((resolve, reject) => {
            wx.login({
                success: (res) => {
                    if (res.code) {
                        console.log('📱 获取微信 code 成功:', res.code)

                        // 调用后端接口
                        wx.request({
                            url: that.globalData.baseUrl + '/api/wechat/login',
                            method: 'POST',
                            data: { code: res.code },
                            success: (response) => {
                                // 后端返回格式: { code: 0, data: { user_id: '...', user_info: {...} } }
                                if (response.data && response.data.data && response.data.data.user_id) {
                                    const userId = response.data.data.user_id
                                    const userInfo = response.data.data.user_info

                                    that.globalData.userId = userId
                                    that.globalData.userInfo = userInfo

                                    wx.setStorageSync('userId', userId)
                                    wx.setStorageSync('userInfo', userInfo)

                                    console.log('✅ 登录成功，用户ID:', userId)
                                    resolve(userId)
                                } else {
                                    console.error('❌ 登录失败：返回数据格式错误', response.data)
                                    reject(new Error('数据格式错误'))
                                }
                            },
                            fail: (error) => {
                                console.error('❌ 登录请求失败:', error)
                                reject(error)
                            }
                        })
                    } else {
                        console.error('❌ 获取微信 code 失败:', res.errMsg)
                        reject(new Error(res.errMsg))
                    }
                },
                fail: (error) => {
                    console.error('❌ wx.login 调用失败:', error)
                    reject(error)
                }
            })
        })
    }
})
