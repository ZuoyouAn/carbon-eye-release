# Carbon Eye 数据质量报告

- 状态：通过
- 生成时间：2026-07-14T15:02:35.247270+08:00
- 通过项：29
- 警告项：0
- 错误项：0

## 通过项
- 文件存在：backend/data/carbon_eye/sources/sip_electricity_official.csv
- 文件存在：backend/data/carbon_eye/sources/jiangsu_electricity_emission_factors.csv
- 文件存在：backend/data/carbon_eye/sources/sip_characteristic_air_snapshot.csv
- 文件存在：backend/data/carbon_eye/monthly_trends.json
- 文件存在：backend/data/carbon_eye/park_electricity_emissions.json
- 文件存在：backend/data/carbon_eye/park_environment_snapshot.json
- 文件存在：backend/data/carbon_eye/industry_profile.json
- 文件存在：backend/data/carbon_eye/cdci.json
- 文件存在：backend/data/carbon_eye/cdci_sensitivity.json
- 文件存在：backend/data/carbon_eye/weather/weather_park_monthly.csv
- 文件存在：backend/data/carbon_eye/weather/weather_air_correlations.json
- 官方园区用电记录为4条（2019、2023、2024、2025）
- 2020-2022 年用电缺口未被填补
- 园区官方监测点位为6个
- 特征因子记录为84条（14项×6点）
- 特征因子种类为14项
- 产业画像为6类
- 2019 全社会购电代理公式复算一致
- 2023 全社会购电代理公式复算一致
- 2024 全社会购电代理公式复算一致
- 2025 全社会购电代理公式复算一致
- 月度空气质量记录为152条
- 2026-07 标识为部分月并排除年度统计
- 长期气象月度记录不少于145条
- 长期气象只包含完整月份
- 长期气象各月六点覆盖率不低于95%
- 气象相关分析排除2026-07部分月
- 相关分析保留非因果警告
- 实验性 CDCI 仅对具备年度能碳数据的月份计算

## 口径提醒
- 月度空气质量为苏州市级背景，不能等同于园区内部连续监测。
- 园区六点位数据是 2026 年 6 月、7 天官方短期监测快照。
- 用电结果仅为园区购电间接排放位置法代理估算；2020-2022 保持缺口。
- 气象结果仅用于描述性相关，相关不等于因果。
