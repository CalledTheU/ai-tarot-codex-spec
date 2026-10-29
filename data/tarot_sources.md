# 牌义来源登记

## pg-43548

- 实际书名：*The Illustrated Key to the Tarot: The Veil of Divination*。
- 该版本署名：L. W. de Laurence（1868–1936），1918 年，Chicago，The de Laurence Company。不能将此数字版本误标为 Waite 原版。
- 目录页：https://www.gutenberg.org/ebooks/43548 。访问时作者、1918 年版本正文与版权状态均已核对；目录声明 **Public domain in the USA**。这是美国版权状态，不是全球授权保证。
- 原始 HTML：https://www.gutenberg.org/files/43548/43548-h/43548-h.htm 。获取日期：2026-10-29；本地完整快照：`data/sources/43548-h.htm`。保留原书署名和历史版权声明，未下载或分发书中图片。
- 大阿尔卡那：Part III, Section 3（`#III3`），逐牌条目。Strength 在该版本称 Fortitude，Judgment 称 The Last Judgment。
- 小阿尔卡那：Part III, Section 2；`#III2wands`、`#III2cups`、`#III2swords`、`#III2pent` 下逐牌 Divinatory Meanings 与 Reversed。
- **圣杯二例外**：Section 2 原文没有逆位段落；逆位摘自 Part III, Section 4（`#III4`），Cups → Two → Reversed: Passion。逐牌记录包含该例外定位和独立逆位链接，没有补写或伪造缺失原文。
- 处理方式：仅去掉 HTML 标记、解码实体、合并空白。保留英文原文，不生成中文牌义、不把现代常见解释混入引文。关键词取对应摘录最前面的最多三个标点分句，属于机械摘录，不声称为人工审核关键词。
- 每张牌记录来源 ID、实际 URL、章节与条目定位、作者、出版年、版权状态、获取日期、内容版本、原始快照 SHA-256、正逆位合并摘录 SHA-256。`scripts/build_catalog.py` 可从本地快照确定性重建 JSON，测试比对全部 78 张。

## 使用边界

这是可核对的历史文本资料，不是科学事实或现代专业建议。原文存在过时的性别、外貌、疾病、死亡和宿命描述；展示时必须明确标注“历史文献摘录（英文）”，不能据此推断真实人物或未来事件。中文释义与现代化编辑尚未进行人工审核，本阶段不声称已经完成。

中文牌名为项目整理的检索标签，并非该英文版本中的中文译文。四种牌阵及其说明、位置与坐标由本项目按 SPEC 编写，不宣称来自上述书籍，也不冒称某种古老牌阵传承。

## 变更规则

修改摘录须更新来源、版本及哈希并通过快照重建比对。种子导入只插入缺失记录，不覆盖数据库已有内容；修订线上内容需要单独审核和显式数据迁移。图片路径现全部为空，前端使用文字占位，不含任何商业牌面素材。
