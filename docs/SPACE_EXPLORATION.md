# Space v5.1：浅色界面、任务档案与持续阅读

## 页面与范围

- 全站浅色系统字体、留白卡片、蓝色主按钮、轻量滚动显现；尊重减少动态效果，不使用 Apple 的素材或代码。
- `/wasteland`：原创 Three.js 低多边形场景。WASD/方向键、Shift 冲刺、E 拾取/修复、F 急救、Esc 暂停；触屏摇杆。180 秒内搜集 4 零件、2 电芯，修复信标并撤离。暂停/失焦/隐藏页面不推进时间；卸载释放帧循环、监听器和 GPU 资源。
- `/wasteland?mode=story`：原三十天剧情、v1 存档与导出规则不变。3D 模式不保存、不上传进度；无 WebGL2 时提供剧情入口。
- `/solar-system`：独立原创八行星示意图。拖动相机、缩放、选择、深链接、暂停与近景。默认静止，隐藏页面停止动画；图形不可用时可阅读文字。大小、距离、运行速度不是物理量，圆轨道不能预测星历。
- `/life-guide`：完整 34 节、657 条冻结原文；全文搜索、原书顺序、证据/成本/收益口径过滤、12 条分页。四路并发加载静态章节，失败重试，卸载取消读取。完整保留条目来源、适用条件和备注，不提供个性化医疗/法律/金融建议，不调用模型。

新模块均懒加载，Three.js 由两个 3D 页面共享，不进入首页包；不新增云资源或费用。账号、数据库、权限、模型配置没有改动。

## v5.1：持续探索与阅读

- 太阳系新增十个历史任务，按 UTC 发射日期排序；可组合目标行星、年代和关键词筛选。任务链接如 `/solar-system?planet=neptune&mission=voyager-2` 可独立打开。选择任务高亮相关行星与示意轨道，近景按钮暂停运行；不绘制航天器轨迹，不提供实时位置或当前任务状态。
- 任务档案只标记主要探测对象，不列全部助推点；每项附 NASA 来源。MESSENGER 发射按 NASA History 的 UTC 日期 2004-08-03，避免混用当地时间；旅行者 2 号先于 1 号发射。核对于 2026-10-05。
- 原文章节四路并发、逐章展示。选择或分享的章节优先加载；索引未完成时明确提示结果不完整。一章失败不隐藏其他原文，重试使用成功章节的内存缓存；离开路由取消请求。关键词搜索复用小写全文索引，完整 Markdown 仅在展开时渲染。
- 收藏和阅读定位默认只在会话内存在。用户主动开启本机保存后，`space-life-guide-reader-v1` 仅保存版本、许可标记、收藏条目编号与最后阅读编号；不存正文、查询、账号，也不上传服务器。关闭保存删除该键，但保留当前会话；清除记录删除该键并重置当前会话，保留其他存档。存储受限或损坏时降级到会话模式。
- 条目链接 `/life-guide?entry=1-13` 自动选择对应章节、页码并展开原文。筛选链接支持查询、章节、证据、收益口径、成本、性价比档与页码；不会把私有收藏列表带入 URL。浏览器前进/后退同步筛选控件。剪贴板不可用时提供可手动复制的链接。
- 原书冻结快照、许可、全部 657 条来源与备注以及性价比算法均未改动。不把阅读记录当健康数据，不添加个性化建议或模型调用。

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

`scripts/check_exploration_reader_browser.py` 验证档案筛选、深链接、本机保存需明确开启、恢复定位、限定清除范围、全部 URL 筛选与历史导航、章节缓存及 390px 布局。仅本地测试会模拟章节延迟与单章失败；`--live` 不注入网络故障、不创建线上账号或修改云端数据。新模块的纯函数、加载器和存储异常测试已加入现有 CI 通配范围。
