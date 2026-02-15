Page({
    data: {
        userId: '',


        // 写作状态
        writingStatus: {
            ready: false,
            is_first_time: false,
            words_count: 0,
            threshold: 0,
            writing_state: 0  // 0=pending, 1=writing
        },

        // 文章数据
        articles: [],
        hasArticles: false,

        // 分页相关
        currentPage: 1,
        pageSize: 500,  // 每页500字
        totalPages: 1,
        displayedArticles: [],

        // 轮询相关
        pollingTimer: null,
        isPolling: false,

        // 首次写作自动触发标记(避免重复触发)
        hasAutoTriggered: false,

        // 导航栏布局信息
        navTop: 40,  // 默认值
        navHeight: 32 // 默认值
    },

    onLoad() {
        const app = getApp();
        this.setData({
            userId: app.globalData.userId
        });

        this.loadPageData();

        // 计算导航栏位置 (适配胶囊按钮)
        const menuButton = wx.getMenuButtonBoundingClientRect();
        this.setData({
            navTop: menuButton.top,
            navHeight: menuButton.height
        });
    },

    onShow() {
        // 页面显示时刷新数据
        if (this.data.userId) {
            this.loadPageData();
        }
    },

    onUnload() {
        // 页面卸载时清除轮询
        this.stopPolling();
    },

    onPullDownRefresh() {
        // 下拉刷新
        this.loadPageData().then(() => {
            wx.stopPullDownRefresh();
        });
    },

    /**
     * 加载页面数据
     */
    async loadPageData() {
        console.log('[Story] 📥 开始加载页面数据, userId:', this.data.userId);

        // 检查 userId 是否存在
        if (!this.data.userId) {
            console.error('[Story] ❌ userId 为空,无法加载数据');

            wx.showToast({
                title: '用户信息缺失,请重新登录',
                icon: 'none'
            });
            return;
        }

        wx.showToast({
            title: '加载中',
            icon: 'none',
            duration: 2000
        });

        try {
            console.log('[Story] 🔄 开始并行请求 API...');
            // 并行请求写作状态和文章数据
            const [statusRes, articlesRes] = await Promise.all([
                this.getWritingStatus(),
                this.getArticles()
            ]);
            console.log('[Story] ✅ API 请求完成', { statusRes, articlesRes });

            // 处理写作状态
            if (statusRes && statusRes.code === 0) {
                this.setData({
                    writingStatus: statusRes.data
                });

                // 如果正在写作，开始轮询
                if (statusRes.data.writing_state === 1) {
                    this.startPolling();
                } else {
                    this.stopPolling();
                }
            }

            // 处理文章数据
            if (articlesRes && articlesRes.code === 0) {
                const articles = articlesRes.data.articles || [];
                this.setData({
                    articles: articles,
                    hasArticles: articles.length > 0
                });

                // 计算分页
                this.calculatePagination();
            }

            // 首次写作自动触发判断
            if (statusRes && statusRes.code === 0) {
                const { is_first_time, ready, writing_state } = statusRes.data;

                console.log('[Story] 首次写作检查:', { is_first_time, ready, writing_state, hasAutoTriggered: this.data.hasAutoTriggered });

                // 条件:首次 && 准备好 && 未在写作 && 未自动触发过
                if (is_first_time && ready && writing_state === 0 && !this.data.hasAutoTriggered) {
                    console.log('[Story] ✅ 满足首次写作条件,自动触发写作');
                    this.setData({ hasAutoTriggered: true });

                    // 延迟 500ms 触发,避免 UI 闪烁
                    setTimeout(() => {
                        this.onStartWriting();
                    }, 500);
                }
            }

        } catch (error) {
            console.error('加载数据失败:', error);
            wx.showToast({
                title: '加载失败，请重试',
                icon: 'none'
            });
        } finally {
            wx.hideToast();
        }
    },

    /**
     * 获取写作状态
     */
    getWritingStatus() {
        const app = getApp();
        return new Promise((resolve, reject) => {
            wx.request({
                url: `${app.globalData.baseUrl}/api/writing/status`,
                method: 'GET',
                data: {
                    user_id: this.data.userId
                },
                success: (res) => {
                    resolve(res.data);
                },
                fail: reject
            });
        });
    },

    /**
     * 获取文章列表
     */
    getArticles() {
        const app = getApp();
        return new Promise((resolve, reject) => {
            wx.request({
                url: `${app.globalData.baseUrl}/api/memoir/articles`,
                method: 'GET',
                data: {
                    user_id: this.data.userId
                },
                success: (res) => {
                    resolve(res.data);
                },
                fail: reject
            });
        });
    },

    /**
     * 触发写作任务
     */
    async onStartWriting() {
        console.log('[Story] 🚀 触发写作任务');



        const app = getApp();

        // 发起 trigger 请求,但不等待返回(fire-and-forget)
        // 因为写作可能需要几分钟,wx.request 会超时
        wx.request({
            url: `${app.globalData.baseUrl}/api/writing/trigger`,
            method: 'POST',
            data: {
                user_id: this.data.userId
            },
            timeout: 120000,  // 120s 超时
            success: (res) => {
                console.log('[Story] Trigger 响应:', res.data);
            },
            fail: (error) => {
                console.warn('[Story] Trigger 请求失败(可能超时,但写作可能仍在进行):', error);
            }
        });

        // 立即隐藏 loading,刷新页面
        setTimeout(() => {
            wx.showToast({
                title: '写作任务已启动',
                icon: 'none',
                duration: 2000
            });

            // 刷新页面数据,此时 writing_state 应为 1
            this.loadPageData();
        }, 1000);
    },

    /**
     * 计算分页
     */
    calculatePagination() {
        const { articles } = this.data;
        if (!articles || articles.length === 0) {
            this.setData({
                totalPages: 1,
                currentPage: 1,
                displayedArticles: []
            });
            return;
        }

        // 按章节分组
        const chapters = this.groupByChapter(articles);

        // 计算总字数
        let totalWords = 0;
        articles.forEach(article => {
            totalWords += (article.section_name || '').length;
            totalWords += (article.section_content || '').length;
        });

        // 计算总页数
        const totalPages = Math.ceil(totalWords / this.data.pageSize);

        this.setData({
            totalPages: totalPages,
            currentPage: 1,
            displayedArticles: this.getPageArticles(chapters, 1)
        });
    },

    /**
     * 按章节分组
     */
    groupByChapter(articles) {
        const chapterMap = new Map();

        articles.forEach(article => {
            const chapterId = article.chapter_id;
            if (!chapterMap.has(chapterId)) {
                chapterMap.set(chapterId, {
                    chapter_id: chapterId,
                    chapter_name: article.chapter_name,
                    chapter_sort_num: article.chapter_sort_num || 0,
                    sections: []
                });
            }

            chapterMap.get(chapterId).sections.push({
                section_id: article.section_id,
                section_name: article.section_name,
                section_content: article.section_content,
                section_sort_num: article.section_sort_num || 0
            });
        });

        // 转换为数组并排序
        const chapters = Array.from(chapterMap.values());
        chapters.sort((a, b) => a.chapter_sort_num - b.chapter_sort_num);

        // 对每个章节的sections排序
        chapters.forEach(chapter => {
            chapter.sections.sort((a, b) => a.section_sort_num - b.section_sort_num);
        });

        return chapters;
    },

    /**
     * 获取指定页的文章
     */
    getPageArticles(chapters, page) {
        const startIndex = (page - 1) * this.data.pageSize;
        const endIndex = page * this.data.pageSize;

        let currentLength = 0;
        const result = [];

        for (const chapter of chapters) {
            const chapterData = {
                chapter_id: chapter.chapter_id,
                chapter_name: chapter.chapter_name,
                chapter_sort_num: chapter.chapter_sort_num,
                sections: []
            };

            for (const section of chapter.sections) {
                const sectionLength = (section.section_name || '').length +
                    (section.section_content || '').length;

                // 如果当前内容在显示范围内
                if (currentLength + sectionLength > startIndex && currentLength < endIndex) {
                    chapterData.sections.push(section);
                }

                currentLength += sectionLength;

                // 如果已经超出范围，停止
                if (currentLength >= endIndex) {
                    break;
                }
            }

            if (chapterData.sections.length > 0) {
                result.push(chapterData);
            }

            if (currentLength >= endIndex) {
                break;
            }
        }

        return result;
    },

    /**
     * 加载更多（下一页）
     */
    onLoadMore() {
        const { currentPage, totalPages, articles } = this.data;

        if (currentPage >= totalPages) {
            return;
        }

        const nextPage = currentPage + 1;
        const chapters = this.groupByChapter(articles);
        const newArticles = this.getPageArticles(chapters, nextPage);

        this.setData({
            currentPage: nextPage,
            displayedArticles: [...this.data.displayedArticles, ...newArticles]
        });
    },

    /**
     * 开始轮询写作状态
     */
    startPolling() {
        if (this.data.isPolling) {
            return;
        }

        this.setData({ isPolling: true });

        // 每 3 秒轮询一次
        this.data.pollingTimer = setInterval(async () => {
            console.log('[Story] 🔄 轮询写作状态...');
            try {
                const res = await this.getWritingStatus();

                if (res && res.code === 0) {
                    const oldState = this.data.writingStatus.writing_state;
                    const newState = res.data.writing_state;

                    this.setData({
                        writingStatus: res.data
                    });

                    // 如果从写作中变为完成
                    if (oldState === 1 && newState === 0) {
                        console.log('[Story] ✅ 写作完成! oldState:', oldState, 'newState:', newState);
                        this.stopPolling();

                        // 显示完成提示
                        wx.showToast({
                            title: '我写完啦！更新中…',
                            icon: 'none',
                            duration: 2000
                        });

                        // 2秒后刷新页面
                        setTimeout(() => {
                            this.loadPageData();
                        }, 2000);
                    }
                }
            } catch (error) {
                console.error('轮询状态失败:', error);
            }
        }, 3000);  // 3秒轮询一次
    },

    /**
     * 跳转到采访页
     */
    onGoToInterview() {
        wx.navigateTo({
            url: '/pages/interview/interview'
        });
    },

    /**
     * 停止轮询
     */
    stopPolling() {
        if (this.data.pollingTimer) {
            clearInterval(this.data.pollingTimer);
            this.setData({
                pollingTimer: null,
                isPolling: false
            });
        }
    },

    /**
     * 返回上一页
     */
    handleGoBack() {
        wx.navigateBack({
            delta: 1,
            fail: () => {
                wx.switchTab({
                    url: '/pages/index/index'
                });
            }
        });
    }


});
