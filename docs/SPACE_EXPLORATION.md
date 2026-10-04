# Space v5：浅色界面与探索页

## 页面与范围

- 全站浅色系统字体、留白卡片、蓝色主按钮、轻量滚动显现；尊重减少动态效果，不使用 Apple 的素材或代码。
- `/wasteland`：原创 Three.js 低多边形场景。WASD/方向键、Shift 冲刺、E 拾取/修复、F 急救、Esc 暂停；触屏摇杆。180 秒内搜集 4 零件、2 电芯，修复信标并撤离。暂停/失焦/隐藏页面不推进时间；卸载释放帧循环、监听器和 GPU 资源。
- `/wasteland?mode=story`：原三十天剧情、v1 存档与导出规则不变。3D 模式不保存、不上传进度；无 WebGL2 时提供剧情入口。
- `/solar-system`：独立原创八行星示意图。拖动相机、缩放、选择、深链接、暂停与近景。默认静止，隐藏页面停止动画；图形不可用时可阅读文字。大小、距离、运行速度不是物理量，圆轨道不能预测星历。
- `/life-guide`：完整 34 节、657 条冻结原文；全文搜索、原书顺序、证据/成本/收益口径过滤、12 条分页。四路并发加载静态章节，失败重试，卸载取消读取。完整保留条目来源、适用条件和备注，不提供个性化医疗/法律/金融建议，不调用模型。

新模块均懒加载，Three.js 由两个 3D 页面共享，不进入首页包；不新增云资源或费用。账号、数据库、权限、模型配置没有改动。

## 来源与许可

太阳系事实：NASA [About the Planets](https://science.nasa.gov/solar-system/planets/)，2026-10-05 核对。仅使用基础分类、顺序、大小排名的文字概述；全部模型为本站程序化几何，没有下载天体照片。

参考站 [Solar System Atlas](https://solar-system-atlas.pages.dev/) 当前为 HUMAN ARTIFACTS 人类太阳系造物图谱。其 `X-Frame-Options: SAMEORIGIN` 与 CSP `frame-ancestors 'self'` 禁止第三方嵌入。本站保留入口并独立实现基础行星体验，不声称复制其完整任务目录，也不绕过安全头。

《高性价比人生指南》原作：eternity4719 / HowToLiveBetter contributors，[仓库](https://github.com/eternity4719/HowToLiveBetter)，[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。快照同步日期 2026-10-05；原始提交 `b4048d14960fec19c0367f8c0e6891f2b038c7ef`。正文未改写，仅转换为章节 JSON 并新增阅读界面；页面、manifest 和完整许可均保留署名、来源、版本与变化说明。原作者不为本站背书。该快照不会自动跟随上游更新。

## 更新原文

`scripts/import_life_guide.mjs` 只读本地上游 checkout 并输出补丁。提交被固定；更新需人工复核新版 README、内容许可、章节结构及成本算法后调整提交断言。

```powershell
# 在项目根目录执行；逐项输出补丁交给 apply_patch，不直接覆写源码。
node scripts/import_life_guide.mjs outputs/life-guide-upstream manifest
node scripts/import_life_guide.mjs outputs/life-guide-upstream 01
node scripts/import_life_guide.mjs outputs/life-guide-upstream license
```

性价比沿用快照 index.html 的 COST_W 与收益/成本分档；缺标签显示未标注，不猜测。性价比是作者判断，与证据等级分开显示；不跨收益口径排名。

## 验证

CI 包含原有回归测试与新增规则/图谱/全文索引测试，并保留首页 CSS 100 KiB / JS 220 KiB 预算。
`scripts/check_light_exploration_browser.py` 通过实际键盘移动完成整局，不使用状态注入或传送；检查移动端、摇杆、暂停、WebGL2 降级、减少动态效果、原文条目与来源。`--live` 仅操作浏览器本地状态和公开读取，不创建云端数据。
