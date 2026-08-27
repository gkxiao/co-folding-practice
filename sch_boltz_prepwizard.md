
名为 **`boltz_prepwizard.py`** 的 Python 脚本，其核心功能是：**将 Boltz 共折叠（co-folding）预测输出的 CIF 文件，用 Schrödinger 的 PrepWizard 工具进行结构准备，并做一系列后处理，最终输出可直接用于后续计算的 Maestro MAEGZ 文件**。

下面按模块逐段解释其功能：

---

## 1. 整体工作流

```
Boltz 预测输出的 CIF 文件
        │
        ▼
   Schrödinger PrepWizard（加氢、补侧链、加二硫键、Epik 质子化、pKa 等）
        │
        ▼
       MAEGZ 文件
        │
        ▼ 后处理（finalize_structure）：
        ├── 设置结构标题为 model_i
        ├── 可选：蛋白质残基编号平移（如 1→28）
        └── 写入 Boltz 置信度属性（confidence_score 等）
        │
        ▼
   最终 MAEGZ 文件
```

---

## 2. 命令行参数（`parse_args`）

| 参数 | 作用 |
|---|---|
| `-i / --input` | **必填**，Boltz 输入 YAML 文件（如 `EP262_K28.yaml`），用于定位预测结果目录 |
| `-ref / --reference` | 可选参考结构（如实验结构 `7S8L.maegz`），传给 PrepWizard 的 `-reference_st_file`（用于以参考结构为模板补缺失残基等） |
| `-oprefix` | 输出文件名前缀，默认取输入 YAML 的文件名主干 |
| `-renumber_shift` | 整数偏移量，PrepWizard 完成后对蛋白残基编号统一平移（如 +27） |
| `-HOST` | PrepWizard 提交的 JobControl host，默认 `localhost:4` |
| `--no-samplewater` | 默认会用 `-samplewater` 采样水分子，此开关可关闭 |

---

## 3. 定位 Boltz 输出（`find_prediction_directory`、`find_cif_files`）

- 根据输入 YAML 的文件名（如 `EP262_K28`），在**当前目录**下寻找标准 Boltz 输出目录结构：
  `boltz_results_EP262_K28/predictions/EP262_K28/`
- 用正则 `_model_(\d+)\.cif$` 提取模型编号，找出所有 `*_model_*.cif` 文件，**并按模型编号数值排序**（保证 model_10 排在 model_2 之后）。

---

## 4. 读取置信度 JSON（`find_confidence_json` / `read_confidence_json`）

- 对每个模型 CIF（如 `EP262_K28_model_0.cif`），配对读取同目录下的 `confidence_EP262_K28_model_0.json`。
- 该 JSON 是 Boltz 输出的模型置信度信息（如 `confidence_score`、`ptm`、`iptm`、`chain_ptm`、`chain_pae` 等），会被写入最终结构的属性中。

---

## 5. 构建 PrepWizard 命令（`build_prepwizard_command`）

从环境变量 `SCHRODINGER` 定位 `utilities/prepwizard` 可执行文件，然后构造一条完整命令，关键选项包括：

- **结构处理**：`-fillsidechains`（补侧链）、`-disulfides`（二硫键）、`-assign_all_residues`、`-rehtreat`（对 His/Asn/Gln 侧链翻转优化）
- **质子化**：`-epik_pH 7.4`、`-epik_pHt 2.0`（Epik 在 pH 7.4 ± 2.0 范围内计算质子化状态，`-max_states 1` 只取一个状态）
- **CDR 编号**：`-antibody_cdr_scheme Kabat`（按 Kabat 方案标注抗体 CDR 区）
- **可选参考结构**：`-reference_st_file`
- **水分子**：默认 `-samplewater`（采样水分子）
- **pKa**：`-propka_pH 7.4`
- **力场/几何**：`-f S-OPLS`（力场）、`-rmsd 0.3`（结构优化 RMSD 收敛阈值）、`-watdist 5.0`
- **作业控制**：`-JOBNAME`、`-HOST localhost:4`

---

## 6. 串行执行 PrepWizard（`run_prepwizard`）

- 使用 `jobcontrol.launch_job` 提交作业并**等待其完成**（`job.wait(throw_on_failure=True)`）。
- 关键设计：**每次只提交一个模型，前一个完成才提交下一个**。这是为了**减少同时占用的 Schrödinger license token**。
- 作业完成后还会校验输出 MAEGZ 文件确实存在，防止"假成功"。

---

## 7. 后处理（`finalize_structure`）—— 本脚本的核心增值部分

对每个 PrepWizard 输出的 MAEGZ 做 4 件事：

1. **读取单结构**：用 `StructureReader` 读取，校验文件中**恰好只有一个** Structure（一个 Boltz CIF 对应一个复合物）。

2. **设置标题**：将结构标题设为 `model_0`、`model_1` … 便于后续区分模型。

3. **残基重编号（可选）**：`renumber_protein_residues` 将所有**标准蛋白氨基酸**（20 种天然氨基酸，见 `STANDARD_PROTEIN_RESIDUES` 集合）的残基编号统一加上偏移量。例如 `-renumber_shift 27` 使残基 1→28、2→29……
   - 判断标准蛋白残基时用的是 `residue.pdbres`（PDB 三字母残基名），因为注释说明 Schrödinger 2025之前 的 `_Residue` 对象没有 `is_protein` 属性。
   - **水和配体等非蛋白残基不参与重编号**，这通常用于把 Boltz 预测编号对齐到实验结构（如 7S8L）的编号体系。
   - 若请求了重编号却找不到任何蛋白残基，会报错。

4. **写入置信度属性**：把 confidence JSON 的每个顶层字段转成 Maestro 用户属性（`st.property`）：
   - 类型前缀规则：float → `r_user_*`，int → `i_user_*`，bool → `b_user_*`，字符串/字典/列表 → `s_user_*`（嵌套结构用紧凑 JSON 字符串存储）。
   - 键名中的非法字符替换为下划线。
   - 例如 `confidence_score: 0.83` 会变成 `r_user_confidence_score = 0.83`。

5. **写回**：用 `st.write()` 覆盖写回同一个 MAEGZ 文件（注释特别提醒不要用 `structure.write(...)`）。

---

## 8. 主流程（`main`）

1. 校验输入 YAML、参考结构存在；确定输出前缀。
2. 定位预测目录、列出所有模型 CIF。
3. 打印总览（模型清单、置信度文件、各参数）。
4. **逐个模型**循环：
   - 先读置信度 JSON
   - 再跑 PrepWizard（串行等待）
   - 再做后处理（标题/重编号/属性）
   - 成功记入 `successful`，失败记入 `failed` 并**立即中止整个流程**（`break`），因为后续模型可能依赖相同问题。
5. 打印最终汇总，有失败则以退出码 1 结束。

---

## 一句话总结

> 这是一个批量流水线脚本：把 Boltz 预测的多个模型 CIF **串行地**经过 Schrödinger PrepWizard（补侧链、质子化、加氢、优化）准备成 MAEGZ，再自动加上模型标题、按需平移蛋白残基编号、并把 Boltz 的置信度评分以 Maestro 属性的形式嵌入结构文件，最终得到适合直接进入后续分子模拟 / 对接 / 分析流程的、且能与实验编号对齐的成品结构。

典型用法（如示例中针对 EP262_K28 系统、以 7S8L 为参考、编号平移 27）：

```bash
$SCHRODINGER/run boltz_prepwizard.py -i EP262_K28.yaml -ref 7S8L.maegz -renumber_shift 27
```
