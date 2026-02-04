Page({
    data: {
        showModal: false,
        showAuthModal: false,
        avatarUrl: '',     // 临时/选中的头像路径
        nickname: ''       // 输入的昵称
    },

    /**
     * 点击"开始讲述"按钮
     */
    async onStartInterview() {
        await this.handleUserAction(this.navigateToInterview)
    },

    /**
     * 点击"查看回忆"按钮
     */
    async onViewMemories() {
        await this.handleUserAction(() => {
            this.setData({ showModal: true });
        })
    },

    /**
     * 统一处理用户点击动作
     * 1. 检查登录
     * 2. 检查授权
     * 3. 执行后续动作
     */
    async handleUserAction(callback) {
        const app = getApp()

        // 1. 检查登录
        if (!app.globalData.userId) {
            wx.showLoading({ title: '登录中', mask: true })
            try {
                await app.doWeChatLogin()
                wx.hideLoading()
            } catch (error) {
                wx.hideLoading()
                wx.showToast({ title: '登录失败，请重试', icon: 'none' })
                return
            }
        }

        // 2. 检查授权信息 (头像和昵称) - [暂时禁用]
        /*
        const userInfo = app.globalData.userInfo
        if (!userInfo || !userInfo.wechat_nickname || !userInfo.wechat_avatar_url) {
            console.log("⚠️ 用户信息不完整，显示授权弹窗")
            this.setData({ showAuthModal: true })
            this.pendingAction = callback // 保存后续动作
            return
        }
        */

        // 3. 执行后续动作
        callback()
    },

    /**
     * 选择头像
     */
    onChooseAvatar(e) {
        const { avatarUrl } = e.detail
        console.log('选中的头像:', avatarUrl)
        this.setData({ avatarUrl })
    },

    /**
     * 昵称输入
     */
    onNicknameInput(e) {
        this.setData({ nickname: e.detail.value })
    },

    onNicknameChange(e) {
        this.setData({ nickname: e.detail.value })
    },

    /**
     * 提交授权信息
     */
    async onSubmitAuth() {
        const { avatarUrl, nickname } = this.data
        if (!avatarUrl || !nickname) {
            wx.showToast({ title: '请完善信息', icon: 'none' })
            return
        }

        wx.showLoading({ title: '保存中...', mask: true })
        const app = getApp()

        try {
            // 1. 上传头像
            const uploadRes = await new Promise((resolve, reject) => {
                wx.uploadFile({
                    url: app.globalData.baseUrl + '/api/upload_avatar',
                    filePath: avatarUrl,
                    name: 'file',
                    formData: {
                        'user_id': app.globalData.userId
                    },
                    success: (res) => {
                        try {
                            const data = JSON.parse(res.data)
                            if (data.code === 0) resolve(data.data.avatar_url)
                            else reject(new Error(data.message))
                        } catch (e) {
                            reject(e)
                        }
                    },
                    fail: reject
                })
            })

            console.log('✅ 头像上传成功:', uploadRes)

            // 2. 更新用户信息
            await new Promise((resolve, reject) => {
                wx.request({
                    url: app.globalData.baseUrl + '/api/wechat/update_userinfo',
                    method: 'POST',
                    data: {
                        user_id: app.globalData.userId,
                        nickname: nickname,
                        avatar_url: uploadRes
                    },
                    success: (res) => {
                        if (res.data.code === 0) resolve(res.data)
                        else reject(new Error(res.data.message))
                    },
                    fail: reject
                })
            })

            console.log('✅ 用户信息更新成功')

            // 3. 更新本地 globalData 和缓存
            const newUserInfo = app.globalData.userInfo || {}
            newUserInfo.wechat_nickname = nickname
            newUserInfo.wechat_avatar_url = uploadRes

            app.globalData.userInfo = newUserInfo
            wx.setStorageSync('userInfo', newUserInfo)

            // 4. 关闭弹窗并执行后续
            wx.hideLoading()
            this.setData({ showAuthModal: false })

            if (this.pendingAction) {
                this.pendingAction()
                this.pendingAction = null
            }

        } catch (error) {
            wx.hideLoading()
            console.error('授权失败:', error)
            wx.showToast({ title: '保存失败，请重试', icon: 'none' })
        }
    },

    /**
     * 跳转到采访页
     */
    navigateToInterview() {
        wx.navigateTo({
            url: '/pages/interview/interview'
        })
    },

    /**
     * 关闭弹窗
     */
    onCloseModal() {
        this.setData({ showModal: false });
    },

    /**
     * 阻止事件冒泡
     */
    stopPropagation() { }
});
