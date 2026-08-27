A personal collection of practical experiences, troubleshooting notes, and scripts for protein-ligand co-folding (Boltz, AlphaFold3, Chai-1, etc.) — from structure prediction to downstream preparation.

# Boltz 结合模式与亲和力预测演示

本文档演示如何使用一个 YAML 输入文件，通过 Boltz 同时预测**蛋白质-配体复合物结合模式**与**结合亲和力**，并解读核心输出文件。

---

## 目录

- [1. 输入文件：`8_affinity.yaml`](#1-输入文件8_affinityyaml)
- [2. 运行预测命令](#2-运行预测命令)
- [3. 实际输出文件结构](#3-实际输出文件结构)
- [4. 文件功能详解](#4-文件功能详解)
  - [4.1 结构文件（.cif）](#41-结构文件cif)
  - [4.2 亲和力预测结果](#42-亲和力预测结果)
- [5. 使用注意](#5-使用注意)
- [6. 参考链接](#6-参考链接)

---

## 1. 输入文件：`8_affinity.yaml`

```yaml
version: 1  # 可选，默认为 1

sequences:
  - protein:
      id: A
      sequence: GLGYGSWEIDPKDLTFLKELGTGQFGVVKYGKWRGQYDVAIKMIKEGSMSEDEFIEEAKVMMNLSHEKLVQLYGVCTKQRPIFIITEYMANGCLLNYLREMRHRFQTQQLLEMCKDVCEAMEYLESKQFLHRDLAARNCLVNDQGVVKVSDFGLSRYVLDDEYTSSVGSKFPVRWSPPEVLMYSKFSSKSDIWAFGVLMWEIYSLGKMPYERFTNSETAEHIAQGLRLYRPHLASEKVYTIMYSCWHEKADERPTFKILLSNILDVMDEEX
  - ligand:
      id: B
      smiles: 'O=C(N)c1c(N)c2cccc(-c3ccc4cn[nH]c4c3)c2nn1'

properties:
  - affinity:
      binder: B
```

**说明**：

- `protein` 链 A 为靶标蛋白，`ligand` 链 B 为小分子。
- `affinity.binder: B` 表明要对配体 B 与蛋白的亲和力进行预测。
- 实际使用时请将序列替换为目标蛋白的完整氨基酸序列。

---

## 2. 运行预测命令

```bash
boltz predict 8_affinity.yaml \
  --use_msa_server \
  --use_potentials \
  --diffusion_samples 5 \
  --sampling_steps 1500 \
  --step_scale 1.5
```

**参数解析**：

| 参数 | 作用 |
|------|------|
| `--use_msa_server` | 在线获取 MSA 信息，无需本地数据库 |
| `--use_potentials` | 施加物理化学势能约束，改善构象合理性 |
| `--diffusion_samples 5` | 生成 5 个扩散结构样本 |
| `--sampling_steps 1500` | 每个样本的扩散去噪步数 |
| `--step_scale 1.5` | 扩散步长缩放因子 |

---

## 3. 实际输出文件结构

以下为一次典型运行的输出目录结构：

```
boltz_results_8_affinity/predictions/8_affinity
├── affinity_8_affinity.json
├── confidence_8_affinity_model_0.json
├── confidence_8_affinity_model_1.json
├── confidence_8_affinity_model_2.json
├── confidence_8_affinity_model_3.json
├── confidence_8_affinity_model_4.json
├── 8_affinity_model_0.cif
├── 8_affinity_model_1.cif
├── 8_affinity_model_2.cif
├── 8_affinity_model_3.cif
├── 8_affinity_model_4.cif
├── pae_8_affinity_model_0.npz
├── pae_8_affinity_model_1.npz
├── pae_8_affinity_model_2.npz
├── pae_8_affinity_model_3.npz
├── pae_8_affinity_model_4.npz
├── pde_8_affinity_model_0.npz
├── pde_8_affinity_model_1.npz
├── pde_8_affinity_model_2.npz
├── pde_8_affinity_model_3.npz
├── pde_8_affinity_model_4.npz
├── plddt_8_affinity_model_0.npz
├── plddt_8_affinity_model_1.npz
├── plddt_8_affinity_model_2.npz
├── plddt_8_affinity_model_3.npz
├── plddt_8_affinity_model_4.npz
└── pre_affinity_8_affinity.npz
```

---

## 4. 文件功能详解

### 4.1 结构文件（.cif）

- `8_affinity_model_{0..4}.cif`：5 个模型分别预测的复合物三维结构（每个模型对应一个 MSA 采样/模型参数，Boltz 默认使用 5 个模型集成）。
- 文件为 mmCIF 格式，可用可视化软件打开查看结合模式。

### 4.2 亲和力预测结果

- **`affinity_8_affinity.json`**：最终聚合的亲和力预测结果，通常包含以下键（具体以实际版本为准）：

```json
{
  "affinity_pred_value": 0.33956101536750793,
  "affinity_probability_binary": 0.27796271443367004,
  "affinity_pred_value1": -0.013617411255836487,
  "affinity_probability_binary1": 0.2643788456916809,
  "affinity_pred_value2": 0.6927394270896912,
  "affinity_probability_binary2": 0.2915465831756592
}
```

#### 字段结构（官方定义）

| 字段 | 含义 |
|---|---|
| `affinity_pred_value` | 集成模型的**结合亲和力数值**：`log10(IC50)`，IC50 单位为 **μM**。**数值越低＝结合越强** |
| `affinity_probability_binary` | 集成模型的**结合概率**（0–1），越接近 1 越可能是 binder |
| `affinity_pred_value1` / `affinity_probability_binary1` | 集成中**第 1 个成员模型**的对应输出 |
| `affinity_pred_value2` / `affinity_probability_binary2` | 集成中**第 2 个成员模型**的对应输出 |

> 注意：这两个输出头是在**不同的数据集、不同监督信号**下训练的，用途不同：
>
> - `affinity_probability_binary` → 用于**命中发现**（区分 binder vs decoy，虚拟筛选阶段）
> - `affinity_pred_value` → 用于**先导优化**（同系物间相对排序 / SAR 分析），是 IC50 类似量纲，assay 依赖

#### 数值解读

**集成模型（最终应采用的值）：**

- `affinity_pred_value = 0.34` → IC50 ≈ **10^0.34 ≈ 2.19 μM**
- `affinity_probability_binary = 0.278` → **结合概率约 28%**，远低于 0.5 阈值，判为"倾向非结合"

**两个成员模型：**

| 成员 | log10(IC50) | 对应 IC50 | 结合概率 |
|---|---|---|---|
| member 1 | −0.014 | ≈ **0.97 μM** | 0.264 |
| member 2 | 0.693 | ≈ **4.93 μM** | 0.292 |

**综合结论：** 三个模型高度一致——该化合物被预测为**弱到中等活性的结合剂**（IC50 在低微摩尔量级，约 1–5 μM），结合概率都只有 26–29%，低于 binder 判定阈值。按官方量纲参考（−3＝强结合 1 nM，0＝中等 1 μM，2＝弱/decoy 100 μM），它属于"中等偏弱"。

**ΔG 粗略换算**（官方公式 `ΔG ≈ (6 − y) × 1.364 kcal/mol`）：

- 集成：≈ **7.72 kcal/mol**
- member 1：≈ 8.20 kcal/mol
- member 2：≈ 7.24 kcal/mol

---

## 5. 使用注意

1. **只看相对排序，不读绝对亲和力**：`affinity_pred_value` 是"IC50 类似量纲"的 assay 依赖值，最适合在**同一靶标同系物系列内**比较修改带来的亲和力变化（其 FEP 子集基准 Pearson R≈0.66），跨 assay / 跨靶标比绝对值不可靠。
2. 结合概率（0.28）与数值（2 μM）结论一致，这里没有冲突。
3. 不要用结构置信度（`iptm`/`ptm`/`plddt`）当作亲和力代理——官方明确说明结构置信度与结合强度不相关。
4. 亲和力头不显式考虑辅因子、离子、水分子和多聚体伙伴；口袋选择错误或构象状态不对时预测质量会下降。若最终决策需要，建议用 ABFE/FEP 或实验复核。

---

## 6. 参考链接

- Boltz GitHub：https://github.com/jwohlwend/boltz
- Boltz 官方文档与输出格式说明：https://github.com/jwohlwend/boltz#output


